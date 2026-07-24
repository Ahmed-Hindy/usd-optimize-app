"""Package metadata helpers."""

import re
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

_VERSION_PATTERN = re.compile(r'^version = "([^"]+)"$', re.MULTILINE)


def installed_version() -> str:
    """Return the installed package or source-checkout version."""
    try:
        return version("usd-optimize-app")
    except PackageNotFoundError:
        return _source_checkout_version()


def _source_checkout_version() -> str:
    pyproject_path = Path(__file__).resolve().parents[2] / "pyproject.toml"
    try:
        pyproject_text = pyproject_path.read_text(encoding="utf-8")
    except OSError:
        return "development"
    version_match = _VERSION_PATTERN.search(pyproject_text)
    return version_match.group(1) if version_match is not None else "development"


PACKAGE_VERSION = installed_version()
