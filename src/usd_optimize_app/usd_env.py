"""Runtime environment setup for the required usd-optimize artifact."""

from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path
from typing import Any

from usd_optimize_app.constants import USD_OPTIMIZE_RUNTIME_ROOT_ENV, runtime_root_candidates
from usd_optimize_app.errors import EnvironmentError
from usd_optimize_app.models import EnvironmentStatus
from usd_optimize_app.runtime_paths import (
    RuntimePaths,
    looks_like_runtime_root,
    resolve_runtime_paths,
)

_DLL_DIRECTORY_HANDLES: dict[str, Any] = {}


def find_runtime_root() -> Path | None:
    """Return a configured, portable, or development usd-optimize runtime root."""
    for candidate in runtime_root_candidates():
        runtime_root = candidate.expanduser().resolve()
        if looks_like_runtime_root(runtime_root):
            return runtime_root
    return None


def _missing_runtime_message() -> str:
    return (
        "Missing usd-optimize runtime artifact. Set "
        f"{USD_OPTIMIZE_RUNTIME_ROOT_ENV} or install the runtime."
    )


def configure_environment(runtime_root: Path | None = None) -> Path:
    """Add the required usd-optimize runtime artifact to this process."""
    resolved_runtime_root = runtime_root or find_runtime_root()
    if resolved_runtime_root is None:
        raise EnvironmentError(_missing_runtime_message())

    runtime_paths = resolve_runtime_paths(resolved_runtime_root)
    _ensure_runtime_dirs(runtime_paths)
    for python_path in [runtime_paths.python_dir, runtime_paths.usdpy_dir]:
        path_text = str(python_path)
        if path_text not in sys.path:
            sys.path.insert(0, path_text)
        _prepend_env_path("PYTHONPATH", path_text)

    for dll_path in [
        runtime_paths.lib_dir,
        runtime_paths.operations_dir,
        runtime_paths.extra_libs_dir,
    ]:
        path_text = str(dll_path)
        _prepend_env_path("PATH", path_text)
        _add_dll_directory_once(path_text)

    return runtime_paths.runtime_root


def get_runtime_paths(runtime_root: Path | None = None) -> RuntimePaths:
    """Return resolved runtime paths for the required artifact."""
    resolved_runtime_root = runtime_root or find_runtime_root()
    if resolved_runtime_root is None:
        raise EnvironmentError(_missing_runtime_message())
    return resolve_runtime_paths(resolved_runtime_root)


def check_environment() -> EnvironmentStatus:
    """Inspect the strict usd-optimize runtime artifact state."""
    runtime_root = find_runtime_root()
    current_python = f"{sys.version_info.major}.{sys.version_info.minor}"
    errors: list[str] = []

    if runtime_root is None:
        errors.append(_missing_runtime_message())
        return EnvironmentStatus(
            runtime_root=None,
            required_python=None,
            current_python=current_python,
            has_python_dir=False,
            has_usdpy_dir=False,
            has_lib_dir=False,
            has_extra_libs_dir=False,
            pxr_import_ok=False,
            usd_optimize_import_ok=False,
            errors=tuple(errors),
        )

    runtime_paths = resolve_runtime_paths(runtime_root)
    missing_dirs = [str(path) for path in runtime_paths.required_dirs if not path.exists()]
    if missing_dirs:
        errors.append(
            "Missing usd-optimize runtime artifact directories: " + ", ".join(missing_dirs)
        )

    configured = False
    if not missing_dirs:
        try:
            configure_environment(runtime_root)
            configured = True
        except EnvironmentError as error:
            errors.append(str(error))

    pxr_import_ok = configured and _can_import("pxr")
    usd_optimize_import_ok = configured and _can_import("usd_optimize")
    operation_count = 0
    operation_error = None
    if usd_optimize_import_ok:
        operation_count, operation_error = _get_operation_count()

    if configured and not pxr_import_ok:
        errors.append("Could not import pxr from the usd-optimize runtime artifact.")
    if configured and not usd_optimize_import_ok:
        errors.append("Could not import usd_optimize from the usd-optimize runtime artifact.")
    if operation_error:
        errors.append(f"Could not enumerate usd-optimize operations: {operation_error}")
    elif usd_optimize_import_ok and operation_count == 0:
        errors.append(
            "No compiled usd-optimize operations were registered by the runtime artifact."
        )

    return EnvironmentStatus(
        runtime_root=runtime_root,
        required_python=None,
        current_python=current_python,
        has_python_dir=runtime_paths.python_dir.exists(),
        has_usdpy_dir=runtime_paths.usdpy_dir.exists(),
        has_lib_dir=runtime_paths.lib_dir.exists(),
        has_extra_libs_dir=runtime_paths.extra_libs_dir.exists(),
        pxr_import_ok=pxr_import_ok,
        usd_optimize_import_ok=usd_optimize_import_ok,
        operation_count=operation_count,
        errors=tuple(errors),
    )


def list_available_operations() -> list[str]:
    """List operation names available in the required runtime artifact."""
    configure_environment()
    from usd_optimize.core import UsdOptimizeCore

    return sorted(UsdOptimizeCore.getInstance().getOperations())


def _ensure_runtime_dirs(runtime_paths: RuntimePaths) -> None:
    missing_dirs = [str(path) for path in runtime_paths.required_dirs if not path.exists()]
    if missing_dirs:
        message = "Missing usd-optimize runtime artifact directories: " + ", ".join(missing_dirs)
        raise EnvironmentError(message)


def _prepend_env_path(variable_name: str, path_text: str) -> None:
    existing_value = os.environ.get(variable_name, "")
    parts = [part for part in existing_value.split(os.pathsep) if part]
    if path_text not in parts:
        suffix = os.pathsep + existing_value if existing_value else ""
        os.environ[variable_name] = path_text + suffix


def _add_dll_directory_once(path_text: str) -> None:
    """Register a DLL directory only once for this process.

    Windows keeps each ``add_dll_directory`` registration alive until its
    handle is closed. Environment checks run before every isolated matrix job,
    so registering the same paths repeatedly eventually exhausts the Windows
    loader path limit.
    """
    if not hasattr(os, "add_dll_directory") or path_text in _DLL_DIRECTORY_HANDLES:
        return
    _DLL_DIRECTORY_HANDLES[path_text] = os.add_dll_directory(path_text)


def _can_import(module_name: str) -> bool:
    try:
        importlib.import_module(module_name)
    except Exception:
        return False
    return True


def _get_operation_count() -> tuple[int, str | None]:
    """Return the registered operation count and any native registry error."""
    try:
        from usd_optimize.core import UsdOptimizeCore

        return len(UsdOptimizeCore.getInstance().getOperations()), None
    except Exception as error:
        return 0, str(error)
