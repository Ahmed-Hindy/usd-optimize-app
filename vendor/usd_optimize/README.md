# NVIDIA usd-optimize package location

This folder is not searched automatically. Development launchers use the shared
runtime discovery: an explicit `USD_OPTIMIZE_RUNTIME_ROOT` override, a portable
bundle, or the sibling v1.2.1 runtime artifact.

To use a package stored here, set `USD_OPTIMIZE_RUNTIME_ROOT` to its extracted
root. See [runtime setup](../../docs/usd-optimize-source-dependency.md).

This repository intentionally does not vendor NVIDIA binaries.
