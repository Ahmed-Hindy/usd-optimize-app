from typing import Any

from usd_optimize_app.operation_support import ARTIST_SUPPORTED_OPERATIONS
from usd_optimize_app.operations import OPERATION_DLL_NAMES
from usd_optimize_app.presets import load_all_presets, load_preset, operation_names


def test_load_all_builtin_presets() -> None:
    user_presets = load_all_presets()
    all_presets = load_all_presets(include_developer=True)

    assert {preset.name for preset in user_presets} == {
        "diagnostics",
        "find_overlaps",
        "geometry_optimization",
        "safe_publish",
    }
    assert {preset.name for preset in all_presets} == {
        "aggressive_geometry",
        "animated_asset",
        "diagnostics",
        "find_overlaps",
        "geometry_optimization",
        "review_light",
        "safe_publish",
    }


def test_user_presets_only_use_artist_supported_operations() -> None:
    for preset in load_all_presets():
        asset_operations = set(operation_names(preset)) - {"executionContext"}
        assert asset_operations <= ARTIST_SUPPORTED_OPERATIONS


def test_all_bundled_preset_operations_are_registered() -> None:
    for preset in load_all_presets(include_developer=True):
        asset_operations = set(operation_names(preset)) - {"executionContext"}
        assert asset_operations <= OPERATION_DLL_NAMES.keys()


def test_geometry_optimization_uses_conservative_primvar_parameters() -> None:
    preset = load_preset("geometry_optimization")

    assert preset.display_name == "Geometry Optimization"
    assert preset.risk == "safe"
    assert preset.audience == "user"
    assert operation_names(preset) == [
        "executionContext",
        "computeExtents",
        "optimizePrimvars",
    ]
    assert _operation(preset.operations, "optimizePrimvars") == {
        "operation": "optimizePrimvars",
        "mode": 1,
        "simplify": True,
    }


def test_safe_publish_uses_explicit_conservative_parameters() -> None:
    preset = load_preset("safe_publish")

    assert preset.risk == "safe"
    assert operation_names(preset) == [
        "executionContext",
        "computeExtents",
        "optimizePrimvars",
        "optimizeMaterials",
        "optimizeTimeSamples",
    ]
    assert _operation(preset.operations, "optimizePrimvars") == {
        "operation": "optimizePrimvars",
        "mode": 1,
        "simplify": True,
        "removeIfBound": False,
    }
    assert _operation(preset.operations, "optimizeTimeSamples") == {
        "operation": "optimizeTimeSamples",
        "removeInterpolated": False,
        "epsilonD": 0.0,
        "epsilonF": 0.0,
    }


def test_animated_asset_avoids_structural_and_topology_operations() -> None:
    preset = load_preset("animated_asset")

    assert preset.display_name == "Developer: Animated Cleanup Comparison"
    assert preset.risk == "safe"
    assert preset.audience == "developer"
    assert operation_names(preset) == [
        "executionContext",
        "computeExtents",
        "optimizePrimvars",
        "optimizeMaterials",
        "optimizeTimeSamples",
    ]


def test_find_overlaps_is_a_read_only_analysis_preset() -> None:
    preset = load_preset("find_overlaps")

    assert preset.risk == "diagnostic"
    assert _operation(preset.operations, "findOverlappingMeshes") == {
        "operation": "findOverlappingMeshes",
        "useGpu": False,
        "reportIslands": True,
        "fullStageReport": True,
    }


def test_review_light_key_now_provides_static_viewport_workflow() -> None:
    preset = load_preset("review_light")

    assert preset.display_name == "Developer: Prototype Rewrite Test"
    assert preset.risk == "review"
    assert preset.audience == "developer"
    assert operation_names(preset) == [
        "executionContext",
        "computeExtents",
        "optimizePrimvars",
        "optimizeMaterials",
        "deduplicateGeometry",
        "organizePrototypes",
    ]
    assert _operation(preset.operations, "deduplicateGeometry") == {
        "operation": "deduplicateGeometry",
        "tolerance": 0.001,
        "duplicateMethod": 2,
        "fuzzy": False,
        "allowScaling": False,
    }
    assert _operation(preset.operations, "organizePrototypes") == {
        "operation": "organizePrototypes",
        "prototypesNamespace": "/Prototypes",
        "hierarchyLevels": 0,
    }


def _operation(operations: list[dict[str, Any]], operation_name: str) -> dict[str, Any]:
    """Return one operation config by name for precise preset assertions."""
    return next(operation for operation in operations if operation["operation"] == operation_name)
