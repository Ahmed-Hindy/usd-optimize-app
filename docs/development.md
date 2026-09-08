# Development Guide 🛠️

This guide is for developers working from the source checkout. The packaged artifact is the end-user distribution and includes the application runtime.

## Setup

Clone the repository, then install the development environment:

```powershell
uv sync
```

The app requires the extracted `usd-optimize` runtime described in the [runtime dependency notes](usd-optimize-source-dependency.md) for local runtime checks. Run the diagnostic command to confirm it is complete:

```powershell
uv run usdopt doctor
```

## Source checks

```powershell
uv run ruff check src tests tools/build_windows_portable.py
uv run pytest
```

These are the checks run by GitHub Actions. The CLI and GUI share the same backend request and optimization path.

## Source structure

The application is organized by responsibility:

- `backend.py` validates user-facing settings and builds shared optimization requests.
- `usd_runner.py` owns isolated worker execution, cancellation, logs, and reports.
- `runtime_worker.py` is the subprocess entry point that imports NVIDIA and OpenUSD code.
- `operation_support.py` classifies every registered operation for product exposure.
- `operation_matrix.py` runs isolated developer checks using that classification.
- `gui/main_window.py` coordinates widgets and user interaction.
- `gui/stage_inspection.py` owns hierarchy and automatic-diagnostics lifecycles.
- `gui/analysis_view.py` formats reviewed structured operation findings for artists.
- `backend.get_gui_workflows()` defines the explicit artist-triggered workflow order.
- `gui/report_views.py` renders structured diagnostic tables.
- `gui/scene_graph_view.py` renders the bounded USD prim hierarchy.
- `gui/log_view.py` renders fixed-width worker output with severity-aware colors.
- `gui/theme.py` contains the Qt stylesheet and semantic state colors.
- `formatting.py` contains shared human-readable value formatting.

Keep native USD imports out of GUI presentation modules. New CLI and GUI behavior should enter through the shared backend rather than duplicating execution logic.

Launch the source-checkout GUI with:

```powershell
uv run usdopt-gui
```

## Runtime validation

Run the local smoke test after changing runtime-facing code:

```powershell
uv run usdopt smoke-test
```

For the broader external asset suite, prepare the cache in the sibling `usd-optimize` checkout and then run:

```powershell
uv run usdopt smoke-test --external-assets
```

See [external asset smoke tests](external-asset-smoke-tests.md) for the cache and manifest details, [operational smoke tests](operational-smoke-tests.md) for the recorded validation procedure, and [operation support](operation-support.md) for the 48-operation product classification.

## Developer operations

The NVIDIA runtime registers 48 operations. Most change topology or hierarchy,
depend on hardware, or require asset-specific parameters, so they are available
through developer presets and the operation matrix rather than general GUI controls.

```powershell
uv --system-certs run usdopt list-presets --all
uv --system-certs run usdopt operation-matrix --input tests/fixtures/teapot/teapot.usd
```

The [operation support matrix](operation-support.md) explains each classification.
The [operations reference](operations.md) maps operations to presets and describes
their effects.

## Portable release

The local and CI packaging procedure is documented in the [Windows portable release guide](windows-portable-release.md). The builder installs the CLI and GUI from the same project package, bundles the NVIDIA runtime, and executes its smoke tests from inside the assembled directory.

The packaging workflow uses one locked app environment and one NVIDIA runtime
package. Before archiving, it checks runtime and operation discovery, CLI preset
discovery, native Windows and offscreen GUI construction, diagnostic operations,
and Safe Cleanup with a saved USD output.

`manifest.json` records the bundled application, Python, PySide6, and NVIDIA
runtime versions. The release includes a `.sha256` file for archive verification.
Historical archive-size measurements and component sizes are recorded in the
[portable release guide](windows-portable-release.md#local-build).

## Reports and CI

See the [report summary guide](report-summary.md) for generated report output. The normal CI workflow runs source checks. The portable-release workflow additionally downloads the NVIDIA package, builds the distributable ZIP, and runs packaged runtime smoke tests.

## Related technical notes

- [Runtime dependency](usd-optimize-source-dependency.md)
- [GUI implementation](gui.md)
- [Operation support](operation-support.md)
- [CI details](ci.md)
- [Windows portable release](windows-portable-release.md)

Keep Houdini integration external for now. A future shelf tool should call the CLI through `subprocess.run(...)` instead of importing NVIDIA USD libraries into Houdini's Python process.
