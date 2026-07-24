"""Report writing for optimization jobs."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from usd_optimize_app.models import OptimizeResult


def write_result_report(result: OptimizeResult, report_path: Path) -> None:
    """Write an optimization result as JSON.

    Args:
        result: Optimization result data.
        report_path: Destination report path.
    """
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(_to_json_data(result), indent=2), encoding="utf-8")


def _to_json_data(result: OptimizeResult) -> dict[str, Any]:
    data = asdict(result)
    data.pop("worker_output", None)
    for key in ["input_path", "output_path", "report_path", "log_path"]:
        value = data.get(key)
        if isinstance(value, Path):
            data[key] = str(value)
    return data
