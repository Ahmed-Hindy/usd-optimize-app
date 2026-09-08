# Runtime v1.2.1 validation

Validated on Windows with CPython 3.12 and OpenUSD 25.11 on 2026-09-09.
The development runtime, portable builder, and release workflows now target
NVIDIA `usd-optimize` v1.2.1.

## Package

- Archive: `usd_optimize_usd_25.11_py_3.12@1.2.1.1-2-1.1193.bec04ac2.gl.windows-x86_64.release.zip`
- Download: 163,255,745 bytes (155.7 MiB).
- SHA-256, verified against the GitHub release asset digest:
  `9eb1a342f2893c485890cd673e28f445300ce6e235b170b1f7a65e08162dafbd`
- Runtime: `../usd-optimize/.artifacts/usd-optimize-v1.2.1-windows-25.11-py3.12/release-runtime`.
- The old v1.1.0 runtime remains available for comparison.

## Pain areas: before and after

| Check | v1.1.0 baseline | v1.2.1 |
| --- | --- | --- |
| `usdMtlx` plugin loading | Fails: required module missing | Passes; MaterialX DLLs are included |
| MaterialX layer and supplied shader definition | Blocked by plugin failure | Layer loads; shader is valid and exposes its declared input |
| Public operation registry and normal Python shutdown | Passes, 47 operations | Passes, 48 operations |
| `executeConfig` and normal Python shutdown | Passes | Passes |
| CPU overlap analysis on McUsd | 22 meshes, zero suppressed overlaps | Same result |
| Packaged CLI, GPU overlap analysis | Aborts after execution, exit `3221226505`, `CUDA error: driver shutting down` | Exits 0 without the shutdown error |
| Python GPU overlap analysis | Exits 0 | Exits 0; expected overlap result preserved |
| Packaged CLI `--help` | Exits 1 | Exits 0 |

The GPU commands used `findOverlappingMeshes` with `useGpu=1`; neither runtime
reported a CPU fallback. This confirms the CLI shutdown fix on this workstation.
It does not establish that the older v1.0.4 Python access violation had the same
cause. Public Python initialization already worked in v1.1.0.

The runtime does not bundle the standard MaterialX shader-definition library:
an unconfigured lookup of `ND_standard_surface_surfaceshader` returns no node.
The regression check supplies a small self-contained definition, verifies its
parsed input, and requires normal process exit. The original DLL failure is
resolved; standard-library discovery is not claimed as provided by this package.

## Real assets and app integration

- Original Kitbash asset: `KB3D_AMP_BldgSmWaterGameStand_A.usd` from the local
  amusement-park library. Safe Cleanup, Inspect Stage, and Find Overlaps all pass
  without MaterialX warnings. Safe Cleanup preserves geometry, transforms, and
  stage metrics through the app's existing validation harness.
- A fresh process reopened both the original asset and saved Safe Cleanup output:
  the default prim, traversed prim count, and all 42 nonempty MaterialX layers match.
- The layered teapot fixture passes the same three workflows.
- The default teapot operation matrix records 31 passes, 17 intentional skips,
  and zero unexpected failures. `moveMaterials`, introduced upstream after
  v1.1.0, passes and is classified as advanced because it changes material hierarchy.
- App tests: 120 passed. Required Ruff and smoke-tool compilation checks pass.
- Portable app built using cached dependencies into
  `dist/runtime-v1.2.1/usd-optimize-app-0.1.3-windows-x86_64`.
  Its manifest records runtime 1.2.1. The packaged interpreter passes doctor,
  preset discovery, GUI construction on native Windows and offscreen platforms,
  and the three workflow smoke checks. A separate check with user-site packages
  disabled, matching the launcher, confirms MaterialX still works after packaging.
- The portable builder intentionally omits the upstream CLI executable; CLI GPU
  validation uses the complete release runtime. No visual/render equivalence or
  manual GUI acceptance is implied by these automated checks.

## Workaround cleanup

The v1.0.4 manual operation loader, renamed `operations_manual` directory, and
forced `os._exit()` shutdown are already absent from the app's tracked code.
This upgrade removes the remaining development-launcher bootstrap that selected
`vendor/usd_optimize` ahead of shared runtime discovery, and deletes the unused
`detect_required_python_version` stub. Both development launchers now use the
shared v1.2.1 default; CLI doctor and native GUI startup pass without overrides.

Fifteen ignored historical investigation scripts were moved out of `tools/`
into `reports/legacy-runtime-investigation-2026-09-09/tools/`, with original paths
and checksums in the adjacent `manifest.json`. This local archive is not part of
the PR or the portable app. Historical crash notes and older runtime packages
remain available as evidence.

Explicit runtime overrides, Windows DLL-directory registration, worker-process
isolation, and deterministic CPU overlap presets are retained. They support
runtime selection, native dependency loading, cancellation, and portable
workflow behavior; the upstream CLI fix does not replace those responsibilities.

## Local evidence and reproduction

Logs and generated USD outputs are under the ignored `reports/runtime-v1.2.1/`
directory. Main evidence files:

- `baseline-v1.1.0.log` and `package-v1.2.1.log`
- `gpu-shutdown-comparison.json` and the corresponding per-process logs
- `kitbash.log`, `kitbash-reopen.json`, and `teapot.log`
- `operation-matrix/operation-matrix.json`
- `portable-build.log` and `portable-package.log`

Run the package regression checks without another download:

```powershell
uv --system-certs run python tools/release_smoke/windows_package_smoke.py `
  --package-root ../usd-optimize/.artifacts/usd-optimize-v1.2.1-windows-25.11-py3.12/release-runtime `
  --overlap-fixture-usd tests/fixtures/mcusd/McUsd.usda

uv --system-certs run usdopt smoke-test --input tests/fixtures/teapot/teapot.usd
```
