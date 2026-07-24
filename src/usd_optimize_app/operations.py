"""usd-optimize operation registry helpers."""

from __future__ import annotations

from dataclasses import dataclass

OPERATION_DLL_NAMES = {
    "boxClip": "boxClip.dll",
    "computeExtents": "computeExtents.dll",
    "countVertices": "countVertices.dll",
    "decimateMeshes": "decimateMeshes.dll",
    "deduplicateGeometry": "deduplicateGeometry.dll",
    "deduplicateHierarchies": "deduplicateHierarchies.dll",
    "deletePrims": "deletePrims.dll",
    "diceMeshes": "diceMeshes.dll",
    "editStageMetrics": "editStageMetrics.dll",
    "findCoincidingGeometry": "findCoincidingGeometry.dll",
    "findFlatHierarchies": "findFlatHierarchies.dll",
    "findOccludedMeshes": "findOccludedMeshes.dll",
    "findOverlappingMeshes": "findOverlappingMeshes.dll",
    "fitPrimitives": "fitPrimitives.dll",
    "flattenHierarchy": "flattenHierarchy.dll",
    "generateAtlasUVs": "generateAtlasUVs.dll",
    "generateNormals": "generateNormals.dll",
    "generateProjectionUVs": "generateProjectionUVs.dll",
    "generateScene": "generateScene.dll",
    "manifoldMeshes": "manifoldMeshes.dll",
    "merge": "merge.dll",
    "mergeVertices": "mergeVertices.dll",
    "meshCleanup": "meshCleanup.dll",
    "optimizeMaterials": "optimizeMaterials.dll",
    "optimizePrimvars": "optimizePrimvars.dll",
    "optimizeSkelRoots": "optimizeSkelRoots.dll",
    "optimizeTimeSamples": "optimizeTimeSamples.dll",
    "organizePrototypes": "organizePrototypes.dll",
    "pivot": "pivot.dll",
    "primitivesToMeshes": "primitivesToMeshes.dll",
    "printStats": "printStats.dll",
    "pruneLeaves": "pruneLeaves.dll",
    "remeshMeshes": "remeshMeshes.dll",
    "removeAttributes": "removeAttributes.dll",
    "removePrims": "removePrims.dll",
    "removeSmallGeometry": "removeSmallGeometry.dll",
    "removeUnusedUVs": "removeUnusedUVs.dll",
    "rtxMeshCount": "rtxMeshCount.dll",
    "shrinkwrap": "shrinkwrap.dll",
    "sparseMeshes": "sparseMeshes.dll",
    "splitMeshes": "splitMeshes.dll",
    "subdivideMeshes": "subdivideMeshes.dll",
    "triangulateMeshes": "triangulateMeshes.dll",
    "utilityFunction": "utilityFunctions.dll",
}

_OPERATION_NAMES_BY_DLL_STEM = {
    dll_name.removesuffix(".dll"): operation_name
    for operation_name, dll_name in OPERATION_DLL_NAMES.items()
}


@dataclass(frozen=True)
class OperationPresentation:
    """Human-facing context for an operation exposed by a bundled profile."""

    label: str
    category: str
    description: str


OPERATION_PRESENTATIONS = {
    "computeExtents": OperationPresentation(
        "Compute extents", "Scene cleanup", "Recalculate bounds for scene prims."
    ),
    "optimizeMaterials": OperationPresentation(
        "Optimize materials", "Materials", "Remove redundant material data."
    ),
    "optimizePrimvars": OperationPresentation(
        "Optimize primvars",
        "Geometry data",
        "Index repeated primvar values and simplify uniform primvars without removing bound data.",
    ),
    "pruneLeaves": OperationPresentation(
        "Prune empty leaves", "Scene cleanup", "Remove empty terminal prims."
    ),
    "optimizeTimeSamples": OperationPresentation(
        "Optimize time samples", "Animation", "Reduce redundant animated samples."
    ),
    "printStats": OperationPresentation(
        "Inspect stage",
        "Diagnostics",
        "Collect scene statistics without changing the source stage.",
    ),
    "findOverlappingMeshes": OperationPresentation(
        "Find overlaps",
        "Analysis",
        "Report intersecting mesh islands without writing a USD derivative.",
    ),
    "deduplicateGeometry": OperationPresentation(
        "Deduplicate geometry", "Geometry", "Share duplicate geometry where possible."
    ),
    "organizePrototypes": OperationPresentation(
        "Organize prototypes",
        "Instancing",
        "Collect internal instance prototypes under a dedicated namespace and rewrite references.",
    ),
    "merge": OperationPresentation(
        "Merge geometry", "Geometry", "Combine compatible geometry into fewer prims."
    ),
    "flattenHierarchy": OperationPresentation(
        "Flatten hierarchy", "Hierarchy", "Collapse hierarchy levels; can change scene structure."
    ),
    "decimateMeshes": OperationPresentation(
        "Decimate meshes", "Geometry", "Reduce mesh complexity; can change visible detail."
    ),
}


def operation_name_from_dll_stem(dll_stem: str) -> str:
    """Return the usd-optimize operation name for a DLL stem.

    Args:
        dll_stem: DLL file stem without the `.dll` suffix.

    Returns:
        Public operation name used in usd-optimize configs.
    """
    return _OPERATION_NAMES_BY_DLL_STEM.get(dll_stem, dll_stem)


def get_operation_presentation(operation_name: str) -> OperationPresentation:
    """Return a readable operation label and explanation for the GUI."""
    presentation = OPERATION_PRESENTATIONS.get(operation_name)
    if presentation is not None:
        return presentation
    return OperationPresentation(operation_name, "Advanced", operation_name)
