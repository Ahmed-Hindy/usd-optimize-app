# Development & Packaging Guide

## Environment Setup

Install the Python development environment with `uv`:

```powershell
uv sync
```

For local runtime checks, `usd-optimize-app` expects the extracted NVIDIA `usd-optimize` v1.4.0 (OpenUSD 26.08, CPython 3.12) package at:

```text
../usd-optimize/.artifacts/usd-optimize-v1.4.0-windows-26.08-py3.12/release-runtime
```

Set `USD_OPTIMIZE_RUNTIME_ROOT` to point to another extracted runtime directory containing `python/`, `usdpy/`, `lib/operations/`, and `extraLibs/`. Verify your setup with:

```powershell
uv run usdopt doctor
```

Launch the GUI from source with:

```powershell
uv run usdopt-gui
```

---

## Architecture Overview

- `backend.py` — Validates job settings and builds optimization requests shared by the CLI and GUI.
- `usd_runner.py` & `runtime_worker.py` — Runs OpenUSD and NVIDIA `usd-optimize` inside an isolated worker subprocess so native DLLs never load in the GUI process, and rebases relative root-layer asset paths when exporting to a new directory.
- `operation_support.py` & `operation_matrix.py` — Classifies all 50 runtime operations and runs isolated per-operation checks.
- `gui/` — PySide6 interface (`main_window.py`, `stage_inspection.py`, `scene_graph_view.py`, `report_views.py`, `analysis_view.py`, `log_view.py`, `theme.py`).

---

## Testing & Runtime Validation

### Unit tests and lint

```powershell
uv run ruff check src tests tools/build_windows_portable.py
uv run pytest
```

### Local runtime smoke tests

```powershell
# Run Safe Cleanup, Inspect Stage, and Find Overlaps against the default fixture
uv run usdopt smoke-test

# Run against the 7 checksum-pinned OpenUSD tutorial assets (requires ../usd-optimize/.cache/usd-assets)
uv run usdopt smoke-test --external-assets

# Run every supported/advanced operation in isolation against the teapot fixture
uv run usdopt operation-matrix --input tests/fixtures/teapot/teapot.usd --strict
```

### Upstream release-package smoke test

`tools/release_smoke/windows_package_smoke.py` tests a raw NVIDIA release ZIP in isolated subprocesses (`pxr`, `usdMtlx`, `deletePrims`, CPU `findOverlappingMeshes`, and `usdOptimize.exe`):

```powershell
uv run python tools/release_smoke/windows_package_smoke.py `
  --package-archive C:\path\to\usd_optimize_usd_26.08_py_3.12@1.4.0.1-4-0.1799.aca426ac.gl.windows-x86_64.release.zip `
  --overlap-fixture-usd tests/fixtures/mcusd/McUsd.usda
```

---

## Portable Windows Build & CI

### Local portable build

`tools/build_windows_portable.py` assembles a self-contained `usd-optimize-app-<version>-windows-x86_64` directory with an isolated CPython 3.12 distribution, trimmed Qt modules (`QtCore`, `QtGui`, `QtWidgets`), the NVIDIA runtime, `manifest.json`, and launcher scripts (`usdopt.cmd`, `usdopt-gui.cmd`), then smoke-tests the packaged binaries before zipping:

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

- **CI** (`.github/workflows/ci.yml`) — Runs Ruff, script compilation checks, and pytest on every push to `main` and pull request.
- **Windows portable release** (`.github/workflows/windows-portable-release.yml`) — Triggered on `v*` tags or manual dispatch. Downloads the NVIDIA v1.4.0 runtime, builds and smoke-tests the portable package, and attaches the `.zip` and `.zip.sha256` to the GitHub Release.
- **Windows release package smoke** (`.github/workflows/windows-release-package-smoke.yml`) — Manual workflow that validates an upstream NVIDIA release ZIP against the focused smoke suite and optional 42-run external asset matrix.
