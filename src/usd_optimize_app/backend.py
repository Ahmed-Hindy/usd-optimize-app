"""Shared backend used by the CLI and GUI."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from threading import Event

from usd_optimize_app.errors import PresetError, UsdOptimizeAppError
from usd_optimize_app.models import (
    EnvironmentStatus,
    OptimizeRequest,
    OptimizeResult,
    PresetDefinition,
)
from usd_optimize_app.operation_scope import normalize_prim_paths
from usd_optimize_app.path_utils import default_output_path, ensure_supported_usd_path
from usd_optimize_app.presets import load_all_presets, load_preset, operation_names
from usd_optimize_app.usd_env import check_environment, configure_environment
from usd_optimize_app.usd_runner import run_optimization

SCENE_GRAPH_MAX_PRIMS = 2_000
SCENE_GRAPH_MAX_DEPTH = 64
GUI_WORKFLOW_PRESET_NAMES = (
    "safe_publish",
    "geometry_optimization",
    "find_overlaps",
)


@dataclass(frozen=True)
class SceneGraphNode:
    """One display-ready prim in the inspected USD hierarchy."""

    name: str
    path: str
    type_name: str
    children: tuple[SceneGraphNode, ...] = ()
    has_payload: bool = False
    has_references: bool = False
    is_instance: bool = False
    is_active: bool = True
    is_loaded: bool = True


@dataclass(frozen=True)
class PresetView:
    """Display-ready preset data."""

    name: str
    display_name: str
    risk: str
    description: str
    operations: tuple[str, ...]


@dataclass(frozen=True)
class InputInspection:
    """Display-ready validation result for one input USD path."""

    is_valid: bool
    message: str
    root_prim_count: int | None = None
    authored_reference_count: int = 0
    authored_payload_count: int = 0
    prim_count: int = 0
    scene_graph: tuple[SceneGraphNode, ...] = ()
    scene_graph_truncated: bool = False


@dataclass(frozen=True)
class OptimizeJobSettings:
    """User-facing optimization settings before preset resolution."""

    input_path: Path
    output_path: Path | None
    preset_name: str
    force: bool = False
    dry_run: bool = False
    write_output: bool = True
    cancel_event: Event | None = None
    prim_paths: tuple[str, ...] = ()


def get_environment_status() -> EnvironmentStatus:
    """Return the strict usd-optimize runtime environment status."""
    return check_environment()


def get_gui_workflows() -> list[PresetView]:
    """Return the explicit artist-triggered workflows in UI order."""
    return [preset_to_view(load_preset(name)) for name in GUI_WORKFLOW_PRESET_NAMES]


def get_preset_views() -> list[PresetView]:
    """Return all bundled user presets for backward compatibility."""
    return [preset_to_view(preset) for preset in load_all_presets()]


def preset_to_view(preset: PresetDefinition) -> PresetView:
    """Convert a preset definition to display data."""
    return PresetView(
        name=preset.name,
        display_name=preset.display_name,
        risk=preset.risk,
        description=preset.description,
        operations=tuple(
            operation_name
            for operation_name in operation_names(preset)
            if operation_name != "executionContext"
        ),
    )


def resolve_default_output_path(input_path: Path) -> Path:
    """Return the default optimized output path."""
    return default_output_path(input_path)


def inspect_input_path(input_path: Path) -> InputInspection:
    """Open a USD stage and return concise feedback for the GUI input field."""
    try:
        resolved_path = ensure_supported_usd_path(input_path)
    except UsdOptimizeAppError as error:
        return InputInspection(False, str(error))
    if not resolved_path.exists():
        return InputInspection(False, "Input USD file does not exist.")

    status = check_environment()
    if not status.is_usable:
        message = status.errors[0] if status.errors else "USD runtime is unavailable."
        return InputInspection(False, message)
    try:
        configure_environment(status.runtime_root)
        from pxr import Usd

        stage = Usd.Stage.Open(str(resolved_path))
        if stage is None:
            return InputInspection(False, "USD stage could not be opened.")
        scene_graph, prim_count, scene_graph_truncated = _build_scene_graph(stage)
        root_prim_count = len(stage.GetPseudoRoot().GetAllChildren())
        authored_reference_count = 0
        authored_payload_count = 0
        for prim in stage.TraverseAll():
            authored_reference_count += int(prim.HasAuthoredReferences())
            authored_payload_count += int(prim.HasAuthoredPayloads())
    except Exception as error:
        return InputInspection(False, f"Could not inspect USD stage: {error}")
    prim_label = "prim" if prim_count == 1 else "prims"
    return InputInspection(
        True,
        f"Scene loaded · {prim_count} {prim_label}",
        root_prim_count,
        authored_reference_count,
        authored_payload_count,
        prim_count,
        scene_graph,
        scene_graph_truncated,
    )


def _build_scene_graph(stage: object) -> tuple[tuple[SceneGraphNode, ...], int, bool]:
    """Build a bounded display hierarchy from an opened USD stage.

    Every top-level prim remains visible even when one root has enough descendants
    to exhaust the display budget. The remaining budget is shared across roots.
    """
    prim_count = 0
    truncated = False

    def build_node(prim: object, depth: int, budget: int) -> tuple[SceneGraphNode, int]:
        nonlocal prim_count, truncated
        prim_count += 1
        children: list[SceneGraphNode] = []
        child_prims = prim.GetAllChildren()
        remaining_budget = budget - 1
        if child_prims and depth >= SCENE_GRAPH_MAX_DEPTH:
            truncated = True
        else:
            for child in child_prims:
                if remaining_budget <= 0:
                    truncated = True
                    break
                child_node, child_count = build_node(child, depth + 1, remaining_budget)
                children.append(child_node)
                remaining_budget -= child_count

        node = SceneGraphNode(
            name=str(prim.GetName()),
            path=str(prim.GetPath()),
            type_name=str(prim.GetTypeName()) or "Prim",
            children=tuple(children),
            has_payload=prim.HasAuthoredPayloads(),
            has_references=prim.HasAuthoredReferences(),
            is_instance=prim.IsInstance(),
            is_active=prim.IsActive(),
            is_loaded=prim.IsLoaded(),
        )
        return node, budget - remaining_budget

    root_prims = stage.GetPseudoRoot().GetAllChildren()
    roots: list[SceneGraphNode] = []
    remaining_budget = SCENE_GRAPH_MAX_PRIMS
    for index, root_prim in enumerate(root_prims):
        remaining_roots = len(root_prims) - index
        remaining_descendant_budget = max(0, remaining_budget - remaining_roots)
        root_budget = 1 + (remaining_descendant_budget + remaining_roots - 1) // remaining_roots
        root_node, root_count = build_node(root_prim, 0, root_budget)
        roots.append(root_node)
        remaining_budget -= root_count
    return tuple(roots), prim_count, truncated


def build_optimize_request(settings: OptimizeJobSettings) -> OptimizeRequest:
    """Build a validated optimization request from user-facing settings."""
    input_path = ensure_supported_usd_path(settings.input_path)
    output_path = (
        settings.output_path.expanduser().resolve()
        if settings.output_path
        else default_output_path(input_path)
    )
    preset = load_preset(settings.preset_name)
    return OptimizeRequest(
        input_path=input_path,
        output_path=output_path,
        preset=preset,
        force=settings.force,
        dry_run=settings.dry_run,
        write_output=settings.write_output,
        prim_paths=normalize_prim_paths(settings.prim_paths),
        cancel_event=settings.cancel_event,
    )


def run_optimize_job(settings: OptimizeJobSettings) -> OptimizeResult:
    """Run an optimization job through the shared backend."""
    return run_optimization(build_optimize_request(settings))


def run_batch_jobs(
    input_paths: tuple[Path, ...],
    output_dir: Path | None,
    preset_name: str,
    *,
    force: bool = False,
) -> list[OptimizeResult]:
    """Run one bundled preset across explicit inputs into one output directory."""
    if not input_paths:
        raise PresetError("Select at least one USD input for batch optimization.")
    preset = load_preset(preset_name)
    write_output = preset.risk != "diagnostic"
    if write_output and output_dir is None:
        raise PresetError("Choose an output directory for this batch preset.")
    resolved_output_dir = output_dir.expanduser().resolve() if output_dir else None
    planned_jobs: list[tuple[Path, Path]] = []
    for input_path in input_paths:
        resolved_input_path = ensure_supported_usd_path(input_path)
        output_path = (
            resolved_output_dir / default_output_path(resolved_input_path).name
            if resolved_output_dir
            else default_output_path(resolved_input_path)
        )
        planned_jobs.append((resolved_input_path, output_path))

    if write_output:
        output_counts = Counter(output_path for _, output_path in planned_jobs)
        duplicate_outputs = sorted(
            output_path for output_path, count in output_counts.items() if count > 1
        )
        if duplicate_outputs:
            paths = ", ".join(str(path) for path in duplicate_outputs)
            raise PresetError(f"Batch inputs resolve to duplicate output paths: {paths}")
        input_set = {input_path for input_path, _ in planned_jobs}
        source_overwrites = [
            output_path for _, output_path in planned_jobs if output_path in input_set
        ]
        if source_overwrites:
            paths = ", ".join(str(path) for path in source_overwrites)
            raise PresetError(f"Batch outputs would overwrite input USD files: {paths}")
        if not force:
            existing_outputs = [
                output_path for _, output_path in planned_jobs if output_path.exists()
            ]
            if existing_outputs:
                paths = ", ".join(str(path) for path in existing_outputs)
                raise PresetError(
                    f"Batch output paths already exist: {paths}. Use --force to replace."
                )

    results: list[OptimizeResult] = []
    for resolved_input_path, output_path in planned_jobs:
        results.append(
            run_optimize_job(
                OptimizeJobSettings(
                    input_path=resolved_input_path,
                    output_path=output_path,
                    preset_name=preset_name,
                    force=force,
                    write_output=write_output,
                )
            )
        )
    return results
