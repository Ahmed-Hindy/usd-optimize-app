# External Asset Smoke Tests

`usdopt smoke-test --external-assets` reuses the same OpenUSD asset set used by the sibling `usd-optimize` Windows CI.

## Source manifest

```text
../usd-optimize/tools/windows_prebuilt_repro/external_usd_assets.json
```

The manifest contains ten pinned OpenUSD files:

- seven primary smoke assets;
- three dependency files for referenced assets.

The app verifies the manifest SHA-256 hashes before running tests.

## Required local cache

```text
../usd-optimize/.cache/usd-assets
```

The cache is produced by the sibling `usd-optimize` downloader:

```powershell
cd ../usd-optimize
python tools/windows_prebuilt_repro/download_external_assets.py --manifest tools/windows_prebuilt_repro/external_usd_assets.json --assets-dir .cache/usd-assets
```

## Commands

Run diagnostics across the seven primary assets:

```powershell
uv run usdopt smoke-test --external-assets
```

Run `safe_publish` across the same assets:

```powershell
uv run usdopt smoke-test --external-assets --preset safe_publish
```

## Current result

Validated on 2026-07-04:

```text
Assets: 7
Operation count: 44
Preset runs: all OK
Smoke test passed.
```

Both `diagnostics` and `safe_publish` passed across the seven primary smoke assets.

## Reference handling

Some OpenUSD tutorial assets use relative references. The smoke harness copies the full manifest asset tree into:

```text
reports/smoke-tests/external-assets
```

The optimized outputs are written beside the copied inputs so relative references still resolve when outputs are reopened and expected prims are checked.
