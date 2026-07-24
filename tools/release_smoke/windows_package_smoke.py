# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""Smoke-test a Windows Usd Optimize prebuilt package in isolated subprocesses."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
import zipfile
from pathlib import Path

CHECKS = {
    "pxr_import": """
        from pxr import Usd

        assert Usd.Stage.CreateInMemory()
        print("pxr import and in-memory stage creation succeeded")
    """,
    "core_registry": """
        from usd_optimize.core import UsdOptimizeCore

        operations = UsdOptimizeCore.getInstance().getOperations()
        assert "findOverlappingMeshes" in operations, operations
        print(f"operation registry contains {len(operations)} operations")
    """,
    "execute_config": """
        from pxr import Usd, UsdGeom
        from usd_optimize.core import ExecutionContext, UsdOptimizeCore

        stage = Usd.Stage.CreateInMemory()
        UsdGeom.Xform.Define(stage, "/World")
        UsdGeom.Cube.Define(stage, "/World/keep")
        UsdGeom.Cube.Define(stage, "/World/delete_me")
        context = ExecutionContext()
        assert context.set_stage(stage)
        results = UsdOptimizeCore.getInstance().executeConfig(
            context,
            [{"operation": "deletePrims", "primPaths": ["/World/delete_me"]}],
        )
        assert all(success for success, _error, _output in results), results
        assert stage.GetPrimAtPath("/World/keep")
        assert not stage.GetPrimAtPath("/World/delete_me")
        print("UsdOptimizeCore.executeConfig succeeded")
    """,
    "find_overlapping_meshes": """
        import os

        from pxr import Usd
        from usd_optimize.core import ExecutionContext, UsdOptimizeCore

        stage = Usd.Stage.Open(os.environ["USD_OPTIMIZE_OVERLAP_FIXTURE"])
        assert stage, os.environ["USD_OPTIMIZE_OVERLAP_FIXTURE"]
        context = ExecutionContext()
        assert context.set_stage(stage)
        context.analysisMode = 1
        results = UsdOptimizeCore.getInstance().executeConfig(
            context,
            [{
                "operation": "findOverlappingMeshes",
                "paths": [],
                "reportIslands": True,
                "fullStageReport": True,
                "useGpu": False,
            }],
        )
        assert len(results) == 1, results
        success, error, output = results[0]
        assert success, (error, output)
        analysis = output.get("analysis", {})
        expected_suppressed = int(os.environ["USD_OPTIMIZE_EXPECTED_SUPPRESSED_OVERLAPS"])
        expected_mesh_count = int(os.environ["USD_OPTIMIZE_EXPECTED_OVERLAPPING_MESH_COUNT"])
        assert analysis.get("suppressedOverlaps") == expected_suppressed, output
        assert len(analysis.get("overlappingMeshes", [])) == expected_mesh_count, output
        print(
            "findOverlappingMeshes CPU analysis returned "
            f"{expected_mesh_count} meshes and {expected_suppressed} suppressed overlaps"
        )
    """,
}

EXTERNAL_OPERATION_MATRIX_CHECK = """
    import json
    import os
    from pathlib import Path
    import re

    from pxr import Usd
    from usd_optimize.core import ExecutionContext, UsdOptimizeCore

    def validate_stage(stage, asset, asset_path):
        assert stage, f"failed to open {asset_path}"
        prims = list(stage.TraverseAll())
        assert prims, f"asset has no traversable prims: {asset_path}"
        for prim_path in asset.get("expected_prims", []):
            assert stage.GetPrimAtPath(prim_path), f"{asset['name']} is missing {prim_path}"
        return len(prims)

    manifest = json.loads(Path(os.environ["USD_OPTIMIZE_EXTERNAL_ASSET_MANIFEST"]).read_text(encoding="utf-8"))
    matrix = json.loads(Path(os.environ["USD_OPTIMIZE_EXTERNAL_OPERATION_MATRIX"]).read_text(encoding="utf-8"))
    assets_root = Path(os.environ["USD_OPTIMIZE_EXTERNAL_ASSETS_DIR"])
    assets = [asset for asset in manifest["assets"] if asset.get("smoke", True)]
    operations = matrix["operations"]
    assert assets, "external asset manifest has no smoke assets"
    assert operations, "operation matrix has no operations"
    core = UsdOptimizeCore.getInstance()
    completed = 0

    for asset in assets:
        asset_path = assets_root / asset["relative_path"]
        for operation in operations:
            stage = Usd.Stage.Open(str(asset_path))
            source_prim_count = validate_stage(stage, asset, asset_path)
            context = ExecutionContext()
            assert context.set_stage(stage)
            results = core.executeConfig(context, operation["commands"])
            assert all(success for success, _error, _output in results), (asset["name"], operation["name"], results)

            output_name = f".{asset_path.stem}.release_smoke_{operation['name']}.usda"
            output_path = asset_path.with_name(re.sub(r"[^A-Za-z0-9_.-]+", "_", output_name))
            try:
                assert stage.GetRootLayer().Export(str(output_path)), output_path
                output_stage = Usd.Stage.Open(str(output_path))
                output_prim_count = validate_stage(output_stage, asset, output_path)
                if operation.get("preserve_prim_count", True):
                    assert output_prim_count == source_prim_count, (
                        asset["name"], operation["name"], source_prim_count, output_prim_count
                    )
            finally:
                output_path.unlink(missing_ok=True)
            completed += 1
            print(f"external matrix passed: {operation['name']} on {asset['name']}")

    print(f"external operation matrix completed {completed} runs")
"""


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments.

    Returns:
        Parsed command-line arguments.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--package-archive", type=Path, help="Released package ZIP archive.")
    source.add_argument("--package-root", type=Path, help="Already extracted package root.")
    parser.add_argument(
        "--overlap-fixture-usd",
        type=Path,
        required=True,
        help="USD fixture with known CPU overlap-analysis results.",
    )
    parser.add_argument(
        "--expected-suppressed-overlaps",
        type=int,
        default=0,
        help="Expected findOverlappingMeshes suppressed-overlap count.",
    )
    parser.add_argument(
        "--expected-overlapping-mesh-count",
        type=int,
        default=22,
        help="Expected findOverlappingMeshes overlapping-mesh count.",
    )
    parser.add_argument(
        "--keep-extracted",
        action="store_true",
        help="Keep a temporary archive extraction for inspection.",
    )
    parser.add_argument("--external-asset-manifest", type=Path, help="Checksum-pinned external asset manifest.")
    parser.add_argument("--external-assets-dir", type=Path, help="Directory holding downloaded external assets.")
    parser.add_argument("--external-operation-matrix", type=Path, help="Conservative operation matrix JSON file.")
    return parser.parse_args()


def extract_archive(archive_path: Path, destination: Path) -> Path:
    """Extract a package archive and locate its package root.

    Args:
        archive_path: ZIP archive to extract.
        destination: Empty directory receiving extracted files.

    Returns:
        The directory containing the package layout.
    """
    with zipfile.ZipFile(archive_path) as archive:
        archive.extractall(destination)

    children = [path for path in destination.iterdir() if path.is_dir()]
    if len(children) == 1 and (children[0] / "python").is_dir():
        return children[0]
    return destination


def validate_package_root(package_root: Path) -> list[str]:
    """Return structural errors for an extracted Windows package.

    Args:
        package_root: Extracted package root directory.

    Returns:
        Human-readable structural errors. An empty list means the expected
        v1.1-era package layout is present.
    """
    expected_paths = (
        "python/usd_optimize/core/__init__.py",
        "usdpy/pxr",
        "lib/usd_optimize.core.dll",
        "extraLibs",
        "lib/operations/findOverlappingMeshes.dll",
    )
    return [f"Missing package path: {path}" for path in expected_paths if not (package_root / path).exists()]


def make_environment(
    package_root: Path,
    overlap_fixture: Path,
    expected_suppressed_overlaps: int,
    expected_overlapping_mesh_count: int,
    external_asset_manifest: Path | None = None,
    external_assets_dir: Path | None = None,
    external_operation_matrix: Path | None = None,
) -> dict[str, str]:
    """Create a clean child-process environment for package loading.

    Args:
        package_root: Extracted package root directory.
        overlap_fixture: USD fixture for the targeted overlap check.
        expected_suppressed_overlaps: Expected suppressed-overlap count.
        expected_overlapping_mesh_count: Expected reported overlapping-mesh count.
        external_asset_manifest: Optional checksum-pinned external asset manifest.
        external_assets_dir: Optional cache containing the external assets.
        external_operation_matrix: Optional conservative operation matrix.

    Returns:
        Environment values for Python and CLI smoke subprocesses.
    """
    environment = os.environ.copy()
    python_paths = [str(package_root / "python"), str(package_root / "usdpy")]
    existing_python_path = environment.get("PYTHONPATH")
    if existing_python_path:
        python_paths.append(existing_python_path)
    environment["PYTHONPATH"] = os.pathsep.join(python_paths)
    environment["PATH"] = os.pathsep.join(
        [str(package_root / "lib"), str(package_root / "extraLibs"), environment.get("PATH", "")]
    )
    environment["PYTHONUTF8"] = "1"
    environment["USD_OPTIMIZE_OVERLAP_FIXTURE"] = str(overlap_fixture)
    environment["USD_OPTIMIZE_EXPECTED_SUPPRESSED_OVERLAPS"] = str(
        expected_suppressed_overlaps
    )
    environment["USD_OPTIMIZE_EXPECTED_OVERLAPPING_MESH_COUNT"] = str(
        expected_overlapping_mesh_count
    )
    if external_asset_manifest:
        environment["USD_OPTIMIZE_EXTERNAL_ASSET_MANIFEST"] = str(external_asset_manifest)
        environment["USD_OPTIMIZE_EXTERNAL_ASSETS_DIR"] = str(external_assets_dir)
        environment["USD_OPTIMIZE_EXTERNAL_OPERATION_MATRIX"] = str(external_operation_matrix)
    return environment


def run_python_check(name: str, source: str, environment: dict[str, str]) -> bool:
    """Run one Python check in a new process.

    Args:
        name: Human-readable check name.
        source: Python source code to execute.
        environment: Package-configured child-process environment.

    Returns:
        ``True`` only when the subprocess exits successfully.
    """
    print(f"\n=== {name} ===", flush=True)
    process = subprocess.run(
        [sys.executable, "-c", textwrap.dedent(source)],
        env=environment,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    print(process.stdout.rstrip(), flush=True)
    if process.returncode:
        print(f"FAILED: {name} exited with code {process.returncode}", flush=True)
        return False
    print(f"PASSED: {name}", flush=True)
    return True


def run_cli_check(package_root: Path, overlap_fixture: Path, environment: dict[str, str]) -> bool:
    """Run the packaged CLI against the targeted overlap fixture.

    Args:
        package_root: Extracted package root directory.
        overlap_fixture: USD fixture with known overlap results.
        environment: Package-configured child-process environment.

    Returns:
        ``True`` only when the CLI exits successfully.
    """
    executable = package_root / "bin" / "usdOptimize.exe"
    if not executable.is_file():
        print("\nSKIPPED: packaged_cli_find_overlapping_meshes (CLI is not shipped in this package)", flush=True)
        return True

    print("\n=== packaged_cli_find_overlapping_meshes ===", flush=True)
    command = [
        str(executable),
        "--input",
        str(overlap_fixture),
        "--analysis",
        "--operation",
        "findOverlappingMeshes",
        "--argument",
        "useGpu=0",
    ]
    process = subprocess.run(
        command,
        env=environment,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    print(process.stdout.rstrip(), flush=True)
    if process.returncode:
        print(f"FAILED: packaged_cli_find_overlapping_meshes exited with code {process.returncode}", flush=True)
        return False
    print("PASSED: packaged_cli_find_overlapping_meshes", flush=True)
    return True


def main() -> int:
    """Run the Windows package smoke suite.

    Returns:
        Process exit status.
    """
    args = parse_args()
    fixture = args.overlap_fixture_usd.resolve()
    if not fixture.is_file():
        print(f"Missing overlap fixture: {fixture}", flush=True)
        return 1

    external_paths = (args.external_asset_manifest, args.external_assets_dir, args.external_operation_matrix)
    if any(external_paths) and not all(external_paths):
        print(
            "External matrix requires --external-asset-manifest, --external-assets-dir, and "
            "--external-operation-matrix together.",
            flush=True,
        )
        return 1
    if all(external_paths):
        external_manifest = args.external_asset_manifest.resolve()
        external_assets = args.external_assets_dir.resolve()
        external_matrix = args.external_operation_matrix.resolve()
        if not external_manifest.is_file() or not external_assets.is_dir() or not external_matrix.is_file():
            print("External matrix manifest, assets directory, or operation matrix is missing.", flush=True)
            return 1
    else:
        external_manifest = None
        external_assets = None
        external_matrix = None

    temporary_directory = None
    if args.package_root:
        package_root = args.package_root.resolve()
    else:
        archive = args.package_archive.resolve()
        if not archive.is_file():
            print(f"Missing package archive: {archive}", flush=True)
            return 1
        temporary_directory = Path(tempfile.mkdtemp(prefix="usd_optimize_release_smoke_"))
        package_root = extract_archive(archive, temporary_directory)

    try:
        errors = validate_package_root(package_root)
        if errors:
            print("\n".join(errors), flush=True)
            return 1

        print(f"Package root: {package_root}", flush=True)
        print(f"Python executable: {sys.executable}", flush=True)
        environment = make_environment(
            package_root,
            fixture,
            args.expected_suppressed_overlaps,
            args.expected_overlapping_mesh_count,
            external_manifest,
            external_assets,
            external_matrix,
        )
        results = [run_python_check(name, source, environment) for name, source in CHECKS.items()]
        if external_manifest:
            results.append(run_python_check("external_operation_matrix", EXTERNAL_OPERATION_MATRIX_CHECK, environment))
        results.append(run_cli_check(package_root, fixture, environment))
        return 0 if all(results) else 1
    finally:
        if temporary_directory and not args.keep_extracted:
            shutil.rmtree(temporary_directory, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
