# Windows Release Package Smoke Test

`tools/release_smoke/windows_package_smoke.py` validates a Windows CPython 3.12
NVIDIA Usd Optimize package in separate processes. It distinguishes native
loader failures from ordinary operation failures without relying on the app's
runtime configuration.

It verifies:

1. `pxr` can create an in-memory stage.
2. `usd_optimize.core` registers `findOverlappingMeshes`.
3. `UsdOptimizeCore.executeConfig()` runs `deletePrims`.
4. CPU overlap analysis returns the 22 known McUsd paths and zero suppressed overlaps.
5. The packaged `usdOptimize.exe` completes an overlap-analysis command.
6. Optionally, six conservative operation stacks run over seven checksum-pinned OpenUSD tutorial assets (42 runs total).
7. `usdMtlx` loads, reads a MaterialX layer, and parses a supplied shader definition with its expected input. This uses a self-contained definition because the package does not bundle the standard MaterialX shader library.

The package is the system under test; the checked-in McUsd fixture is input only.

## Run locally

```powershell
uv run python tools/release_smoke/windows_package_smoke.py `
  --package-archive C:\path\to\usd_optimize_usd_25.11_py_3.12@1.2.1.1-2-1.1193.bec04ac2.gl.windows-x86_64.release.zip `
  --overlap-fixture-usd tests/fixtures/mcusd/McUsd.usda
```

Run the external matrix only when its cache is already available or you intend
to download the checksum-pinned assets:

```powershell
uv run python tools/release_smoke/download_external_assets.py `
  --manifest tools/release_smoke/external_usd_assets.json `
  --assets-dir .cache/release-smoke-assets
```

Then add `--external-asset-manifest`, `--external-assets-dir`, and
`--external-operation-matrix` to the smoke command.

## GitHub Actions

Dispatch **Windows release package smoke** from the Actions tab. The workflow
defaults to upstream `v1.2.1`; set **Run external matrix** to false when only
the focused package-loader and overlap regression checks are needed.
