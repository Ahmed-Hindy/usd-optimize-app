from usd_optimize_app.operation_support import (
    ARTIST_SUPPORTED_OPERATIONS,
    OPERATION_SUPPORT,
    get_operation_support,
)

EXPECTED_RUNTIME_OPERATIONS = {
    "boxClip",
    "computeExtents",
    "countVertices",
    "decimateMeshes",
    "deduplicateGeometry",
    "deduplicateHierarchies",
    "deleteHiddenPrims",
    "deletePrims",
    "diceMeshes",
    "editStageMetrics",
    "findCoincidingGeometry",
    "findFlatHierarchies",
    "findOccludedMeshes",
    "findOverlappingMeshes",
    "fitPrimitives",
    "flattenHierarchy",
    "generateAtlasUVs",
    "generateNormals",
    "generateProjectionUVs",
    "generateScene",
    "manifoldMeshes",
    "merge",
    "mergeVertices",
    "meshCleanup",
    "optimizeMaterials",
    "optimizePrimvars",
    "optimizeSkelRoots",
    "optimizeTimeSamples",
    "organizePrototypes",
    "pivot",
    "primitivesToMeshes",
    "printStats",
    "pruneLeaves",
    "pythonScript",
    "remeshMeshes",
    "removeAttributes",
    "removePrims",
    "removeSmallGeometry",
    "removeUntypedPrims",
    "removeUnusedUVs",
    "rtxMeshCount",
    "shrinkwrap",
    "sparseMeshes",
    "splitMeshes",
    "subdivideMeshes",
    "triangulateMeshes",
    "utilityFunction",
}


def test_every_runtime_operation_has_a_support_classification() -> None:
    assert set(OPERATION_SUPPORT) == EXPECTED_RUNTIME_OPERATIONS


def test_artist_supported_operations_are_intentionally_small() -> None:
    assert ARTIST_SUPPORTED_OPERATIONS == {
        "computeExtents",
        "findOverlappingMeshes",
        "optimizeMaterials",
        "optimizePrimvars",
        "optimizeTimeSamples",
        "printStats",
    }


def test_destructive_helpers_are_not_artist_supported() -> None:
    assert get_operation_support("pruneLeaves").tier == "advanced"
    assert get_operation_support("pythonScript").tier == "internal"
    assert get_operation_support("boxClip").tier == "requires_configuration"
