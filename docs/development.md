# Development & Packaging Guide

## Environment Setup

Install the Python development environment with `uv`:

```powershell
uv sync
```

For local runtime checks, `usd-optimize-app` expects the extracted NVIDIA `usd-optimize` v1.4.0 (`usd_optimize_usd_26.08_py_3.12@1.4.0.1-4-0.1799.aca426ac.gl.windows-x86_64.release.zip`) package at:

```text
../usd-optimize/.artifacts/usd-optimize-v1.4.0-windows-26.08-py3.12/release-runtime
```

Set `USD_OPTIMIZE_RUNTIME_ROOT` to point to another extracted runtime directory containing `python/`, `usdpy/`, `lib/operations/`, and `extraLibs/`. The app fails fast rather than falling back to incomplete runtimes. Verify your setup with:

```powershell
uv run usdopt doctor
```

Launch the GUI from source with:

```powershell
uv run usdopt-gui
```

---

## Architecture Overview

- `constants.py`, `runtime_paths.py`, `usd_env.py` — Runtime path discovery, DLL search-path setup, and environment diagnostics.
- `backend.py` — Validates job settings and builds optimization requests shared by the CLI and GUI.
- `usd_runner.py` & `runtime_worker.py` — Runs optimization jobs in an isolated worker subprocess and rebases relative root-layer asset paths when exporting to a different folder.
- `operation_support.py` & `operation_matrix.py` — Classifies all 50 runtime operations and runs isolated per-operation checks (writing `operation-matrix.json`).
- `gui/` — PySide6 interface (`main_window.py`, `stage_inspection.py`, `scene_graph_view.py`, `report_views.py`, `analysis_view.py`, `log_view.py`, `theme.py`).

*(External DCC integrations such as Houdini shelf tools should invoke `usdopt` via `subprocess.run(...)` rather than importing the bundled USD libraries into the host Python process.)*

---

## Testing & Runtime Validation

### Lint and unit tests (matches CI)

```powershell
uv run ruff check src tests tools/build_windows_portable.py
uv run ruff check --select I tools/release_smoke
uv run python -m py_compile tools/release_smoke/windows_package_smoke.py tools/release_smoke/download_external_assets.py
uv run pytest
```

### Local runtime smoke tests

By default, `usdopt smoke-test` uses the sibling `../usd-optimize` checkout's fixture and external asset cache, or you can pass paths from this repository explicitly:

```powershell
# Run Safe Cleanup, Inspect Stage, and Find Overlaps against a checked-in fixture (outputs to reports/smoke-tests)
uv run usdopt smoke-test --input tests/fixtures/teapot/teapot.usd

# Download the 7 checksum-pinned OpenUSD tutorial assets and run the external asset suite
uv run python tools/release_smoke/download_external_assets.py `
  --manifest tools/release_smoke/external_usd_assets.json `
  --assets-dir .cache/release-smoke-assets
uv run usdopt smoke-test --external-assets `
  --asset-manifest tools/release_smoke/external_usd_assets.json `
  --assets-dir .cache/release-smoke-assets
uv run usdopt smoke-test --external-assets `
  --asset-manifest tools/release_smoke/external_usd_assets.json `
  --assets-dir .cache/release-smoke-assets `
  --preset safe_publish

# Run every supported/advanced operation in isolation against the teapot fixture (add --all for parameterized/GPU/internal ops)
uv run usdopt operation-matrix --input tests/fixtures/teapot/teapot.usd --strict
```

### Upstream release-package smoke test

`tools/release_smoke/windows_package_smoke.py` validates a raw NVIDIA release ZIP in isolated subprocesses (`pxr`, `usdMtlx` with a self-contained shader definition since the runtime does not bundle the standard MaterialX library, `deletePrims`, CPU `findOverlappingMeshes` on `McUsd.usda`, and `usdOptimize.exe`):

```powershell
uv run python tools/release_smoke/windows_package_smoke.py `
  --package-archive C:\path\to\usd_optimize_usd_26.08_py_3.12@1.4.0.1-4-0.1799.aca426ac.gl.windows-x86_64.release.zip `
  --overlap-fixture-usd tests/fixtures/mcusd/McUsd.usda
```

To include the 42-run external asset matrix, pass `--external-asset-manifest tools/release_smoke/external_usd_assets.json`, `--external-assets-dir .cache/release-smoke-assets`, and `--external-operation-matrix`.

---

## Portable Windows Build & CI

### Artifact layout

```text
usd-optimize-app-<version>-windows-x86_64/
├── usdopt.cmd
├── usdopt-gui.cmd
├── manifest.json
├── README.md
├── docs/
├── licenses/
├── presets/
├── python/
└── runtime/usd-optimize/ (python, usdpy, lib/operations, extraLibs)
```

### Local portable build

`tools/build_windows_portable.py` copies a clean CPython 3.12 distribution, installs locked runtime dependencies, strips unused Qt modules/headers/tests (keeping `QtCore`, `QtGui`, `QtWidgets`, and Windows platform/image plugins), bundles the NVIDIA runtime and `manifest.json`, and runs CLI, GUI (native Windows and offscreen), and workflow smoke tests before zipping:

```powershell
uv run python tools\build_windows_portable.py `
  --runtime-root "..\usd-optimize\.artifacts\usd-optimize-v1.4.0-windows-26.08-py3.12\release-runtime" `
  --python-root "C:\Program Files\Python312" `
  --output-dir dist `
  --usd-optimize-version 1.4.0 `
  --usd-optimize-license ..\usd-optimize\LICENSE `
  --smoke-input tests\fixtures\teapot\teapot.usd
```

### GitHub Actions workflows

- **CI** (`.github/workflows/ci.yml`) — Runs Ruff, script compilation checks, and pytest (including teapot and McUsd fixture checks) on every push to `main` and pull request.
- **Windows portable release** (`.github/workflows/windows-portable-release.yml`) — Triggered on `v*` tags or manual dispatch. Caches/downloads the NVIDIA v1.4.0 runtime, builds and smoke-tests the portable package, and uploads the workflow artifact. When run on a `v*` tag ref (rather than a branch dispatch), it also attaches the `.zip` and `.zip.sha256` to the GitHub Release.
- **Windows release package smoke** (`.github/workflows/windows-release-package-smoke.yml`) — Manual workflow that validates an upstream NVIDIA release ZIP against the focused smoke suite and optional 42-run external asset matrix.
