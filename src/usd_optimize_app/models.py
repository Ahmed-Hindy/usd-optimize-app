"""Data models shared by the CLI, GUI, and optimizer backend."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from threading import Event
from typing import Any, Literal

PresetRisk = Literal["safe", "review", "diagnostic", "destructive"]
PresetAudience = Literal["user", "developer"]


@dataclass(frozen=True)
class PresetDefinition:
    """A named optimization preset loaded from JSON."""

    name: str
    display_name: str
    risk: PresetRisk
    audience: PresetAudience
    description: str
    operations: list[dict[str, Any]]
    path: Path


@dataclass(frozen=True)
class OptimizeRequest:
    """User request for a single optimization job."""

    input_path: Path
    output_path: Path
    preset: PresetDefinition
    force: bool = False
    dry_run: bool = False
    write_output: bool = True
    report_path: Path | None = None
    log_path: Path | None = None
    cancel_event: Event | None = None
    prim_paths: tuple[str, ...] = ()


@dataclass
class OptimizeResult:
    """Result data written after an optimization job finishes."""

    input_path: Path
    output_path: Path
    preset_name: str
    success: bool
    duration_seconds: float
    operations: list[str]
    report_path: Path | None = None
    log_path: Path | None = None
    worker_output: str = ""
    operation_results: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    prim_paths: tuple[str, ...] = ()


@dataclass(frozen=True)
class EnvironmentStatus:
    """Detected usd-optimize runtime environment state."""

    runtime_root: Path | None
    required_python: str | None
    current_python: str
    has_python_dir: bool
    has_usdpy_dir: bool
    has_lib_dir: bool
    has_extra_libs_dir: bool
    pxr_import_ok: bool
    usd_optimize_import_ok: bool
    operation_count: int | None = None
    errors: tuple[str, ...] = ()

    @property
    def is_usable(self) -> bool:
        """Whether the current environment appears usable."""
        return not self.errors and self.pxr_import_ok and self.usd_optimize_import_ok
