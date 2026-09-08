# Runtime Operations Reference

The bundled NVIDIA `usd-optimize` 1.2.1 runtime registers 48 operations. The
**What it does** text has been verified against NVIDIA's official [Scene
Optimizer operations documentation](https://docs.omniverse.nvidia.com/extensions/latest/ext_scene-optimizer/operations.html)
and, for operations not published on that page, the operation description in
the previously reviewed NVIDIA 1.1.0 source checkout. The added `moveMaterials`
entry follows the shipped 1.2.1 changelog. This reference describes
the operation's behavior, not this app's safety policy.

`executionContext`, which appears in every preset, is not an operation in this
registry. It supplies execution flags such as verbose logging and analysis mode.

## Bundled-workflow operations

| Operation | What it does | Support | Bundled preset(s) |
| --- | --- | --- | --- |
| `computeExtents` | Computes or recomputes and authors the `extents` property for meshes. | Supported; writes USD | Safe Cleanup; Animated Cleanup Comparison; Prototype Rewrite Test |
| `decimateMeshes` | Reduces mesh tessellation density subject to configured quality/error limits. | Advanced; writes USD | Destructive Geometry Stress |
| `deduplicateGeometry` | Replaces duplicate meshes with one mesh plus references or instances to it. | Advanced; writes USD | Destructive Geometry Stress; Prototype Rewrite Test |
| `moveMaterials` | Moves material prims using USD namespace edits, changing their hierarchy. | Advanced; writes USD | Developer operation matrix |
| `findOverlappingMeshes` | Finds interfering geometry in a stage. | Supported; read-only analysis | Find Overlaps |
| `flattenHierarchy` | Removes redundant `Xform` prims to reduce prim count. | Advanced; writes USD | Destructive Geometry Stress |
| `merge` | Replaces meshes that share common properties with a single merged mesh. | Advanced; writes USD | Destructive Geometry Stress |
| `optimizeMaterials` | Replaces duplicate materials with references to unique materials. | Supported; writes USD | Safe Cleanup; Animated Cleanup Comparison; Prototype Rewrite Test |
| `optimizePrimvars` | Simplifies primvar data and can index or flatten primvars. | Supported; writes USD | Safe Cleanup; Animated Cleanup Comparison; Prototype Rewrite Test |
| `optimizeTimeSamples` | Removes redundant time samples from attributes throughout a stage. | Supported; writes USD | Safe Cleanup; Animated Cleanup Comparison |
| `organizePrototypes` | Reparents internal scene-graph instance prototypes under a user-specified namespace. | Advanced; writes USD | Prototype Rewrite Test |
| `printStats` | Collects read-only stage statistics. | Supported; read-only analysis | Inspect Stage |

The first three columns describe the runtime behavior; a preset can further
constrain it with fixed configuration. The three user-facing presets are Safe
Cleanup, Inspect Stage, and Find Overlaps. The remaining listed presets are
developer-only and appear with `usdopt list-presets --all`.

## Available, but not used by a bundled preset

| Operation | What it does | Support |
| --- | --- | --- |
| `boxClip` | Clips selected content to an explicit box. | Requires configuration; writes USD |
| `countVertices` | Reports prims with excessive vertex counts. | Advanced; writes USD |
| `deduplicateHierarchies` | Finds duplicate prim hierarchies and replaces duplicates with instanceable internal references to a prototype. | Advanced; writes USD |
| `deleteHiddenPrims` | Deletes prims that are constantly hidden. | Advanced; writes USD |
| `deletePrims` | Low-level deletion of explicitly named prims. | Internal; writes USD |
| `diceMeshes` | Partitions meshes using spatial dicing parameters. | Requires configuration; writes USD |
| `editStageMetrics` | Changes stage scale or up-axis metadata. | Requires configuration; writes USD |
| `findCoincidingGeometry` | Finds geometry occupying the same positional space in a scene. | Advanced; writes USD |
| `findFlatHierarchies` | Finds prims with more than a specified number of children. | Advanced; writes USD |
| `findOccludedMeshes` | Finds meshes occluded from any camera whose sightline does not cross meshes in the scene. | GPU-dependent; read-only analysis |
| `fitPrimitives` | Fits sphere, cylinder, cone, or cube primitives to selected meshes and replaces meshes that fit within tolerance. | Requires configuration; writes USD |
| `generateAtlasUVs` | Generates atlas UVs using texture-layout settings. | Requires configuration; writes USD |
| `generateNormals` | Authors mesh normal/shading data. | Advanced; writes USD |
| `generateProjectionUVs` | Generates UVs with an explicit projection mode. | Requires configuration; writes USD |
| `generateScene` | Provides a test/helper scene-generation operation. | Internal; writes USD |
| `manifoldMeshes` | Repairs mesh topology to make meshes manifold. | Advanced; writes USD |
| `mergeVertices` | Merges vertices using a configured tolerance. | Advanced; writes USD |
| `meshCleanup` | Cleans meshes, for example by merging nearby vertices, removing degenerate faces, making meshes manifold, or removing isolated vertices. | Advanced; writes USD |
| `optimizeSkelRoots` | Merges meshes attached to a skeleton to optimize GPU skinning computation. | Advanced; writes USD |
| `pivot` | Places a target prim's parent transform at the center of its bounding box. | Requires configuration; writes USD |
| `primitivesToMeshes` | Replaces sphere, cylinder, cone, and cube gprims with mesh approximations. | Advanced; writes USD |
| `pruneLeaves` | Finds and prunes leaf grouping prims such as `Xform` and `Scope`. | Advanced; writes USD |
| `pythonScript` | Executes arbitrary Python supplied to the operation. | Internal; writes USD |
| `remeshMeshes` | Remeshes input `UsdGeom` mesh prims to a defined tolerance, creating new topology. | Advanced; writes USD |
| `removeAttributes` | Removes attributes or namespaces matched by explicit rules. | Requires configuration; writes USD |
| `removePrims` | Removes selected prims using explicit selection semantics. | Requires configuration; writes USD |
| `removeSmallGeometry` | Identifies and removes small or degenerate geometry from a USD stage. | Advanced; writes USD |
| `removeUntypedPrims` | Deletes untyped authored prims. | Advanced; writes USD |
| `removeUnusedUVs` | Removes UV data based on material-usage assumptions. | Advanced; writes USD |
| `rtxMeshCount` | Counts RTX meshes in the stage and how many are unique. | Advanced; read-only analysis |
| `shrinkwrap` | Converts meshes to a level-set volume and extracts a watertight mesh. | Requires configuration; writes USD |
| `sparseMeshes` | Analyzes sparse meshes in a scene and suggests optimizations. | Advanced; read-only analysis |
| `splitMeshes` | Splits disjoint parts of meshes that share no vertices into separate mesh prims. | Requires configuration; writes USD |
| `subdivideMeshes` | Applies Catmull-Clark or Loop subdivision, replacing mesh topology with the subdivided result. | Requires configuration; writes USD |
| `triangulateMeshes` | Converts mesh faces to triangles. | Advanced; writes USD |
| `utilityFunction` | Provides simple utilities such as deinstancing, unbinding materials, setting instanceability, and flattening instances. | Internal; writes USD |

## How to inspect the current runtime

The app queries the installed runtime rather than assuming this list:

```powershell
uv run usdopt list-operations
```

For the product support policy and validation details, see
[Operation Support Matrix](operation-support.md).
