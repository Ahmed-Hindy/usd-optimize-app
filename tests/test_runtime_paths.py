from pathlib import Path

from usd_optimize_app.runtime_paths import resolve_runtime_paths


def test_resolve_runtime_paths_uses_required_artifact_layout(tmp_path: Path) -> None:
    runtime_root = tmp_path / "release-runtime"
    runtime_paths = resolve_runtime_paths(runtime_root)

    assert runtime_paths.runtime_root == runtime_root
    assert runtime_paths.python_dir == runtime_root / "python"
    assert runtime_paths.usdpy_dir == runtime_root / "usdpy"
    assert runtime_paths.lib_dir == runtime_root / "lib"
    assert runtime_paths.operations_dir == runtime_root / "lib" / "operations"
    assert runtime_paths.extra_libs_dir == runtime_root / "extraLibs"
