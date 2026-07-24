# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""Download and checksum-verify external USD assets for release smoke tests."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import tempfile
import urllib.request
from pathlib import Path


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments.

    Returns:
        Parsed command-line arguments.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True, help="External asset manifest JSON file.")
    parser.add_argument("--assets-dir", type=Path, required=True, help="Cache directory for external assets.")
    parser.add_argument("--timeout", type=int, default=60, help="Download timeout for each asset in seconds.")
    return parser.parse_args()


def hash_file(asset_path: Path) -> str:
    """Return the SHA-256 digest for an asset.

    Args:
        asset_path: Local asset file to hash.

    Returns:
        Lowercase hexadecimal SHA-256 digest.
    """
    digest = hashlib.sha256()
    with asset_path.open("rb") as asset_file:
        for chunk in iter(lambda: asset_file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def ensure_asset(asset: dict, assets_dir: Path, timeout: int) -> None:
    """Download one asset when absent and verify its expected SHA-256 digest.

    Args:
        asset: Manifest entry describing the source, relative path, and digest.
        assets_dir: Root directory for the local asset cache.
        timeout: Network timeout in seconds.

    Raises:
        RuntimeError: If the downloaded file's digest does not match the manifest.
    """
    destination = assets_dir / asset["relative_path"]
    expected_hash = asset["sha256"].lower()
    if destination.is_file() and hash_file(destination) == expected_hash:
        print(f"cached: {asset['name']}", flush=True)
        return

    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(delete=False, dir=destination.parent) as temporary_file:
        temporary_path = Path(temporary_file.name)
        with urllib.request.urlopen(asset["url"], timeout=timeout) as response:
            shutil.copyfileobj(response, temporary_file)
    temporary_path.replace(destination)

    actual_hash = hash_file(destination)
    if actual_hash != expected_hash:
        destination.unlink(missing_ok=True)
        raise RuntimeError(f"SHA-256 mismatch for {asset['name']}: expected {expected_hash}, got {actual_hash}")
    print(f"downloaded: {asset['name']}", flush=True)


def main() -> int:
    """Populate the external asset cache.

    Returns:
        Process exit status.
    """
    args = parse_args()
    manifest_path = args.manifest.resolve()
    assets_dir = args.assets_dir.resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for asset in manifest["assets"]:
        ensure_asset(asset, assets_dir, args.timeout)
    print(f"External assets ready: {len(manifest['assets'])}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
