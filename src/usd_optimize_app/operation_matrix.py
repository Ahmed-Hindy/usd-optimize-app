"""Run isolated exploratory checks for registered usd-optimize operations."""

from __future__ import annotations

import json
import shutil
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal

from usd_optimize_app.constants import PROJECT_ROOT
from usd_optimize_app.errors import EnvironmentError, OptimizeError
from usd_optimize_app.models import OptimizeRequest, PresetDefinition
from usd_optimize_app.operation_support import OperationSupportTier, get_operation_support
from usd_optimize_app.usd_env import check_environment, list_available_operations
from usd_optimize_app.usd_runner import run_optimization

DEFAULT_OPERATION_MATRIX_OUTPUT_DIR = PROJECT_ROOT / "reports" / "operation-matrix"

OperationKind = Literal["standard", "analysis", "parameterized", "gpu", "special"]
OperationExpectation = Literal["pass", "allow_failure"]

_KIND_BY_SUPPORT_TIER: dict[OperationSupportTier, OperationKind] = {
    "supported": "standard",
    "advanced": "standard",
    "requires_configuration": "parameterized",
    "gpu": "gpu",
    "internal": "special",
}

# These operations need asset-specific settings or compatible hardware. Failure
# with an empty/default configuration is therefore not a product regression.
DEFAULT_CONFIGURATION_FAILURES = frozenset({"boxClip", "findOccludedMeshes", "removeAttributes"})


@dataclass(frozen=True)
class OperationMatrixCase:
    """One registered operation selected for an isolated runtime check."""

    operation_name: str
    kind: OperationKind
    support_tier: OperationSupportTier
    is_analysis: bool
    expected: OperationExpectation


@dataclass(frozen=True)
class OperationMatrixStep:
    """Recorded outcome for one isolated operation execution."""

    operation_name: str
    kind: OperationKind
    support_tier: OperationSupportTier
    expected: OperationExpectation
    status: Literal["passed", "failed", "skipped"]
    output_path: Path | None
    output_reopened: bool | None
    error: str | None = None


@dataclass(frozen=True)
class OperationMatrixResult:
    """Summary and persisted manifest for one operation matrix run."""

    input_path: Path
    output_dir: Path
    manifest_path: Path
    steps: tuple[OperationMatrixStep, ...]

    @property
    def unexpected_failures(self) -> tuple[OperationMatrixStep, ...]:
        """Return failed operations whose declared default check should pass."""
        return tuple(
            step for step in self.steps if step.status == "failed" and step.expected == "pass"
        )


def build_operation_matrix_cases(operation_names: list[str]) -> tuple[OperationMatrixCase, ...]:
    """Classify runtime operations for safe, isolated exploratory execution.

    Args:
        operation_names: Names discovered from the configured runtime artifact.

    Returns:
        One matrix case per distinct operation name, sorted by name.
    """
    cases: list[OperationMatrixCase] = []
    for operation_name in sorted(set(operation_names)):
        support = get_operation_support(operation_name)
        kind = _KIND_BY_SUPPORT_TIER[support.tier]
        if support.behavior == "analysis" and support.tier != "gpu":
            kind = "analysis"
        expected: OperationExpectation = (
            "allow_failure" if operation_name in DEFAULT_CONFIGURATION_FAILURES else "pass"
        )
        cases.append(
            OperationMatrixCase(
                operation_name=operation_name,
                kind=kind,
                support_tier=support.tier,
                is_analysis=support.behavior == "analysis",
                expected=expected,
            )
        )
    return tuple(cases)


def run_operation_matrix(
    input_path: Path,
    output_dir: Path | None = None,
    *,
    include_parameterized: bool = False,
    include_gpu: bool = False,
    include_special: bool = False,
) -> OperationMatrixResult:
    """Run each selected operation in a separate worker process.

    The matrix intentionally does not combine operations. A failed operation is
    captured in its own log and does not prevent subsequent checks from running.

    Args:
        input_path: USD fixture used as the input for every selected operation.
        output_dir: Directory for isolated USD outputs, logs, and manifest.
        include_parameterized: Include operations requiring asset-specific settings.
        include_gpu: Include operations that may require a compatible GPU.
        include_special: Include internal helper or explicitly destructive operations.

    Returns:
        Result containing all completed and skipped matrix steps.

    Raises:
        EnvironmentError: If the configured runtime is not usable.
    """
    status = check_environment()
    if not status.is_usable:
        problem_text = "; ".join(status.errors) if status.errors else "unknown problem"
        raise EnvironmentError(f"usd-optimize runtime is not usable: {problem_text}")

    resolved_input_path = input_path.expanduser().resolve()
    resolved_output_dir = (output_dir or DEFAULT_OPERATION_MATRIX_OUTPUT_DIR).expanduser().resolve()
    resolved_output_dir.mkdir(parents=True, exist_ok=True)
    staged_input_path = _stage_fixture(resolved_input_path, resolved_output_dir)

    steps: list[OperationMatrixStep] = []
    for case in build_operation_matrix_cases(list_available_operations()):
        if not _should_run(case, include_parameterized, include_gpu, include_special):
            steps.append(_skipped_step(case))
            continue
        steps.append(_run_case(case, staged_input_path, resolved_output_dir))

    manifest_path = resolved_output_dir / "operation-matrix.json"
    result = OperationMatrixResult(
        input_path=resolved_input_path,
        output_dir=resolved_output_dir,
        manifest_path=manifest_path,
        steps=tuple(steps),
    )
    _write_manifest(result)
    return result


def _should_run(
    case: OperationMatrixCase,
    include_parameterized: bool,
    include_gpu: bool,
    include_special: bool,
) -> bool:
    if case.kind == "parameterized":
        return include_parameterized
    if case.kind == "gpu":
        return include_gpu
    if case.kind == "special":
        return include_special
    return True


def _skipped_step(case: OperationMatrixCase) -> OperationMatrixStep:
    return OperationMatrixStep(
        operation_name=case.operation_name,
        kind=case.kind,
        support_tier=case.support_tier,
        expected=case.expected,
        status="skipped",
        output_path=None,
        output_reopened=None,
        error=_skip_reason(case),
    )


def _skip_reason(case: OperationMatrixCase) -> str:
    if case.kind == "parameterized":
        return "Use --include-parameterized to try the default operation configuration."
    if case.kind == "gpu":
        return "Use --include-gpu to run this hardware-dependent operation."
    return "Use --include-special to run this internal or explicitly destructive operation."


def _run_case(
    case: OperationMatrixCase,
    input_path: Path,
    output_dir: Path,
) -> OperationMatrixStep:
    output_path = input_path.parent / f"{input_path.stem}.{case.operation_name}.usda"
    preset = PresetDefinition(
        name=f"operation_matrix_{case.operation_name}",
        display_name=f"Operation Matrix: {case.operation_name}",
        risk="review",
        audience="developer",
        description="Isolated operation matrix check.",
        operations=[
            {
                "operation": "executionContext",
                "verbose": True,
                "analysisMode": case.is_analysis,
            },
            {"operation": case.operation_name},
        ],
        path=output_dir / f"{case.operation_name}.json",
    )
    try:
        run_optimization(
            OptimizeRequest(
                input_path=input_path,
                output_path=output_path,
                preset=preset,
                force=True,
                write_output=not case.is_analysis,
            )
        )
    except OptimizeError as error:
        return OperationMatrixStep(
            operation_name=case.operation_name,
            kind=case.kind,
            support_tier=case.support_tier,
            expected=case.expected,
            status="failed",
            output_path=None if case.is_analysis else output_path,
            output_reopened=None,
            error=str(error),
        )

    if case.is_analysis:
        return OperationMatrixStep(
            operation_name=case.operation_name,
            kind=case.kind,
            support_tier=case.support_tier,
            expected=case.expected,
            status="passed",
            output_path=None,
            output_reopened=None,
            error=None,
        )

    output_reopened = _stage_reopens(output_path)
    return OperationMatrixStep(
        operation_name=case.operation_name,
        kind=case.kind,
        support_tier=case.support_tier,
        expected=case.expected,
        status="passed" if output_reopened else "failed",
        output_path=output_path,
        output_reopened=output_reopened,
        error=None if output_reopened else "Output USD could not be reopened.",
    )


def _stage_fixture(input_path: Path, output_dir: Path) -> Path:
    """Copy a fixture directory so relative USD dependencies remain resolvable."""
    if not input_path.is_file():
        raise OptimizeError(f"Input USD does not exist: {input_path}")
    fixture_dir = output_dir / "fixture"
    ignored_names: tuple[str, ...] = ()
    try:
        output_relative_to_source = output_dir.relative_to(input_path.parent)
    except ValueError:
        pass
    else:
        ignored_names = (output_relative_to_source.parts[0],)
    ignore = shutil.ignore_patterns(*ignored_names) if ignored_names else None
    shutil.copytree(input_path.parent, fixture_dir, dirs_exist_ok=True, ignore=ignore)
    return fixture_dir / input_path.name


def _stage_reopens(output_path: Path) -> bool:
    """Return whether an exported output can be opened as a USD stage."""
    if not output_path.is_file():
        return False
    from pxr import Usd

    return Usd.Stage.Open(str(output_path)) is not None


def _write_manifest(result: OperationMatrixResult) -> None:
    """Write machine-readable matrix outcomes beside the generated outputs."""
    payload = {
        "input_path": str(result.input_path),
        "output_dir": str(result.output_dir),
        "unexpected_failure_count": len(result.unexpected_failures),
        "steps": [
            {
                **asdict(step),
                "output_path": str(step.output_path) if step.output_path else None,
            }
            for step in result.steps
        ],
    }
    result.manifest_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
