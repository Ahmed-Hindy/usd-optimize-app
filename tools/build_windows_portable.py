"""Build a self-contained Windows distribution for USD Optimize App."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path

REQUIRED_RUNTIME_DIRS = ("python", "usdpy", "lib", "lib/operations", "extraLibs")
PYTHON_PRUNE_PATHS = (
    "Doc",
    "include",
    "libs",
    "tcl",
    "NEWS.txt",
    "Scripts",
    "Lib/test",
    "Lib/idlelib",
    "Lib/tkinter",
    "Lib/turtledemo",
    "Lib/ensurepip",
    "Lib/venv",
    "Lib/lib2to3",
    "Lib/msilib",
)
PYTHON_RUNTIME_DEV_SUFFIXES = {".exp", ".lib", ".pdb"}
PYSIDE_KEEP_MODULES = {"QtCore", "QtGui", "QtSvg", "QtWidgets"}
PYSIDE_KEEP_PLUGINS = {
    "iconengines": {"qsvgicon.dll"},
    "imageformats": {"qgif.dll", "qico.dll", "qjpeg.dll", "qsvg.dll"},
    "platforms": {"qoffscreen.dll", "qwindows.dll"},
    "styles": {"qmodernwindowsstyle.dll"},
}
USD_RUNTIME_PRUNE_DIRS = ("bin", "docs", "include")
USD_RUNTIME_DEV_SUFFIXES = {".exp", ".lib", ".pdb"}


def main(argv: list[str] | None = None) -> int:
    """Build and optionally archive the portable Windows application.

    Args:
        argv: Optional command-line arguments.

    Returns:
        Process exit code.
    """
    args = _build_parser().parse_args(argv)
    project_root = Path(__file__).resolve().parents[1]
    app_version = args.version or _read_project_version(project_root)
    output_dir = args.output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    artifact_name = f"usd-optimize-app-{app_version}-windows-x86_64"
    artifact_root = output_dir / artifact_name

    with tempfile.TemporaryDirectory(prefix="usdopt_portable_") as temporary_dir:
        runtime_root = _resolve_runtime_root(args, Path(temporary_dir))
        _validate_python_root(args.python_root)
        _validate_runtime_root(runtime_root)
        _replace_directory(artifact_root)
        _copy_python(args.python_root, artifact_root / "python")
        _install_application(
            project_root, artifact_root / "python" / "python.exe", Path(temporary_dir)
        )
        _prune_python_runtime(artifact_root / "python")
        _copy_runtime(runtime_root, artifact_root / "runtime" / "usd-optimize")
        _prune_usd_runtime(artifact_root / "runtime" / "usd-optimize")
        shutil.copytree(project_root / "presets", artifact_root / "presets")
        shutil.copytree(project_root / "docs", artifact_root / "docs")
        shutil.copy2(project_root / "README.md", artifact_root / "README.md")
        _copy_licenses(args.usd_optimize_license, artifact_root, project_root)
        _write_launchers(artifact_root)
        _write_manifest(artifact_root, app_version, args.usd_optimize_version)
        _run_smoke_tests(artifact_root, args.smoke_input)

    archive_path = None
    if not args.no_archive:
        archive_path = _create_archive(artifact_root)
        _write_sha256(archive_path)

    print(f"Portable directory: {artifact_root}")
    if archive_path:
        print(f"Portable archive: {archive_path}")
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    runtime_group = parser.add_mutually_exclusive_group(required=True)
    runtime_group.add_argument("--runtime-root", type=Path, help="Extracted usd-optimize root.")
    runtime_group.add_argument("--runtime-archive", type=Path, help="NVIDIA release ZIP.")
    parser.add_argument("--python-root", required=True, type=Path, help="Portable CPython root.")
    parser.add_argument("--output-dir", type=Path, default=Path("dist"), help="Output directory.")
    parser.add_argument("--version", help="Application version. Defaults to pyproject.toml.")
    parser.add_argument(
        "--usd-optimize-version", default="1.1.0", help="Bundled NVIDIA runtime version."
    )
    parser.add_argument(
        "--usd-optimize-license", required=True, type=Path, help="Upstream LICENSE file."
    )
    parser.add_argument("--smoke-input", type=Path, help="USD file used for packaged smoke tests.")
    parser.add_argument("--no-archive", action="store_true", help="Keep only the portable folder.")
    return parser


def _read_project_version(project_root: Path) -> str:
    pyproject_text = (project_root / "pyproject.toml").read_text(encoding="utf-8")
    version_match = re.search(r'^version = "([^"]+)"$', pyproject_text, re.MULTILINE)
    if version_match is None:
        raise RuntimeError("Could not read the application version from pyproject.toml.")
    return version_match.group(1)


def _resolve_runtime_root(args: argparse.Namespace, temporary_dir: Path) -> Path:
    if args.runtime_root:
        return args.runtime_root.expanduser().resolve()

    runtime_archive = args.runtime_archive.expanduser().resolve()
    if not runtime_archive.is_file():
        raise FileNotFoundError(f"Runtime archive does not exist: {runtime_archive}")
    extraction_root = temporary_dir / "runtime"
    with zipfile.ZipFile(runtime_archive) as archive:
        archive.extractall(extraction_root)

    candidates = [extraction_root]
    candidates.extend(path for path in extraction_root.rglob("*") if path.is_dir())
    valid_candidates = [path for path in candidates if _looks_like_runtime_root(path)]
    if not valid_candidates:
        raise RuntimeError(f"No usable usd-optimize runtime found in {runtime_archive}")
    return min(valid_candidates, key=lambda path: len(path.parts))


def _validate_python_root(python_root: Path) -> None:
    resolved_root = python_root.expanduser().resolve()
    required_paths = ("python.exe", "pythonw.exe", "Lib")
    missing = [name for name in required_paths if not (resolved_root / name).exists()]
    if missing:
        raise RuntimeError(f"Python root is missing required paths: {', '.join(missing)}")


def _looks_like_runtime_root(runtime_root: Path) -> bool:
    return all((runtime_root / relative_path).exists() for relative_path in REQUIRED_RUNTIME_DIRS)


def _validate_runtime_root(runtime_root: Path) -> None:
    missing = [path for path in REQUIRED_RUNTIME_DIRS if not (runtime_root / path).exists()]
    if missing:
        raise RuntimeError(f"Runtime root is missing required paths: {', '.join(missing)}")
    core_library = runtime_root / "lib" / "usd_optimize.core.dll"
    if not core_library.is_file():
        raise RuntimeError(f"Runtime core library is missing: {core_library}")


def _replace_directory(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True)


def _copy_python(source_root: Path, destination_root: Path) -> None:
    resolved_source = source_root.expanduser().resolve()
    shutil.copytree(
        resolved_source,
        destination_root,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".pytest_cache"),
    )
    site_packages = destination_root / "Lib" / "site-packages"
    if site_packages.exists():
        shutil.rmtree(site_packages)
    site_packages.mkdir(parents=True)
    scripts_dir = destination_root / "Scripts"
    if scripts_dir.exists():
        shutil.rmtree(scripts_dir)
    scripts_dir.mkdir()


def _install_application(project_root: Path, python_executable: Path, temporary_dir: Path) -> None:
    uv_executable = shutil.which("uv")
    if not uv_executable:
        raise RuntimeError("uv is required to build the portable application.")

    requirements_path = temporary_dir / "runtime-requirements.txt"
    _run_command(
        [
            uv_executable,
            "export",
            "--frozen",
            "--no-dev",
            "--no-emit-project",
            "--format",
            "requirements-txt",
            "--output-file",
            str(requirements_path),
        ],
        cwd=project_root,
    )
    environment = os.environ.copy()
    environment.pop("PYTHONHOME", None)
    environment.pop("PYTHONPATH", None)
    environment["PYTHONNOUSERSITE"] = "1"
    environment["UV_LINK_MODE"] = "copy"
    _run_command(
        [
            uv_executable,
            "pip",
            "install",
            "--python",
            str(python_executable),
            "--requirement",
            str(requirements_path),
        ],
        cwd=project_root,
        env=environment,
    )
    _run_command(
        [
            uv_executable,
            "pip",
            "install",
            "--python",
            str(python_executable),
            "--no-deps",
            str(project_root),
        ],
        cwd=project_root,
        env=environment,
    )


def _copy_runtime(source_root: Path, destination_root: Path) -> None:
    shutil.copytree(
        source_root,
        destination_root,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".pytest_cache"),
    )


def _prune_python_runtime(python_root: Path) -> None:
    """Remove development-only CPython and Qt files from the portable runtime.

    Args:
        python_root: Copied CPython installation containing the app and PySide6.
    """
    before_bytes = _directory_size(python_root)
    for relative_path in PYTHON_PRUNE_PATHS:
        _remove_path(python_root / relative_path)
    for executable_path in python_root.glob("*.exe"):
        if executable_path.name.lower() not in {"python.exe", "pythonw.exe"}:
            _remove_path(executable_path)

    dll_dir = python_root / "DLLs"
    for filename in ("_tkinter.pyd", "tcl86t.dll", "tk86t.dll"):
        _remove_path(dll_dir / filename)
    for test_extension in dll_dir.glob("_test*.pyd"):
        _remove_path(test_extension)
    for limited_extension in dll_dir.glob("xxlimited*.pyd"):
        _remove_path(limited_extension)

    site_packages = python_root / "Lib" / "site-packages"
    _prune_pyside(site_packages / "PySide6")
    _prune_shiboken(site_packages / "shiboken6")
    for path in list(python_root.rglob("*")):
        if path.is_file() and path.suffix.lower() in PYTHON_RUNTIME_DEV_SUFFIXES:
            _remove_path(path)
    _remove_python_caches(python_root)
    after_bytes = _directory_size(python_root)
    print(f"Pruned Python/Qt runtime: {_format_mib(before_bytes - after_bytes)} MiB removed")


def _prune_pyside(pyside_root: Path) -> None:
    """Keep only the Qt modules and plugins used by the Widgets GUI."""
    if not pyside_root.is_dir():
        raise RuntimeError(f"PySide6 package is missing: {pyside_root}")

    for directory_name in (
        "doc",
        "glue",
        "include",
        "lib",
        "metatypes",
        "qml",
        "resources",
        "scripts",
        "support",
        "translations",
        "typesystems",
    ):
        _remove_path(pyside_root / directory_name)
    _prune_pyside_files(pyside_root)
    _prune_pyside_plugins(pyside_root / "plugins")


def _prune_pyside_files(pyside_root: Path) -> None:
    """Remove unused PySide modules, tools, stubs, and development files."""
    for path in list(pyside_root.iterdir()):
        if path.is_file() and _should_remove_pyside_file(path):
            _remove_path(path)


def _should_remove_pyside_file(path: Path) -> bool:
    """Return whether one top-level PySide file is unnecessary at runtime."""
    filename = path.name
    if path.suffix.lower() in {".exe", ".lib", ".pyi"}:
        return True
    if filename in {
        "PySide6_Essentials.json",
        "opengl32sw.dll",
        "pyside6qml.abi3.dll",
        "py.typed",
    }:
        return True

    module_match = re.fullmatch(r"(Qt[A-Za-z0-9]+)\.pyd", filename)
    if module_match is not None:
        return module_match.group(1) not in PYSIDE_KEEP_MODULES
    library_match = re.fullmatch(r"Qt6([A-Za-z0-9]+)\.dll", filename)
    if library_match is not None:
        return f"Qt{library_match.group(1)}" not in PYSIDE_KEEP_MODULES
    return False


def _prune_pyside_plugins(plugins_root: Path) -> None:
    """Keep only plugins required by native and offscreen Widgets smoke tests."""
    if not plugins_root.is_dir():
        return
    for plugin_directory in list(plugins_root.iterdir()):
        allowed_files = PYSIDE_KEEP_PLUGINS.get(plugin_directory.name)
        if allowed_files is None:
            _remove_path(plugin_directory)
            continue
        for plugin_file in list(plugin_directory.iterdir()):
            if plugin_file.name not in allowed_files:
                _remove_path(plugin_file)


def _prune_shiboken(shiboken_root: Path) -> None:
    """Remove Shiboken headers, type stubs, and import libraries."""
    if not shiboken_root.is_dir():
        raise RuntimeError(f"Shiboken package is missing: {shiboken_root}")
    _remove_path(shiboken_root / "include")
    for path in list(shiboken_root.iterdir()):
        if path.suffix.lower() in {".lib", ".pyi"} or path.name == "py.typed":
            _remove_path(path)


def _prune_usd_runtime(runtime_root: Path) -> None:
    """Remove headers, documentation, and linker files from usd-optimize."""
    before_bytes = _directory_size(runtime_root)
    for directory_name in USD_RUNTIME_PRUNE_DIRS:
        _remove_path(runtime_root / directory_name)
    for path in list(runtime_root.rglob("*")):
        if path.is_file() and path.suffix.lower() in USD_RUNTIME_DEV_SUFFIXES:
            _remove_path(path)
    _remove_python_caches(runtime_root)
    after_bytes = _directory_size(runtime_root)
    print(f"Pruned usd-optimize runtime: {_format_mib(before_bytes - after_bytes)} MiB removed")


def _remove_python_caches(root: Path) -> None:
    for cache_directory in list(root.rglob("__pycache__")):
        _remove_path(cache_directory)
    for bytecode_file in list(root.rglob("*.pyc")):
        _remove_path(bytecode_file)


def _remove_path(path: Path) -> None:
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
    elif path.exists() or path.is_symlink():
        path.unlink()


def _directory_size(path: Path) -> int:
    return sum(file_path.stat().st_size for file_path in path.rglob("*") if file_path.is_file())


def _format_mib(byte_count: int) -> str:
    return f"{byte_count / (1024 * 1024):.2f}"


def _copy_licenses(license_path: Path, artifact_root: Path, project_root: Path) -> None:
    resolved_license = license_path.expanduser().resolve()
    if not resolved_license.is_file():
        raise FileNotFoundError(f"usd-optimize license does not exist: {resolved_license}")

    licenses_dir = artifact_root / "licenses"
    licenses_dir.mkdir()
    shutil.copy2(resolved_license, licenses_dir / "NVIDIA-usd-optimize-LICENSE.txt")

    resource_dir = project_root / "src" / "usd_optimize_app" / "resources"
    shutil.copy2(resource_dir / "OpenUSD-LICENSE.txt", licenses_dir / "OpenUSD-LICENSE.txt")
    shutil.copy2(resource_dir / "OpenUSD-NOTICE.txt", licenses_dir / "OpenUSD-NOTICE.txt")


def _write_launchers(artifact_root: Path) -> None:
    cli_launcher = r"""@echo off
setlocal
set "APP_ROOT=%~dp0"
set "PYTHONHOME=%APP_ROOT%python"
set "PYTHONNOUSERSITE=1"
set "USD_OPTIMIZE_RUNTIME_ROOT=%APP_ROOT%runtime\usd-optimize"
set "USD_OPTIMIZE_APP_PRESETS_DIR=%APP_ROOT%presets"
"%APP_ROOT%python\python.exe" -I -m usd_optimize_app.cli %*
exit /b %ERRORLEVEL%
"""
    gui_launcher = r"""@echo off
setlocal
set "APP_ROOT=%~dp0"
set "PYTHONHOME=%APP_ROOT%python"
set "PYTHONNOUSERSITE=1"
set "USD_OPTIMIZE_RUNTIME_ROOT=%APP_ROOT%runtime\usd-optimize"
set "USD_OPTIMIZE_APP_PRESETS_DIR=%APP_ROOT%presets"
"%APP_ROOT%python\pythonw.exe" -I -m usd_optimize_app.gui.app %*
exit /b %ERRORLEVEL%
"""
    (artifact_root / "usdopt.cmd").write_text(cli_launcher, encoding="utf-8", newline="\r\n")
    (artifact_root / "usdopt-gui.cmd").write_text(gui_launcher, encoding="utf-8", newline="\r\n")


def _write_manifest(artifact_root: Path, app_version: str, usd_optimize_version: str) -> None:
    python_executable = artifact_root / "python" / "python.exe"
    environment = _portable_environment(artifact_root)
    python_version = _capture_command(
        [str(python_executable), "-I", "--version"], cwd=artifact_root, env=environment
    ).strip()
    pyside_version = _capture_command(
        [str(python_executable), "-I", "-c", "import PySide6; print(PySide6.__version__)"],
        cwd=artifact_root,
        env=environment,
    ).strip()
    manifest = {
        "application": {"name": "usd-optimize-app", "version": app_version},
        "runtime": {
            "name": "NVIDIA usd-optimize",
            "version": usd_optimize_version,
            "root": "runtime/usd-optimize",
        },
        "python": {"version": python_version, "root": "python"},
        "qt": {"binding": "PySide6", "version": pyside_version},
        "entry_points": {"cli": "usdopt.cmd", "gui": "usdopt-gui.cmd"},
        "shared_backend": "usd_optimize_app.backend",
    }
    manifest_path = artifact_root / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8", newline="\n")


def _run_smoke_tests(artifact_root: Path, smoke_input: Path | None) -> None:
    python_executable = artifact_root / "python" / "python.exe"
    environment = _portable_environment(artifact_root)
    base_python_command = [str(python_executable), "-I"]
    _run_command(
        base_python_command + ["-m", "usd_optimize_app.cli", "doctor"],
        cwd=artifact_root,
        env=environment,
    )
    _run_command(
        base_python_command + ["-m", "usd_optimize_app.cli", "list-presets"],
        cwd=artifact_root,
        env=environment,
    )

    gui_launcher = artifact_root / "usdopt-gui.cmd"
    for platform_name in ("offscreen", "windows"):
        gui_environment = environment.copy()
        gui_environment["QT_QPA_PLATFORM"] = platform_name
        _run_command(
            ["cmd.exe", "/d", "/c", str(gui_launcher), "--startup-smoke-test"],
            cwd=artifact_root,
            env=gui_environment,
        )
    if smoke_input is None:
        return

    resolved_input = smoke_input.expanduser().resolve()
    if not resolved_input.is_file():
        raise FileNotFoundError(f"Smoke-test USD does not exist: {resolved_input}")
    with tempfile.TemporaryDirectory(prefix="usdopt_artifact_smoke_") as smoke_temp:
        smoke_dir = Path(smoke_temp)
        smoke_command = base_python_command + [
            "-m",
            "usd_optimize_app.cli",
            "smoke-test",
            "--input",
            str(resolved_input),
            "--output-dir",
            str(smoke_dir),
            "--preset",
            "safe_publish",
            "--preset",
            "diagnostics",
            "--preset",
            "find_overlaps",
        ]
        _run_command(smoke_command, cwd=artifact_root, env=environment)
        optimized_output = (
            smoke_dir / resolved_input.stem / f"{resolved_input.stem}.safe_publish.usda"
        )
        if not optimized_output.is_file():
            raise RuntimeError(f"Packaged optimization did not create {optimized_output}")


def _portable_environment(artifact_root: Path) -> dict[str, str]:
    environment = os.environ.copy()
    runtime_root = artifact_root / "runtime" / "usd-optimize"
    environment["PYTHONHOME"] = str(artifact_root / "python")
    environment["PYTHONNOUSERSITE"] = "1"
    environment.pop("PYTHONPATH", None)
    environment["USD_OPTIMIZE_RUNTIME_ROOT"] = str(runtime_root)
    environment["USD_OPTIMIZE_APP_PRESETS_DIR"] = str(artifact_root / "presets")
    runtime_paths = [
        artifact_root / "python",
        runtime_root / "lib",
        runtime_root / "lib" / "operations",
        runtime_root / "extraLibs",
    ]
    portable_path = os.pathsep.join(str(path) for path in runtime_paths)
    environment["PATH"] = portable_path + os.pathsep + environment.get("PATH", "")
    return environment


def _create_archive(artifact_root: Path) -> Path:
    archive_path = artifact_root.parent / f"{artifact_root.name}.zip"
    if archive_path.exists():
        archive_path.unlink()
    print(f"Creating archive: {archive_path}")
    with zipfile.ZipFile(
        archive_path,
        mode="w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
    ) as archive:
        for file_path in sorted(path for path in artifact_root.rglob("*") if path.is_file()):
            archive_name = Path(artifact_root.name) / file_path.relative_to(artifact_root)
            archive.write(file_path, archive_name)
    return archive_path


def _write_sha256(archive_path: Path) -> None:
    digest = hashlib.sha256()
    with archive_path.open("rb") as archive_file:
        for chunk in iter(lambda: archive_file.read(1024 * 1024), b""):
            digest.update(chunk)
    checksum_path = archive_path.with_suffix(archive_path.suffix + ".sha256")
    checksum_path.write_text(
        f"{digest.hexdigest()}  {archive_path.name}\n", encoding="utf-8", newline="\n"
    )


def _run_command(command: list[str], cwd: Path, env: dict[str, str] | None = None) -> None:
    print(f"> {' '.join(command)}")
    subprocess.run(command, cwd=cwd, env=env, check=True)


def _capture_command(
    command: list[str], cwd: Path | None = None, env: dict[str, str] | None = None
) -> str:
    return subprocess.run(
        command, cwd=cwd, env=env, check=True, capture_output=True, text=True
    ).stdout


if __name__ == "__main__":
    raise SystemExit(main())
