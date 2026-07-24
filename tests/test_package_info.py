from __future__ import annotations

import re
from importlib.metadata import PackageNotFoundError
from pathlib import Path

import usd_optimize_app
from usd_optimize_app import package_info


def test_package_version_matches_project_metadata() -> None:
    project_text = Path("pyproject.toml").read_text(encoding="utf-8")
    version_match = re.search(r'^version = "([^"]+)"$', project_text, re.MULTILINE)
    assert version_match is not None

    expected_version = version_match.group(1)
    assert usd_optimize_app.__version__ == expected_version
    assert usd_optimize_app.PACKAGE_VERSION == expected_version
    assert package_info.PACKAGE_VERSION == expected_version


def test_installed_version_reads_uninstalled_source_metadata(monkeypatch) -> None:
    def raise_not_found(_package_name: str) -> str:
        raise PackageNotFoundError

    monkeypatch.setattr(package_info, "version", raise_not_found)

    assert package_info.installed_version() == package_info.PACKAGE_VERSION


def test_source_version_falls_back_when_pyproject_is_absent(monkeypatch, tmp_path: Path) -> None:
    fake_module_path = tmp_path / "src" / "usd_optimize_app" / "package_info.py"
    monkeypatch.setattr(package_info, "__file__", str(fake_module_path))

    assert package_info._source_checkout_version() == "development"
