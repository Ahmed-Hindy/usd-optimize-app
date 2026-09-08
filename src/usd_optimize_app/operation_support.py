"""Support classifications for the usd-optimize operation registry."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

OperationSupportTier = Literal[
    "supported",
    "advanced",
    "requires_configuration",
    "gpu",
    "internal",
]
OperationBehavior = Literal["write", "analysis"]


@dataclass(frozen=True)
class OperationSupport:
    """Product-facing support status for one registered operation."""

    name: str
    tier: OperationSupportTier
    behavior: OperationBehavior
    reason: str

    @property
    def is_artist_supported(self) -> bool:
        """Return whether the operation is exposed through a user preset."""
        return self.tier == "supported"


def _support(
    name: str,
    tier: OperationSupportTier,
    behavior: OperationBehavior,
    reason: str,
) -> OperationSupport:
    """Build one concise immutable support declaration."""
    return OperationSupport(name=name, tier=tier, behavior=behavior, reason=reason)


OPERATION_SUPPORT = {
    "boxClip": _support(
        "boxClip",
        "requires_configuration",
        "write",
        "Requires an explicit clip box and asset-specific path selection.",
    ),
    "computeExtents": _support(
        "computeExtents",
        "supported",
        "write",
        "Recomputes authored bounds without changing topology or hierarchy.",
    ),
    "countVertices": _support(
        "countVertices",
        "advanced",
        "write",
        "Developer metric without an end-user workflow by itself.",
    ),
    "decimateMeshes": _support(
        "decimateMeshes",
        "advanced",
        "write",
        "Changes visible mesh detail and needs review-specific quality targets.",
    ),
    "deduplicateGeometry": _support(
        "deduplicateGeometry",
        "advanced",
        "write",
        "Can rewrite geometry, references, transforms, and material bindings.",
    ),
    "deduplicateHierarchies": _support(
        "deduplicateHierarchies",
        "advanced",
        "write",
        "Can rewrite scene composition and hierarchy structure.",
    ),
    "deleteHiddenPrims": _support(
        "deleteHiddenPrims",
        "advanced",
        "write",
        "Deletes authored prims based on visibility and material state.",
    ),
    "deletePrims": _support(
        "deletePrims",
        "internal",
        "write",
        "Low-level deletion helper requiring explicit prim paths.",
    ),
    "diceMeshes": _support(
        "diceMeshes",
        "requires_configuration",
        "write",
        "Requires spatial partitioning parameters and purpose-built geometry.",
    ),
    "editStageMetrics": _support(
        "editStageMetrics",
        "requires_configuration",
        "write",
        "Changes stage scale or up-axis and needs an explicit target.",
    ),
    "findCoincidingGeometry": _support(
        "findCoincidingGeometry",
        "advanced",
        "write",
        "Developer analysis without a supported artist-facing result contract.",
    ),
    "findFlatHierarchies": _support(
        "findFlatHierarchies",
        "advanced",
        "write",
        "Developer analysis that suggests structural operations.",
    ),
    "findOccludedMeshes": _support(
        "findOccludedMeshes",
        "gpu",
        "analysis",
        "Depends on GPU visibility evaluation and hardware-specific behavior.",
    ),
    "findOverlappingMeshes": _support(
        "findOverlappingMeshes",
        "supported",
        "analysis",
        "Read-only CPU overlap analysis with structured prim-path results.",
    ),
    "fitPrimitives": _support(
        "fitPrimitives",
        "requires_configuration",
        "write",
        "Needs fit tolerances and asset-specific primitive targets.",
    ),
    "flattenHierarchy": _support(
        "flattenHierarchy",
        "advanced",
        "write",
        "Collapses hierarchy and can alter composition semantics.",
    ),
    "generateAtlasUVs": _support(
        "generateAtlasUVs",
        "requires_configuration",
        "write",
        "Needs UV generation settings and texture-layout review.",
    ),
    "generateNormals": _support(
        "generateNormals",
        "advanced",
        "write",
        "Authors shading data and may change the rendered result.",
    ),
    "generateProjectionUVs": _support(
        "generateProjectionUVs",
        "requires_configuration",
        "write",
        "Needs an explicit projection mode and asset-space assumptions.",
    ),
    "generateScene": _support(
        "generateScene",
        "internal",
        "write",
        "Test and helper operation rather than an optimization workflow.",
    ),
    "manifoldMeshes": _support(
        "manifoldMeshes",
        "advanced",
        "write",
        "Repairs topology and can change surface structure.",
    ),
    "merge": _support(
        "merge",
        "advanced",
        "write",
        "Combines prims and changes hierarchy, topology, and materials.",
    ),
    "mergeVertices": _support(
        "mergeVertices",
        "advanced",
        "write",
        "Changes topology using a tolerance that must be chosen per asset.",
    ),
    "meshCleanup": _support(
        "meshCleanup",
        "advanced",
        "write",
        "Can remove or rewrite malformed geometry.",
    ),
    "moveMaterials": _support(
        "moveMaterials",
        "advanced",
        "write",
        "Moves material prims with namespace edits and changes authored hierarchy.",
    ),
    "optimizeMaterials": _support(
        "optimizeMaterials",
        "supported",
        "write",
        "Deduplicates material data while preserving tested bindings.",
    ),
    "optimizePrimvars": _support(
        "optimizePrimvars",
        "supported",
        "write",
        "Indexes repeated primvars without removing bound values.",
    ),
    "optimizeSkelRoots": _support(
        "optimizeSkelRoots",
        "advanced",
        "write",
        "Skeleton-specific rewrite needing rigged-asset validation.",
    ),
    "optimizeTimeSamples": _support(
        "optimizeTimeSamples",
        "supported",
        "write",
        "Removes exact redundant samples while preserving authored motion.",
    ),
    "organizePrototypes": _support(
        "organizePrototypes",
        "advanced",
        "write",
        "Rehomes instance prototypes and rewrites references.",
    ),
    "pivot": _support(
        "pivot",
        "requires_configuration",
        "write",
        "Requires a pivot policy and transform-space intent.",
    ),
    "primitivesToMeshes": _support(
        "primitivesToMeshes",
        "advanced",
        "write",
        "Converts authored primitive schemas into meshes.",
    ),
    "printStats": _support(
        "printStats",
        "supported",
        "analysis",
        "Read-only stage statistics used by the Inspect workflow.",
    ),
    "pruneLeaves": _support(
        "pruneLeaves",
        "advanced",
        "write",
        "Deletes empty terminal prims and is not structurally lossless.",
    ),
    "pythonScript": _support(
        "pythonScript",
        "internal",
        "write",
        "Executes arbitrary Python and is not exposed to artists.",
    ),
    "remeshMeshes": _support(
        "remeshMeshes",
        "advanced",
        "write",
        "Rebuilds topology and needs quality and performance targets.",
    ),
    "removeAttributes": _support(
        "removeAttributes",
        "requires_configuration",
        "write",
        "Requires an explicit attribute allowlist or removal pattern.",
    ),
    "removePrims": _support(
        "removePrims",
        "requires_configuration",
        "write",
        "Requires explicit selection and removal semantics.",
    ),
    "removeSmallGeometry": _support(
        "removeSmallGeometry",
        "advanced",
        "write",
        "Deletes geometry according to scene-scale thresholds.",
    ),
    "removeUntypedPrims": _support(
        "removeUntypedPrims",
        "advanced",
        "write",
        "Deletes untyped authored prims and may remove intentional structure.",
    ),
    "removeUnusedUVs": _support(
        "removeUnusedUVs",
        "advanced",
        "write",
        "Removes UV data based on material usage assumptions.",
    ),
    "rtxMeshCount": _support(
        "rtxMeshCount",
        "advanced",
        "analysis",
        "Diagnostic metric without a standalone end-user workflow.",
    ),
    "shrinkwrap": _support(
        "shrinkwrap",
        "requires_configuration",
        "write",
        "Needs voxel resolution and output-detail settings.",
    ),
    "sparseMeshes": _support(
        "sparseMeshes",
        "advanced",
        "analysis",
        "Developer analysis recommending split or dice operations.",
    ),
    "splitMeshes": _support(
        "splitMeshes",
        "requires_configuration",
        "write",
        "Requires clustering and split-mode parameters.",
    ),
    "subdivideMeshes": _support(
        "subdivideMeshes",
        "requires_configuration",
        "write",
        "Requires subdivision level and topology expectations.",
    ),
    "triangulateMeshes": _support(
        "triangulateMeshes",
        "advanced",
        "write",
        "Changes topology and can affect downstream interpolation.",
    ),
    "utilityFunction": _support(
        "utilityFunction",
        "internal",
        "write",
        "Generic helper entry point, not a stable product workflow.",
    ),
}

ARTIST_SUPPORTED_OPERATIONS = frozenset(
    name for name, support in OPERATION_SUPPORT.items() if support.is_artist_supported
)


def get_operation_support(operation_name: str) -> OperationSupport:
    """Return the declared support status for a registered operation.

    Args:
        operation_name: Public usd-optimize operation name.

    Returns:
        Declared support metadata.

    Raises:
        KeyError: If the operation has not been classified.
    """
    return OPERATION_SUPPORT[operation_name]
