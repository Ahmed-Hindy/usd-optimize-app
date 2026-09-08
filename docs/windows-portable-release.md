# Windows Portable Release

The portable release contains the application, its Python and Qt dependencies, and the complete NVIDIA `usd-optimize` runtime in one extracted directory.

## Artifact layout

```text
usd-optimize-app-<version>-windows-x86_64/
├── usdopt.cmd
├── usdopt-gui.cmd
├── manifest.json
├── README.md
├── licenses/
├── presets/
├── python/
└── runtime/
    └── usd-optimize/
        ├── python/
        ├── usdpy/
        ├── lib/
        │   └── operations/
        └── extraLibs/
```

`usdopt.cmd` and `usdopt-gui.cmd` launch the same installed `usd_optimize_app` package. The CLI and GUI therefore share `usd_optimize_app.backend`; the release does not carry separate implementations or duplicate business logic.

## Automated build

`.github/workflows/windows-portable-release.yml` runs manually or for version tags. It:

1. checks out the application;
2. creates a locked Python 3.12 environment;
3. runs Ruff and pytest;
4. restores or downloads NVIDIA's Windows `usd-optimize` package;
5. copies a clean portable CPython installation;
6. installs the locked runtime dependencies and application package;
7. removes Python tests, documentation, headers, unused Qt modules, QML tooling, and native linker files;
8. bundles the extracted NVIDIA runtime and its license;
9. runs packaged CLI, native Windows GUI, offscreen GUI, diagnostic, and write-output smoke tests;
10. creates a maximum-deflate ZIP and SHA-256 checksum;
11. uploads the workflow artifact and attaches tagged builds to a GitHub release.

The workflow defaults to NVIDIA `usd-optimize` v1.2.1, OpenUSD 25.11, and CPython 3.12.

## Local build

Use an already extracted v1.2.1 runtime to avoid another large download:

```powershell
$pythonRoot = "C:\Program Files\Python312"
$runtimeRoot = "..\usd-optimize\.artifacts\usd-optimize-v1.2.1-windows-25.11-py3.12\release-runtime"

uv run python tools\build_windows_portable.py `
  --runtime-root $runtimeRoot `
  --python-root $pythonRoot `
  --output-dir dist `
  --usd-optimize-version 1.2.1 `
  --usd-optimize-license ..\usd-optimize\LICENSE `
  --smoke-input tests\fixtures\teapot\teapot.usd
```

The builder removes the copied interpreter's existing `site-packages`, installs only the locked runtime dependencies and this project, and isolates the packaged interpreter from user-site Python packages. It then keeps only the Qt Core, Gui, and Widgets modules used by the application, the required Windows platform and image plugins, and runtime DLLs. Development headers, import libraries, tests, documentation, QML components, and Qt tooling are excluded.

For the previously measured v1.1.0 runtime, the artifact is approximately 180–190 MiB compressed and 550–560 MiB expanded. Most of that size is NVIDIA/OpenUSD native code: roughly 154 MiB of the compressed archive is the `usd-optimize` runtime, while Python and Qt account for about 28 MiB. Materially smaller builds would require removing USD libraries or optimization operations rather than packaging waste.

## Validation performed inside the artifact

The builder executes the packaged interpreter rather than the development virtual environment. A successful build confirms:

- `pxr` imports from the bundled runtime;
- `usd_optimize` imports from the bundled runtime;
- all registered operations are visible;
- the three user workflows resolve from the portable directory;
- the PySide6 main window can be constructed with both the native Windows and offscreen platform plugins;
- Inspect Stage and Find Overlaps execute without exporting a USD derivative;
- Safe Cleanup writes an output USD while preserving geometry, transforms, stage metrics, and relocated payload dependencies.

Temporary smoke-test reports and USD files are deleted before the archive is created.

## Version and integrity metadata

`manifest.json` records:

- application version;
- NVIDIA runtime version;
- Python version;
- PySide6 version;
- CLI and GUI entry points;
- the shared backend module.

The adjacent `.zip.sha256` file contains the archive checksum.
