from __future__ import annotations

import pytest

from usd_optimize_app.errors import PresetError
from usd_optimize_app.operation_scope import (
    build_operation_scope_plan,
    normalize_prim_paths,
    scoped_operation_skip_reason,
)


def test_normalize_prim_paths_collapses_duplicate_descendants() -> None:
    assert normalize_prim_paths(
        ("/World/Asset/Mesh", "/World/Asset", "/World/Other", "/World/Asset")
    ) == ("/World/Asset", "/World/Other")


def test_scope_plan_owns_normalized_roots_and_operation_names() -> None:
    operations = [
        {"operation": "executionContext", "verbose": True},
        {"operation": "computeExtents"},
        {"operation": "optimizePrimvars", "mode": 1},
        {"operation": "optimizeTimeSamples"},
        {"operation": "findOverlappingMeshes", "useGpu": False},
    ]

    plan = build_operation_scope_plan(
        operations,
        ("/World/Asset/Mesh", "/World/Asset", "/World/Other"),
    )

    expected_scope = ["/World/Asset//", "/World/Other//"]
    assert plan.prim_paths == ("/World/Asset", "/World/Other")
    assert plan.operation_names == (
        "executionContext",
        "computeExtents",
        "optimizePrimvars",
        "optimizeTimeSamples",
        "findOverlappingMeshes",
    )
    assert "paths" not in plan.operations[0]
    assert plan.operations[1]["paths"] == expected_scope
    assert plan.operations[2]["paths"] == expected_scope
    assert plan.operations[3]["paths"] == expected_scope
    assert plan.operations[4]["paths"] == expected_scope
    assert plan.warnings == ()
    assert operations[1] == {"operation": "computeExtents"}


def test_scoped_material_optimization_is_explicitly_skipped() -> None:
    operations = [
        {"operation": "executionContext", "verbose": True},
        {"operation": "optimizeMaterials"},
        {"operation": "computeExtents"},
    ]

    plan = build_operation_scope_plan(operations, ("/World/Asset",))

    assert plan.operation_names == ("executionContext", "computeExtents")
    assert scoped_operation_skip_reason("optimizeMaterials") in plan.warnings[0]
    assert plan.warnings == (
        "Skipped optimizeMaterials: Material deduplication can rebind consumers outside the "
        "selected hierarchy.",
    )


def test_empty_selection_preserves_whole_stage_config() -> None:
    operations = [
        {"operation": "executionContext", "verbose": True},
        {"operation": "optimizeMaterials"},
        {"operation": "computeExtents"},
    ]

    plan = build_operation_scope_plan(operations, ())

    assert plan.prim_paths == ()
    assert plan.operations == operations
    assert plan.operations is not operations
    assert "optimizeMaterials" in plan.operation_names
    assert plan.warnings == ()


def test_scoped_unknown_operation_fails_instead_of_processing_whole_stage() -> None:
    with pytest.raises(PresetError, match="does not have a reviewed prim-selection contract"):
        build_operation_scope_plan([{"operation": "meshCleanup"}], ("/World/Asset",))


def test_scope_rejects_invalid_or_preconfigured_paths() -> None:
    with pytest.raises(PresetError, match="Invalid selected prim path"):
        normalize_prim_paths(("World/Asset",))

    with pytest.raises(PresetError, match="already defines"):
        build_operation_scope_plan(
            [{"operation": "computeExtents", "paths": ["/Existing//"]}],
            ("/World/Asset",),
        )
