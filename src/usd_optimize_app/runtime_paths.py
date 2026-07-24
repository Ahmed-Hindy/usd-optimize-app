"""Strict runtime path resolution for the downloaded usd-optimize artifact."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RuntimePaths:
    """Resolved runtime folders required to import and run usd-optimize."""

    runtime_root: Path
    python_dir: Path
    usdpy_dir: Path
    lib_dir: Path
    operations_dir: Path
    extra_libs_dir: Path

    @property
    def required_dirs(self) -> list[Path]:
        """Return directories that must exist for the runtime to be usable."""
        return [
            self.python_dir,
            self.usdpy_dir,
            self.lib_dir,
            self.operations_dir,
            self.extra_libs_dir,
        ]


def resolve_runtime_paths(runtime_root: Path) -> RuntimePaths:
    """Resolve runtime paths from the required extracted artifact root.

    Args:
        runtime_root: Extracted usd-optimize artifact root.

    Returns:
        Runtime path layout.
    """
    resolved_runtime_root = runtime_root.expanduser().resolve()
    lib_dir = resolved_runtime_root / "lib"
    return RuntimePaths(
        runtime_root=resolved_runtime_root,
        python_dir=resolved_runtime_root / "python",
        usdpy_dir=resolved_runtime_root / "usdpy",
        lib_dir=lib_dir,
        operations_dir=lib_dir / "operations",
        extra_libs_dir=resolved_runtime_root / "extraLibs",
    )


def looks_like_runtime_root(path: Path) -> bool:
    """Return whether a path looks like an extracted usd-optimize runtime package."""
    return (path / "python").exists() and (path / "usdpy").exists() and (path / "lib").exists()
