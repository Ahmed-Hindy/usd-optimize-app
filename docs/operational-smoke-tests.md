# Operational Smoke Tests

This file records the current operational checks for `usd-optimize-app` against the downloaded Windows `usd-optimize` runtime artifact.

## Runtime under test

The app defaults to this runtime artifact:

```text
../usd-optimize/.artifacts/usd-optimize-v1.1.0-windows-25.11-py3.12/release-runtime
```

Set `USD_OPTIMIZE_RUNTIME_ROOT` to explicitly test another extracted package.
The current default was refreshed on 2026-07-20 from NVIDIA's public 1.1.0
Windows package:

```text
usd_optimize_usd_25.11_py_3.12@1.1.0.1-1-0.986.80031f97.gl.windows-x86_64.release.zip
```

## One-command smoke test

Use this command for the normal local operational check:

```powershell
uv run usdopt smoke-test
```

The command checks the strict runtime artifact, confirms imports, counts operations, then runs Safe Cleanup, Inspect Stage, and Find Overlaps against the sibling OpenUSD fixture. Safe Cleanup also validates preserved geometry, transforms, stage metrics, and relocated dependencies.

Observed result on 2026-07-04:

```text
Operation count: 47
Preset runs:
  - diagnostics: OK
  - safe_publish: OK
Smoke test passed.
```

Generated outputs are written under:

```text
reports/smoke-tests
```

## Manual commands run on 2026-07-20

### Code checks

```powershell
uv run -- ruff check src tests
uv run pytest
```

Result:

```text
All checks passed.
74 passed.
```

### Runtime check

```powershell
uv run usdopt doctor
uv run usdopt list-ops
```

Result:

```text
Environment looks usable.
operation count: 47
```

`list-ops` returned the expected operation set, including these operation names used by bundled profiles:

```text
findOverlappingMeshes
merge
utilityFunction
```

### Small OpenUSD fixture smoke tests

Fixture:

```text
../usd-optimize/source/tests/data/external/openusd_helloworld.usda
```

This is the same small OpenUSD-style fixture family used for the sibling `usd-optimize` CI smoke testing.

Diagnostic preset:

```powershell
uv run usdopt optimize --input "G:/Projects/Dev/Github/devspace-test/usd-optimize/source/tests/data/external/openusd_helloworld.usda" --output "reports/openusd_helloworld.diagnostics.usda" --preset diagnostics --force
```

Result:

```text
Optimized: reports/openusd_helloworld.diagnostics.usda
Report: reports/openusd_helloworld.diagnostics.usda.report.json
Log: reports/openusd_helloworld.diagnostics.usda.log
```

Safe publish preset:

```powershell
uv run usdopt optimize --input "G:/Projects/Dev/Github/devspace-test/usd-optimize/source/tests/data/external/openusd_helloworld.usda" --output "reports/openusd_helloworld.safe_publish.usda" --preset safe_publish --force
```

Result:

```text
Optimized: reports/openusd_helloworld.safe_publish.usda
Report: reports/openusd_helloworld.safe_publish.usda.report.json
Log: reports/openusd_helloworld.safe_publish.usda.log
```

## Interpretation

The app is operational for the current small-fixture workflow:

- the configured runtime artifact is found;
- `pxr` imports from the artifact;
- `usd_optimize` imports from the artifact;
- 47 operations are registered through the public runtime API;
- the diagnostic preset can run against a real file-backed USD fixture;
- the safe publish preset can run against the same fixture;
- generated reports and logs are written under `reports/smoke-tests` for the one-command smoke test.

The external asset workflow is documented in `docs/external-asset-smoke-tests.md`. It reuses the sibling `usd-optimize` CI manifest and has passed with both `diagnostics` and `safe_publish` across seven primary OpenUSD smoke assets.

Use `uv run usdopt report-summary --reports-dir reports/smoke-tests` to summarize generated report JSON files after smoke testing.

## Preset workflow verification

On 2026-07-10, the pre-simplification `safe_publish`, `animated_asset`, and `review_light` configurations were run through the required Windows runtime against both the teapot fixture and `tests/fixtures/mcusd/McUsd.usda`. All six runs completed, exported output, generated reports without warnings or errors, and reopened successfully. `animated_asset` and `review_light` are now developer-only comparison presets; the supported GUI exposes Safe Cleanup, Inspect Stage, and Find Overlaps.

`removeUnusedUVs` and `sparseMeshes` now pass their isolated default checks on the teapot fixture with the refreshed Windows runtime. They remain outside the conservative workflows until their output behavior has been reviewed on production-like assets.

On 2026-07-20, `findOverlappingMeshes` completed through the app's isolated runtime worker against `tests/fixtures/mcusd/McUsd.usda` using the public 1.1.0 package. The `find_overlaps` profile reported 22 affected mesh paths with `suppressedOverlaps: 0`, did not export a USD derivative, and saved the structured result in its report JSON.

The next useful validation step is to test a more production-like USD asset with heavier references, materials, animation, and repeated hierarchy data.

## Operation matrix

Use the operation matrix to explore every discovered runtime DLL in isolation. Each
operation receives a fresh input copy plus, where applicable, an output path, worker
log, report, and an `operation-matrix.json` manifest. A failing operation does not
stop later operations.

Start with the standard operation set:

```powershell
uv run usdopt operation-matrix --input "path/to/fixture.usda"
```

Then opt into every category for exploratory local validation:

```powershell
uv run usdopt operation-matrix --input "path/to/fixture.usda" --all --strict
```

`--strict` returns a non-zero exit code only for operations expected to pass. Empty
configurations for `boxClip`, `removeAttributes`, and hardware-dependent
`findOccludedMeshes` are allowed to fail without failing the matrix.
Parameterized, GPU-bound, and helper/destructive operations are excluded by default;
`--all` includes them with their default configuration. Their outputs still require
asset-specific review before they can become supported workflows.
