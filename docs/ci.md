# Continuous Integration

The repository uses three GitHub Actions workflows: a fast app-quality check, an opt-in upstream release-package smoke test, and a portable application release build.

## App quality

`.github/workflows/ci.yml` runs on pushes to `main` and on pull requests.

## Checks

The CI job runs on `windows-latest` with Python 3.12 and `uv`:

```powershell
uv sync --locked
uv run -- ruff check src tests tools/build_windows_portable.py
uv run -- ruff check --select I tools/release_smoke
uv run python -m py_compile `
  tools/release_smoke/windows_package_smoke.py `
  tools/release_smoke/download_external_assets.py
uv run pytest
```

These are intentionally the same checks used locally before committing app code. The test suite includes shared-backend tests and GUI import coverage, but CI does not launch a visible desktop window.
It also validates two checked-in USD fixtures: the Intent VFX teapot payload/reference tree and the
McUsd scene's camera, lighting, geometry, material, shader variety, and texture asset paths.

## Local app runtime smoke

The app-owned operational smoke test remains local because it runs the runtime
installed beside the sibling `usd-optimize` checkout:

```powershell
uv run usdopt smoke-test
```

The default runtime location is:

```text
../usd-optimize/.artifacts/usd-optimize-v1.2.1-windows-25.11-py3.12/release-runtime
```

That artifact is local machine state, not part of this repository. The separate
manual release-package workflow below covers the published NVIDIA package.

## Windows release-package smoke

`.github/workflows/windows-release-package-smoke.yml` is a manual workflow
that downloads exactly one public NVIDIA release ZIP, validates it in isolated
Python processes, and uploads the full log as an artifact. Its defaults target
`v1.2.1`, OpenUSD 25.11, and CPython 3.12.

The checked-in runner verifies package structure, MaterialX plugin and shader loading,
`pxr`, operation registry
creation, `deletePrims`, CPU `findOverlappingMeshes`, and the packaged CLI. It
uses `tests/fixtures/mcusd/McUsd.usda`, expecting 22 reported paths and zero
suppressed overlaps. The optional external matrix runs six conservative
operation stacks across seven checksum-pinned OpenUSD tutorial assets (42
isolated runs) and is enabled by default only for manual dispatch.

Local focused invocation does not download external assets:

```powershell
uv run python tools/release_smoke/windows_package_smoke.py `
  --package-archive C:\path\to\usd_optimize_usd_25.11_py_3.12@1.2.1.1-2-1.1193.bec04ac2.gl.windows-x86_64.release.zip `
  --overlap-fixture-usd tests/fixtures/mcusd/McUsd.usda
```

## Windows portable release

`.github/workflows/windows-portable-release.yml` creates the end-user ZIP. It runs manually and for version tags, caches the upstream NVIDIA archive, installs the locked application dependencies into a copied CPython 3.12 distribution, and bundles `usd-optimize` v1.2.1.

The assembled directory is validated before compression. The workflow runs `doctor`, lists the packaged user presets, constructs the GUI on both the offscreen and native Windows platforms, then runs the shared smoke harness across Safe Cleanup, Inspect Stage, and Find Overlaps. Safe Cleanup must preserve geometry, transforms, stage metrics, and relocated dependencies. It uploads the ZIP, its SHA-256 checksum, and `manifest.json`; tagged builds are also attached to the GitHub release.
