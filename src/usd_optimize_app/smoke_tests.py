"""Smoke-test helpers for the usd-optimize wrapper."""

from __future__ import annotations

import hashlib
import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from usd_optimize_app.constants import PROJECT_ROOT
from usd_optimize_app.errors import EnvironmentError, OptimizeError
from usd_optimize_app.models import OptimizeRequest, OptimizeResult, PresetDefinition
from usd_optimize_app.path_utils import ensure_supported_usd_path
from usd_optimize_app.presets import load_preset
from usd_optimize_app.usd_env import check_environment, list_available_operations
from usd_optimize_app.usd_runner import run_optimization

SIBLING_USD_OPTIMIZE_ROOT = PROJECT_ROOT.parent / "usd-optimize"
DEFAULT_SMOKE_FIXTURE = (
    SIBLING_USD_OPTIMIZE_ROOT / "source" / "tests" / "data" / "external" / "openusd_helloworld.usda"
)
DEFAULT_EXTERNAL_ASSET_MANIFEST = (
    SIBLING_USD_OPTIMIZE_ROOT / "tools" / "windows_prebuilt_repro" / "external_usd_assets.json"
)
DEFAULT_EXTERNAL_ASSETS_DIR = SIBLING_USD_OPTIMIZE_ROOT / ".cache" / "usd-assets"
DEFAULT_SMOKE_OUTPUT_DIR = PROJECT_ROOT / "reports" / "smoke-tests"
DEFAULT_SMOKE_PRESETS = ("safe_publish", "diagnostics", "find_overlaps")
DEFAULT_EXTERNAL_SMOKE_PRESETS = ("diagnostics",)


@dataclass(frozen=True)
class SmokeAsset:
    """One USD asset selected for a smoke-test run."""

    name: str
    path: Path
    expected_prims: tuple[str, ...]
    output_dir: Path | None = None


@dataclass(frozen=True)
class SmokeTestSettings:
    """Inputs controlling one smoke-test workflow."""

    input_path: Path | None = None
    output_dir: Path | None = None
    preset_names: tuple[str, ...] = DEFAULT_SMOKE_PRESETS
    external_assets: bool = False
    external_asset_manifest: Path | None = None
    external_assets_dir: Path | None = None


@dataclass(frozen=True)
class SmokeStepResult:
    """One completed smoke-test optimization step."""

    asset_name: str
    preset_name: str
    result: OptimizeResult


@dataclass(frozen=True)
class SmokeTestResult:
    """Summary of the smoke-test run."""

    runtime_root: Path
    operation_count: int
    input_path: Path | None
    output_dir: Path
    steps: list[SmokeStepResult]


def run_smoke_test(settings: SmokeTestSettings | None = None) -> SmokeTestResult:
    """Run the smoke-test workflow.

    Args:
        settings: Optional smoke-test inputs. Defaults to the bundled local fixture.

    Returns:
        Smoke-test summary.

    Raises:
        EnvironmentError: If the strict runtime artifact is not usable.
        OptimizeError: If an asset is missing, fails validation, or optimization fails.
    """
    settings = settings or SmokeTestSettings()
    status = check_environment()
    if not status.is_usable or status.runtime_root is None:
        problem_text = "; ".join(status.errors) if status.errors else "unknown problem"
        raise EnvironmentError(f"usd-optimize runtime is not usable: {problem_text}")

    available_operations = list_available_operations()
    resolved_output_dir = (settings.output_dir or DEFAULT_SMOKE_OUTPUT_DIR).expanduser().resolve()
    resolved_output_dir.mkdir(parents=True, exist_ok=True)

    assets = _resolve_assets(settings, resolved_output_dir)
    presets = [load_preset(preset_name) for preset_name in settings.preset_names]

    steps: list[SmokeStepResult] = []
    for asset in assets:
        _validate_expected_prims(asset.path, asset.expected_prims)
        for preset in presets:
            result = _run_asset_preset(asset, preset, resolved_output_dir)
            if preset.risk != "diagnostic":
                _validate_expected_prims(result.output_path, asset.expected_prims)
                if preset.name == "safe_publish":
                    _validate_safe_cleanup(asset.path, result.output_path)
            steps.append(
                SmokeStepResult(asset_name=asset.name, preset_name=preset.name, result=result)
            )

    input_path_result = assets[0].path if len(assets) == 1 else None
    return SmokeTestResult(
        runtime_root=status.runtime_root,
        operation_count=len(available_operations),
        input_path=input_path_result,
        output_dir=resolved_output_dir,
        steps=steps,
    )


def _resolve_assets(settings: SmokeTestSettings, output_dir: Path) -> list[SmokeAsset]:
    if settings.external_assets:
        manifest_path = (
            settings.external_asset_manifest or DEFAULT_EXTERNAL_ASSET_MANIFEST
        ).resolve()
        assets_dir = (settings.external_assets_dir or DEFAULT_EXTERNAL_ASSETS_DIR).resolve()
        return _load_external_assets(manifest_path, assets_dir, output_dir)

    resolved_input_path = ensure_supported_usd_path(settings.input_path or DEFAULT_SMOKE_FIXTURE)
    return [SmokeAsset(name=resolved_input_path.stem, path=resolved_input_path, expected_prims=())]


def _load_external_assets(
    manifest_path: Path, assets_dir: Path, output_dir: Path
) -> list[SmokeAsset]:
    if not manifest_path.is_file():
        raise OptimizeError(f"Missing external USD asset manifest: {manifest_path}")
    if not assets_dir.is_dir():
        raise OptimizeError(f"Missing external USD asset cache: {assets_dir}")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    work_dir = output_dir / "external-assets"
    assets: list[SmokeAsset] = []
    for asset_data in manifest.get("assets", []):
        source_path = _verify_cached_asset(asset_data, assets_dir)
        copied_path = work_dir / Path(asset_data["relative_path"])
        copied_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, copied_path)
        if asset_data.get("smoke", True) is False:
            continue
        expected_prims = tuple(asset_data.get("expected_prims", ()))
        assets.append(
            SmokeAsset(
                name=asset_data["name"],
                path=copied_path,
                expected_prims=expected_prims,
                output_dir=copied_path.parent,
            )
        )

    if not assets:
        raise OptimizeError(f"No smoke assets found in manifest: {manifest_path}")
    return assets


def _verify_cached_asset(asset_data: dict[str, Any], assets_dir: Path) -> Path:
    asset_path = assets_dir / Path(asset_data["relative_path"])
    if not asset_path.is_file():
        raise OptimizeError(f"Missing cached external USD asset: {asset_path}")

    expected_hash = asset_data["sha256"].lower()
    actual_hash = _hash_file(asset_path)
    if actual_hash != expected_hash:
        message = (
            f"SHA-256 mismatch for {asset_data['name']}: "
            f"expected {expected_hash}, got {actual_hash}"
        )
        raise OptimizeError(message)
    return asset_path


def _run_asset_preset(
    asset: SmokeAsset,
    preset: PresetDefinition,
    output_dir: Path,
) -> OptimizeResult:
    asset_output_dir = asset.output_dir or output_dir / asset.name
    output_path = asset_output_dir / f"{asset.path.stem}.{preset.name}.usda"
    request = OptimizeRequest(
        input_path=asset.path,
        output_path=output_path,
        preset=preset,
        force=True,
        write_output=preset.risk != "diagnostic",
    )
    return run_optimization(request)


def _validate_safe_cleanup(input_path: Path, output_path: Path) -> None:
    """Verify Safe Cleanup preserves geometry, transforms, and stage metrics.

    Args:
        input_path: Original stage path.
        output_path: Safe Cleanup derivative path.

    Raises:
        OptimizeError: If a supported preservation invariant changes.
    """
    from pxr import Usd, UsdGeom

    input_stage = Usd.Stage.Open(str(input_path))
    output_stage = Usd.Stage.Open(str(output_path))
    if input_stage is None or output_stage is None:
        raise OptimizeError("Safe Cleanup input or output stage could not be opened.")

    _require_equal(
        "default prim",
        str(input_stage.GetDefaultPrim().GetPath()),
        str(output_stage.GetDefaultPrim().GetPath()),
    )
    stage_metrics = {
        "start time": (input_stage.GetStartTimeCode(), output_stage.GetStartTimeCode()),
        "end time": (input_stage.GetEndTimeCode(), output_stage.GetEndTimeCode()),
        "time codes per second": (
            input_stage.GetTimeCodesPerSecond(),
            output_stage.GetTimeCodesPerSecond(),
        ),
        "frames per second": (
            input_stage.GetFramesPerSecond(),
            output_stage.GetFramesPerSecond(),
        ),
        "up axis": (UsdGeom.GetStageUpAxis(input_stage), UsdGeom.GetStageUpAxis(output_stage)),
        "meters per unit": (
            UsdGeom.GetStageMetersPerUnit(input_stage),
            UsdGeom.GetStageMetersPerUnit(output_stage),
        ),
    }
    for label, values in stage_metrics.items():
        _require_equal(label, values[0], values[1])

    input_prims = _transformable_prim_types(input_stage)
    output_prims = _transformable_prim_types(output_stage)
    _require_equal("transformable prim paths and types", input_prims, output_prims)

    for prim_path in input_prims:
        input_prim = input_stage.GetPrimAtPath(prim_path)
        output_prim = output_stage.GetPrimAtPath(prim_path)
        _validate_preserved_attributes(input_prim, output_prim)


def _transformable_prim_types(stage: object) -> dict[str, str]:
    """Return loaded transformable prim paths and schema types."""
    from pxr import UsdGeom

    return {
        str(prim.GetPath()): prim.GetTypeName()
        for prim in stage.TraverseAll()
        if prim.IsA(UsdGeom.Xformable)
    }


def _validate_preserved_attributes(input_prim: object, output_prim: object) -> None:
    """Compare topology and transform values at all source-authored samples."""
    preserved_names = {
        "faceVertexCounts",
        "faceVertexIndices",
        "holeIndices",
        "points",
        "xformOpOrder",
    }
    for input_attribute in input_prim.GetAttributes():
        attribute_name = input_attribute.GetName()
        if attribute_name not in preserved_names and not attribute_name.startswith("xformOp:"):
            continue
        output_attribute = output_prim.GetAttribute(attribute_name)
        if not output_attribute:
            raise OptimizeError(
                f"Safe Cleanup removed attribute {input_prim.GetPath()}.{attribute_name}."
            )
        _require_equal(
            f"{input_prim.GetPath()}.{attribute_name} default value",
            input_attribute.Get(),
            output_attribute.Get(),
        )
        for time_code in input_attribute.GetTimeSamples():
            _require_equal(
                f"{input_prim.GetPath()}.{attribute_name} at {time_code}",
                input_attribute.Get(time_code),
                output_attribute.Get(time_code),
            )


def _require_equal(label: str, input_value: object, output_value: object) -> None:
    if input_value != output_value:
        raise OptimizeError(
            f"Safe Cleanup changed {label}: input={input_value!r}, output={output_value!r}"
        )


def _validate_expected_prims(stage_path: Path, expected_prims: tuple[str, ...]) -> None:
    if not expected_prims:
        return

    from pxr import Usd

    stage = Usd.Stage.Open(str(stage_path))
    if stage is None:
        raise OptimizeError(f"Could not reopen USD stage: {stage_path}")

    missing_prims = [
        prim_path for prim_path in expected_prims if not stage.GetPrimAtPath(prim_path)
    ]
    if missing_prims:
        message = f"Missing expected prims in {stage_path}: {', '.join(missing_prims)}"
        raise OptimizeError(message)


def _hash_file(file_path: Path) -> str:
    digest = hashlib.sha256()
    with file_path.open("rb") as asset_file:
        for chunk in iter(lambda: asset_file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
