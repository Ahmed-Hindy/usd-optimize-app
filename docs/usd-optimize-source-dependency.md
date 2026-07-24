# usd-optimize Runtime Artifact Dependency

## Decision

`usd-optimize-app` uses NVIDIA's Windows 1.1.0 runtime package from the sibling
`usd-optimize` artifact directory.

The required runtime root is:

```text
../usd-optimize/.artifacts/usd-optimize-v1.1.0-windows-25.11-py3.12/release-runtime
```

Set `USD_OPTIMIZE_RUNTIME_ROOT` to use another extracted package with the same
layout. The override is explicit; the app never falls back to vendored Python
packages or source build folders.

## Artifact source

The validated release package zip is:

```text
usd_optimize_usd_25.11_py_3.12@1.1.0.1-1-0.986.80031f97.gl.windows-x86_64.release.zip
```

That zip is extracted into the required `release-runtime` folder.

## Required runtime layout

The extracted runtime root must contain:

```text
release-runtime/python
release-runtime/usdpy
release-runtime/lib
release-runtime/lib/operations
release-runtime/extraLibs
```

The app configures the package's documented `python`, `usdpy`, `lib`,
`lib/operations`, and `extraLibs` search paths. The 1.1.0 package loads and
auto-registers operations through its public Python API; no app-side plugin
loader or bootstrap shim is used.

## Failure policy

The app should fail instead of silently switching runtime sources.

Expected hard failures include:

- required `release-runtime` folder is missing;
- expected runtime folders are missing;
- no compiled operation DLLs are available;
- `pxr` cannot import from the runtime artifact;
- `usd_optimize` cannot import from the runtime artifact.

Use:

```powershell
uv run usdopt doctor
```

as the first diagnostic command. It should report the exact missing folder instead of trying another runtime source.

## Validation on 2026-07-20

Runtime validation passed from `usd-optimize-app`:

```powershell
uv run usdopt doctor
uv run usdopt list-ops
```

Observed result:

```text
Runtime root: ../usd-optimize/.artifacts/usd-optimize-v1.1.0-windows-25.11-py3.12/release-runtime
python dir: OK
usdpy dir: OK
lib dir: OK
extraLibs dir: OK
pxr import: OK
usd_optimize import: OK
operation count: 47
Environment looks usable.
```

The one-command OpenUSD fixture smoke test passed:

```powershell
uv run usdopt smoke-test
```

That command checks the runtime, counts operations, and runs Safe Cleanup, Inspect Stage, and Find Overlaps against the fixture checked into the sibling `usd-optimize` repo:

```text
../usd-optimize/source/tests/data/external/openusd_helloworld.usda
```

Commands run:

```powershell
uv run usdopt optimize --input "G:/Projects/Dev/Github/devspace-test/usd-optimize/source/tests/data/external/openusd_helloworld.usda" --output "reports/openusd_helloworld.diagnostics.usda" --preset diagnostics --force
uv run usdopt optimize --input "G:/Projects/Dev/Github/devspace-test/usd-optimize/source/tests/data/external/openusd_helloworld.usda" --output "reports/openusd_helloworld.safe_publish.usda" --preset safe_publish --force
```

Both manual commands also completed successfully. The one-command smoke test writes USD output, report JSON, and log files under `reports/smoke-tests`.

Code quality checks also passed:

```powershell
uv run -- ruff check src tests
uv run pytest
```

Observed result:

```text
All checks passed.
74 passed.
```

## Implementation notes

The strict dependency is defined in:

```text
src/usd_optimize_app/constants.py
```

Runtime paths are resolved in:

```text
src/usd_optimize_app/runtime_paths.py
```

Environment setup and diagnostics are handled in:

```text
src/usd_optimize_app/usd_env.py
```

The worker subprocess receives the resolved runtime root from the main process and builds its Python and DLL search paths from the same strict artifact layout.
