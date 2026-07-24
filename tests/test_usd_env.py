"""Tests for usd-optimize runtime environment setup."""

from __future__ import annotations

import sys
from pathlib import Path

from usd_optimize_app import constants, usd_env
from usd_optimize_app.constants import (
    USD_OPTIMIZE_PACKAGE_ROOT_ENV,
    USD_OPTIMIZE_RUNTIME_ROOT_ENV,
)


def test_find_runtime_root_prefers_an_explicit_override(monkeypatch, tmp_path: Path) -> None:
    """Allow CI and local validation to select an extracted package explicitly."""
    runtime_root = tmp_path / "release-runtime"
    for directory_name in ("python", "usdpy", "lib"):
        (runtime_root / directory_name).mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv(USD_OPTIMIZE_RUNTIME_ROOT_ENV, str(runtime_root))

    assert usd_env.find_runtime_root() == runtime_root


def test_find_runtime_root_uses_the_portable_artifact_layout(monkeypatch, tmp_path: Path) -> None:
    """Discover the runtime bundled beside the portable Python distribution."""
    portable_runtime = tmp_path / "artifact" / "runtime" / "usd-optimize"
    development_runtime = tmp_path / "development-runtime"
    for runtime_root in (portable_runtime, development_runtime):
        for directory_name in ("python", "usdpy", "lib"):
            (runtime_root / directory_name).mkdir(parents=True, exist_ok=True)

    monkeypatch.delenv(USD_OPTIMIZE_RUNTIME_ROOT_ENV, raising=False)
    monkeypatch.delenv(USD_OPTIMIZE_PACKAGE_ROOT_ENV, raising=False)
    monkeypatch.setattr(constants, "PORTABLE_USD_OPTIMIZE_RUNTIME_ROOT", portable_runtime)
    monkeypatch.setattr(constants, "DEVELOPMENT_USD_OPTIMIZE_RUNTIME_ROOT", development_runtime)

    assert usd_env.find_runtime_root() == portable_runtime


def test_find_runtime_root_supports_the_legacy_package_override(
    monkeypatch, tmp_path: Path
) -> None:
    """Keep existing launch scripts functional while standardizing the new variable."""
    runtime_root = tmp_path / "legacy-runtime"
    for directory_name in ("python", "usdpy", "lib"):
        (runtime_root / directory_name).mkdir(parents=True, exist_ok=True)
    monkeypatch.delenv(USD_OPTIMIZE_RUNTIME_ROOT_ENV, raising=False)
    monkeypatch.setenv(USD_OPTIMIZE_PACKAGE_ROOT_ENV, str(runtime_root))

    assert usd_env.find_runtime_root() == runtime_root


def test_configure_environment_registers_the_standard_package_paths(
    monkeypatch, tmp_path: Path
) -> None:
    """Use the standard package layout without custom loader hooks."""
    runtime_root = tmp_path / "release-runtime"
    for directory_name in ("python", "usdpy", "lib", "lib/operations", "extraLibs"):
        (runtime_root / directory_name).mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(sys, "path", sys.path.copy())
    monkeypatch.setattr(usd_env, "_add_dll_directory_once", lambda _path: None)
    monkeypatch.setattr(usd_env, "_prepend_env_path", lambda _name, _path: None)

    assert usd_env.configure_environment(runtime_root) == runtime_root


def test_check_environment_reports_native_registry_failures(monkeypatch, tmp_path: Path) -> None:
    runtime_root = tmp_path / "release-runtime"
    for directory_name in ("python", "usdpy", "lib", "lib/operations", "extraLibs"):
        (runtime_root / directory_name).mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(usd_env, "find_runtime_root", lambda: runtime_root)
    monkeypatch.setattr(usd_env, "configure_environment", lambda _root: runtime_root)
    monkeypatch.setattr(usd_env, "_can_import", lambda _module_name: True)
    monkeypatch.setattr(usd_env, "_get_operation_count", lambda: (0, "registry failed"))

    status = usd_env.check_environment()

    assert status.is_usable is False
    assert status.operation_count == 0
    assert "Could not enumerate usd-optimize operations: registry failed" in status.errors
