"""Plan hierarchy-scoped NVIDIA usd-optimize operations."""

from __future__ import annotations

from collections.abc import Iterable
from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from usd_optimize_app.errors import PresetError

_MATERIAL_SCOPE_WARNING = (
    "Material deduplication can rebind consumers outside the selected hierarchy."
)


@dataclass(frozen=True)
class _OperationScopeRule:
    """How one operation behaves when hierarchy scope is active."""

    argument_name: str | None = None
    skip_reason: str | None = None


_OPERATION_SCOPE_RULES = {
    "computeExtents": _OperationScopeRule(argument_name="paths"),
    "findOverlappingMeshes": _OperationScopeRule(argument_name="paths"),
    "optimizeMaterials": _OperationScopeRule(skip_reason=_MATERIAL_SCOPE_WARNING),
    "optimizePrimvars": _OperationScopeRule(argument_name="paths"),
    "optimizeTimeSamples": _OperationScopeRule(argument_name="paths"),
}


@dataclass(frozen=True)
class OperationScopePlan:
    """Normalized roots and exact operations prepared for execution."""

    prim_paths: tuple[str, ...]
    operations: list[dict[str, Any]]
    warnings: tuple[str, ...] = ()

    @property
    def operation_names(self) -> tuple[str, ...]:
        """Return configured operation names in plan order."""
        return tuple(
            operation_name
            for operation in self.operations
            if isinstance(operation_name := operation.get("operation"), str)
        )


def normalize_prim_paths(prim_paths: Iterable[str]) -> tuple[str, ...]:
    """Validate, deduplicate, and collapse selected descendant paths."""
    normalized_paths: set[str] = set()
    for raw_path in prim_paths:
        prim_path = raw_path.strip().rstrip("/")
        if not prim_path or prim_path == "/" or not prim_path.startswith("/"):
            raise PresetError(f"Invalid selected prim path: {raw_path!r}")
        normalized_paths.add(prim_path)

    roots: list[str] = []
    for prim_path in sorted(normalized_paths, key=lambda path: (path.count("/"), path)):
        if any(prim_path.startswith(f"{root}/") for root in roots):
            continue
        roots.append(prim_path)
    return tuple(roots)


def scoped_operation_skip_reason(operation_name: str) -> str | None:
    """Return why an operation is omitted from prim-scoped execution."""
    rule = _OPERATION_SCOPE_RULES.get(operation_name)
    return rule.skip_reason if rule is not None else None


def build_operation_scope_plan(
    operations: list[dict[str, Any]],
    prim_paths: Iterable[str],
) -> OperationScopePlan:
    """Build the exact operation plan for a whole-stage or prim-scoped job.

    Whole-stage jobs preserve the preset unchanged. Prim-scoped jobs inject the
    reviewed NVIDIA path argument, omit operations that cannot preserve the
    hierarchy boundary, and reject unknown operations rather than widening the
    job to the complete stage.
    """
    normalized_paths = normalize_prim_paths(prim_paths)
    if not normalized_paths:
        return OperationScopePlan((), deepcopy(operations))

    expressions = [f"{prim_path}//" for prim_path in normalized_paths]
    scoped_operations: list[dict[str, Any]] = []
    warnings: list[str] = []

    for source_operation in operations:
        operation_data = deepcopy(source_operation)
        operation_name = operation_data.get("operation")
        if operation_name == "executionContext":
            scoped_operations.append(operation_data)
            continue
        if not isinstance(operation_name, str):
            raise PresetError("Preset operation is missing a valid operation name.")

        rule = _OPERATION_SCOPE_RULES.get(operation_name)
        if rule is None:
            raise PresetError(
                f"Operation {operation_name!r} does not have a reviewed prim-selection contract."
            )
        if rule.skip_reason is not None:
            warnings.append(f"Skipped {operation_name}: {rule.skip_reason}")
            continue
        if rule.argument_name is None:
            raise PresetError(f"Operation {operation_name!r} has an invalid scope rule.")
        if operation_data.get(rule.argument_name):
            raise PresetError(
                f"Operation {operation_name!r} already defines {rule.argument_name!r}; "
                "it cannot be combined with a GUI prim selection."
            )

        operation_data[rule.argument_name] = expressions
        scoped_operations.append(operation_data)

    return OperationScopePlan(normalized_paths, scoped_operations, tuple(warnings))
