from usd_optimize_app.operations import (
    OPERATION_DLL_NAMES,
    get_operation_presentation,
    operation_name_from_dll_stem,
)


def test_operation_name_from_matching_dll_stem() -> None:
    assert operation_name_from_dll_stem("merge") == "merge"


def test_operation_name_from_mismatched_dll_stem() -> None:
    assert operation_name_from_dll_stem("utilityFunctions") == "utilityFunction"


def test_operation_registry_includes_find_overlapping_meshes() -> None:
    assert OPERATION_DLL_NAMES["findOverlappingMeshes"] == "findOverlappingMeshes.dll"


def test_operation_presentation_is_readable_and_categorized() -> None:
    presentation = get_operation_presentation("decimateMeshes")

    assert presentation.label == "Decimate meshes"
    assert presentation.category == "Geometry"
    assert "detail" in presentation.description


def test_new_preset_operations_have_artist_facing_presentations() -> None:
    expected_categories = {
        "optimizePrimvars": "Geometry data",
        "organizePrototypes": "Instancing",
    }

    for operation_name, expected_category in expected_categories.items():
        presentation = get_operation_presentation(operation_name)
        assert presentation.label != operation_name
        assert presentation.category == expected_category
        assert presentation.description != operation_name
