# Operation Support Matrix

NVIDIA `usd-optimize` v1.2.1 registers 48 operations in the bundled Windows runtime. Registration and successful execution do not by themselves make an operation appropriate for a general artist-facing workflow. This project classifies every registered operation by its configuration requirements and expected scene impact.

The source of truth is `src/usd_optimize_app/operation_support.py`. The operation matrix writes each tier into `operation-matrix.json` so runtime checks, documentation, and product exposure remain aligned.

## Support tiers

### Supported — 6

These operations support two explicit GUI workflows plus automatic stage diagnostics:

- `computeExtents`
- `optimizeMaterials`
- `optimizePrimvars`
- `optimizeTimeSamples`
- `printStats`
- `findOverlappingMeshes`

The write operations preserve the intended hierarchy and topology of the supported cleanup workflow. `printStats` runs automatically with GUI input inspection, while `findOverlappingMeshes` remains an explicit read-only workflow. Neither writes a USD derivative. Overlap analysis is explicitly configured with `useGpu: false` for predictable CPU behavior.

### Advanced — 25

These operations execute, but can change topology, hierarchy, schemas, composition, authored structure, or shading data; or they expose developer diagnostics without a complete end-user contract:

- `countVertices`
- `decimateMeshes`
- `deduplicateGeometry`
- `deduplicateHierarchies`
- `deleteHiddenPrims`
- `findCoincidingGeometry`
- `findFlatHierarchies`
- `flattenHierarchy`
- `generateNormals`
- `manifoldMeshes`
- `merge`
- `mergeVertices`
- `meshCleanup`
- `moveMaterials`
- `optimizeSkelRoots`
- `organizePrototypes`
- `primitivesToMeshes`
- `pruneLeaves`
- `remeshMeshes`
- `removeSmallGeometry`
- `removeUntypedPrims`
- `removeUnusedUVs`
- `rtxMeshCount`
- `sparseMeshes`
- `triangulateMeshes`

They remain accessible to developers through isolated operation-matrix checks and developer presets. They are not presented as broadly safe artist controls.

### Requires configuration — 12

These operations need explicit geometry, path, tolerance, projection, clipping, conversion, or removal parameters before their result can be evaluated:

- `boxClip`
- `diceMeshes`
- `editStageMetrics`
- `fitPrimitives`
- `generateAtlasUVs`
- `generateProjectionUVs`
- `pivot`
- `removeAttributes`
- `removePrims`
- `shrinkwrap`
- `splitMeshes`
- `subdivideMeshes`

Running them with an empty configuration is only a loader and crash check, not a meaningful product validation.

### GPU-dependent — 1

- `findOccludedMeshes`

Its behavior depends on compatible GPU visibility evaluation. It passed on the local validation workstation, but hardware-specific success is not treated as a portable end-user guarantee.

### Internal — 4

- `deletePrims`
- `generateScene`
- `pythonScript`
- `utilityFunction`

These are low-level helpers, test facilities, or arbitrary execution entry points rather than supported product workflows.

## Validation performed

### Isolated registry matrix

The operation matrix ran every standard and analysis operation against the layered teapot fixture in a separate worker process. The baseline matrix completed with 31 passes, 16 intentionally skipped operations, and no unexpected failures.

A second exploratory run included all categories. Every operation completed with its default configuration except `boxClip` and `removeAttributes`, which require explicit parameters. `findOccludedMeshes` completed on the validation workstation but remains GPU-dependent.

An operation-matrix pass verifies that the operation loads, completes or fails as expected, and produces a reopenable USD when it writes output. It does not prove visual equivalence or downstream suitability.

### Representative preset sweep

The six pre-simplification presets were executed across five representative assets:

- layered teapot with relative dependencies;
- material and texture fixture (`McUsd.usda`);
- animated transform fixture;
- point-instancer material fixture;
- referenced hierarchy fixture.

All 30 executions completed and their outputs reopened. The results also showed that the old `animated_asset` workflow was largely redundant with `safe_publish`, while `review_light` and `aggressive_geometry` introduced structural changes without a sufficiently narrow end-user contract. Those presets are now developer-only.

The final supported-workflow sweep ran Safe Cleanup, Inspect Stage, and Find Overlaps across the same five assets. Safe Cleanup additionally verified default prim, stage metrics, transformable prim paths and types, mesh topology, point data, and transform values at every source-authored sample. All 15 workflow runs passed.

### Upstream focused tests

NVIDIA's operation-specific tests were inspected for expected parameters and scene behavior. The supported cleanup configuration follows those tested modes:

- `optimizePrimvars`: indexing and simplification without bound-data removal;
- `optimizeMaterials`: tested against references, payloads, instancing, material bindings, node graphs, and primvar readers;
- `optimizeTimeSamples`: removes exact redundant samples with interpolation removal disabled;
- `findOverlappingMeshes`: structured CPU analysis;
- `computeExtents`: bounds recomputation;
- `printStats`: read-only stage metrics.

`pruneLeaves` was removed from Safe Cleanup because it deliberately deletes authored terminal prims and is therefore not structurally lossless.

A relocation test also exposed that `SdfLayer::Export` preserves root-layer relative asset paths. Writing a layered stage into another directory could therefore open successfully while losing payload geometry. The worker now rebases relative root-layer asset paths to the output directory after export, and the layered teapot smoke test verifies that its payload remains loaded.

## Developer commands

Run the supported/default matrix:

```powershell
uv run usdopt operation-matrix --input tests/fixtures/teapot/teapot.usd --strict
```

Include configuration-dependent, GPU, and internal operations for exploratory checks:

```powershell
uv run usdopt operation-matrix --input tests/fixtures/teapot/teapot.usd --all
```

List developer-only presets:

```powershell
uv run usdopt list-presets --all
```

A future operation should be promoted to the supported tier only after it has a fixed product configuration, purpose-built fixtures, semantic assertions, representative production-asset coverage, and clear user-facing failure behavior.
