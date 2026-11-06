# Operations & Support Reference

The bundled NVIDIA `usd-optimize` v1.4.0 runtime registers 50 operations. Because many operations alter mesh topology, flatten hierarchies, or require asset-specific parameters, `usd-optimize-app` groups them into five support tiers (defined in [`src/usd_optimize_app/operation_support.py`](../src/usd_optimize_app/operation_support.py)):

| Tier | Count | Policy |
| --- | ---: | --- |
| **Supported** | 6 | Safe for general workflows; preserves hierarchy and mesh topology, or runs read-only CPU analysis. |
| **Advanced** | 27 | Modifies topology, hierarchy, materials, or schemas; exposed only via developer presets and the operation matrix. |
| **Requires configuration** | 12 | Needs explicit asset-specific parameters (boxes, paths, tolerances, UV projections) to run meaningfully. |
| **GPU-dependent** | 1 | Requires compatible GPU visibility hardware (`findOccludedMeshes`). |
| **Internal** | 4 | Low-level helpers or scripting entry points (`deletePrims`, `generateScene`, `pythonScript`, `utilityFunction`). |

> **Note:** `executionContext` appears in preset JSON files to configure logging and analysis flags, but is not a registered operation.

---

## Operations in Bundled Presets

The four user-facing presets are **Safe Cleanup** (`safe_publish`), **Geometry Optimization** (`geometry_optimization`), **Inspect Stage** (`diagnostics`), and **Find Overlaps** (`find_overlaps`). The remaining presets are developer-only (`usdopt list-presets --all`).

In the supported presets, `optimizePrimvars` indexes and simplifies primvars without removing bound data, `optimizeTimeSamples` strips only exact duplicate samples (interpolation removal disabled), and `findOverlappingMeshes` runs with `useGpu: false` for deterministic CPU behavior.

| Operation | What it does | Tier | Bundled preset(s) |
| --- | --- | --- | --- |
| `computeExtents` | Computes and authors mesh `extents`. | Supported (writes USD) | Safe Cleanup, Geometry Optimization, Animated Cleanup Comparison, Prototype Rewrite Test |
| `optimizeMaterials` | Deduplicates materials and rebinds consumers to unique materials. | Supported (writes USD) | Safe Cleanup, Animated Cleanup Comparison, Prototype Rewrite Test |
| `optimizePrimvars` | Simplifies, indexes, or flattens primvar storage. | Supported (writes USD) | Safe Cleanup, Geometry Optimization, Animated Cleanup Comparison, Prototype Rewrite Test |
| `optimizeTimeSamples` | Removes exact duplicate time samples across attributes. | Supported (writes USD) | Safe Cleanup, Animated Cleanup Comparison |
| `printStats` | Collects read-only stage statistics. | Supported (read-only) | Inspect Stage |
| `findOverlappingMeshes` | Detects intersecting meshes (configured for deterministic CPU execution). | Supported (read-only) | Find Overlaps |
| `decimateMeshes` | Reduces mesh polygon count within quality/error limits. | Advanced (writes USD) | Destructive Geometry Stress |
| `deduplicateGeometry` | Replaces duplicate meshes with references or instances. | Advanced (writes USD) | Destructive Geometry Stress, Prototype Rewrite Test |
| `flattenHierarchy` | Collapses redundant `Xform` prims. | Advanced (writes USD) | Destructive Geometry Stress |
| `merge` | Combines compatible meshes into a single mesh. | Advanced (writes USD) | Destructive Geometry Stress |
| `moveMaterials` | Moves material prims via namespace edits. | Advanced (writes USD) | Developer operation matrix |
| `organizePrototypes` | Reparents scene-graph instance prototypes under a target namespace. | Advanced (writes USD) | Prototype Rewrite Test |

---

## Other Runtime Operations

| Operation | What it does | Tier |
| --- | --- | --- |
| `boxClip` | Clips geometry to an explicit bounding box. | Requires configuration (writes USD) |
| `conformMeshes` | Reconciles normals, UVs, primvars, and `doubleSided` so meshes can be merged. | Advanced (writes USD) |
| `countVertices` | Reports prims exceeding a vertex threshold. | Advanced (writes USD) |
| `deduplicateHierarchies` | Replaces duplicate prim subtrees with instanceable internal references. | Advanced (writes USD) |
| `deleteHiddenPrims` | Deletes constantly hidden prims. | Advanced (writes USD) |
| `deletePrims` | Deletes explicitly named prims. | Internal (writes USD) |
| `diceMeshes` | Splits meshes using spatial dicing intervals. | Requires configuration (writes USD) |
| `editStageMetrics` | Modifies stage `metersPerUnit` or `upAxis` metadata. | Requires configuration (writes USD) |
| `findCoincidingGeometry` | Identifies geometry occupying identical space. | Advanced (writes USD) |
| `findFlatHierarchies` | Reports prims exceeding a child-count threshold. | Advanced (writes USD) |
| `findOccludedMeshes` | Finds meshes occluded from camera viewpoints. | GPU-dependent (read-only) |
| `fitPrimitives` | Replaces meshes matching sphere, cylinder, cone, or cube shapes within tolerance. | Requires configuration (writes USD) |
| `generateAtlasUVs` | Generates atlas UVs from texture-layout parameters. | Requires configuration (writes USD) |
| `generateNormals` | Computes and authors mesh normals. | Advanced (writes USD) |
| `generateProjectionUVs` | Generates UVs using an explicit projection mode. | Requires configuration (writes USD) |
| `generateScene` | Test helper that generates synthetic scenes. | Internal (writes USD) |
| `manifoldMeshes` | Repairs non-manifold mesh topology. | Advanced (writes USD) |
| `mergePhysicsBodyMeshes` | Merges compatible visual and collision meshes within rigid bodies. | Advanced (writes USD) |
| `mergeVertices` | Welds vertices within a distance tolerance. | Advanced (writes USD) |
| `meshCleanup` | Removes degenerate faces, isolated vertices, and non-manifold geometry. | Advanced (writes USD) |
| `optimizeSkelRoots` | Merges skinned meshes under a skeleton root. | Advanced (writes USD) |
| `pivot` | Centers a prim's parent transform pivot on its bounding box. | Requires configuration (writes USD) |
| `primitivesToMeshes` | Converts analytic sphere, cylinder, cone, and cube gprims into meshes. | Advanced (writes USD) |
| `pruneLeaves` | Removes empty leaf grouping prims (`Xform`, `Scope`). | Advanced (writes USD) |
| `pythonScript` | Runs arbitrary Python code inside the optimization pipeline. | Internal (writes USD) |
| `remeshMeshes` | Rebuilds mesh topology to a target tolerance. | Advanced (writes USD) |
| `removeAttributes` | Strips attributes matching explicit patterns. | Requires configuration (writes USD) |
| `removePrims` | Removes prims matching selection rules. | Requires configuration (writes USD) |
| `removeSmallGeometry` | Deletes small or degenerate geometry. | Advanced (writes USD) |
| `removeUntypedPrims` | Deletes untyped prims. | Advanced (writes USD) |
| `removeUnusedUVs` | Strips UV primvars not referenced by bound materials. | Advanced (writes USD) |
| `rtxMeshCount` | Counts total and unique RTX meshes in the stage. | Advanced (read-only) |
| `shrinkwrap` | Converts meshes to a level-set volume and extracts a watertight mesh. | Requires configuration (writes USD) |
| `sparseMeshes` | Analyzes sparse meshes and recommends optimizations. | Advanced (read-only) |
| `splitMeshes` | Splits disconnected mesh islands into separate mesh prims. | Requires configuration (writes USD) |
| `subdivideMeshes` | Applies Catmull-Clark or Loop subdivision to meshes. | Requires configuration (writes USD) |
| `triangulateMeshes` | Triangulates polygonal mesh faces. | Advanced (writes USD) |
| `utilityFunction` | Runs utility tasks (deinstancing, material unbinding, instance flattening). | Internal (writes USD) |
