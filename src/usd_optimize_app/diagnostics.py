"""Parse concise diagnostics from usd-optimize worker output."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class StageStat:
    """One stage-statistics row reported by the printStats operation."""

    prim_type: str
    count: str
    inactive: str
    invisible: str

    @property
    def numeric_count(self) -> int | None:
        """Return the leading count when the worker adds descriptive annotations."""
        match = re.match(r"\d+", self.count)
        return int(match.group()) if match else None


@dataclass(frozen=True)
class StageMetrics:
    """Top-level geometric metrics emitted by printStats."""

    faces: int | None = None
    vertices: int | None = None
    renderable_geometries: int | None = None


def parse_stage_stats(worker_output: str) -> list[StageStat]:
    """Parse the stable table emitted by usd-optimize's printStats operation."""
    stats: list[StageStat] = []
    for line in worker_output.splitlines():
        if not line.startswith("|"):
            continue
        body = line.strip().strip("|").strip()
        match = re.match(r"^(\S+)\s+(.+?)\s+(\d+|--)\s+(\d+|--)$", body)
        if match is None or match.group(1) in {"Prim", ""}:
            continue
        stats.append(StageStat(*match.groups()))
    return stats


def parse_stage_metrics(worker_output: str) -> StageMetrics:
    """Parse concise geometric metrics from the printStats banner."""
    values: dict[str, int] = {}
    for key, label in {
        "faces": "Faces",
        "vertices": "Vertices",
        "renderable_geometries": "Renderable Geometries",
    }.items():
        match = re.search(rf"\|\s*{label}:\s*([\d,]+)", worker_output)
        if match:
            values[key] = int(match.group(1).replace(",", ""))
    return StageMetrics(**values)
