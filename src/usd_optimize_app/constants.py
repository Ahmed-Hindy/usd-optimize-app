"""Application constants and portable-install path discovery."""

from __future__ import annotations

import os
import sys
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = PACKAGE_ROOT.parents[1]
USD_OPTIMIZE_RUNTIME_ROOT_ENV = "USD_OPTIMIZE_RUNTIME_ROOT"
USD_OPTIMIZE_PACKAGE_ROOT_ENV = "USD_OPTIMIZE_PACKAGE_ROOT"
USD_OPTIMIZE_APP_PRESETS_DIR_ENV = "USD_OPTIMIZE_APP_PRESETS_DIR"

PORTABLE_APP_ROOT = Path(sys.executable).resolve().parent.parent
PORTABLE_USD_OPTIMIZE_RUNTIME_ROOT = PORTABLE_APP_ROOT / "runtime" / "usd-optimize"
DEVELOPMENT_USD_OPTIMIZE_RUNTIME_ROOT = (
    PROJECT_ROOT.parent
    / "usd-optimize"
    / ".artifacts"
    / "usd-optimize-v1.2.1-windows-25.11-py3.12"
    / "release-runtime"
)
DEFAULT_USD_OPTIMIZE_RUNTIME_ROOT = DEVELOPMENT_USD_OPTIMIZE_RUNTIME_ROOT

SUPPORTED_USD_EXTENSIONS = {".usd", ".usda", ".usdc"}
DEFAULT_OUTPUT_SUFFIX = ".optimized"


def runtime_root_candidates() -> tuple[Path, ...]:
    """Return explicit, portable, and development runtime candidates in priority order."""
    candidates: list[Path] = []
    for variable_name in (USD_OPTIMIZE_RUNTIME_ROOT_ENV, USD_OPTIMIZE_PACKAGE_ROOT_ENV):
        configured_root = os.environ.get(variable_name)
        if configured_root:
            candidates.append(Path(configured_root))
    candidates.extend([PORTABLE_USD_OPTIMIZE_RUNTIME_ROOT, DEVELOPMENT_USD_OPTIMIZE_RUNTIME_ROOT])
    return tuple(dict.fromkeys(candidates))


def _find_builtin_presets_dir() -> Path:
    configured_dir = os.environ.get(USD_OPTIMIZE_APP_PRESETS_DIR_ENV)
    candidates = [Path(configured_dir)] if configured_dir else []
    candidates.extend([PORTABLE_APP_ROOT / "presets", PROJECT_ROOT / "presets"])
    for candidate in candidates:
        resolved_candidate = candidate.expanduser().resolve()
        if resolved_candidate.is_dir():
            return resolved_candidate
    return PROJECT_ROOT / "presets"


BUILTIN_PRESETS_DIR = _find_builtin_presets_dir()
