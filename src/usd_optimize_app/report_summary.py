"""Summary helpers for optimization report JSON files."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from usd_optimize_app.formatting import format_file_size


@dataclass(frozen=True)
class ReportSummary:
    """Compact summary of one optimization report."""

    report_path: Path
    input_path: Path
    output_path: Path
    preset_name: str
    success: bool
    duration_seconds: float
    operation_count: int
    warning_count: int
    error_count: int
    output_size_bytes: int | None
    log_path: Path | None


@dataclass(frozen=True)
class ReportSummaryCollection:
    """Collection of report summaries and aggregate counters."""

    reports_dir: Path
    reports: list[ReportSummary]

    @property
    def total_count(self) -> int:
        """Return the number of report summaries."""
        return len(self.reports)

    @property
    def success_count(self) -> int:
        """Return the number of successful reports."""
        return sum(1 for report in self.reports if report.success)

    @property
    def failure_count(self) -> int:
        """Return the number of failed reports."""
        return self.total_count - self.success_count

    @property
    def total_duration_seconds(self) -> float:
        """Return the summed duration across all reports."""
        return sum(report.duration_seconds for report in self.reports)


def load_report_summary(report_path: Path) -> ReportSummary:
    """Load one optimization report JSON file.

    Args:
        report_path: Report JSON path.

    Returns:
        Parsed report summary.
    """
    resolved_report_path = report_path.expanduser().resolve()
    report_data = json.loads(resolved_report_path.read_text(encoding="utf-8"))
    output_path = Path(report_data["output_path"])
    log_path_value = report_data.get("log_path")
    log_path = Path(log_path_value) if log_path_value else None
    return ReportSummary(
        report_path=resolved_report_path,
        input_path=Path(report_data["input_path"]),
        output_path=output_path,
        preset_name=str(report_data["preset_name"]),
        success=bool(report_data["success"]),
        duration_seconds=float(report_data["duration_seconds"]),
        operation_count=len(report_data.get("operations", [])),
        warning_count=len(report_data.get("warnings", [])),
        error_count=len(report_data.get("errors", [])),
        output_size_bytes=_file_size(output_path),
        log_path=log_path,
    )


def load_report_summaries(reports_dir: Path) -> ReportSummaryCollection:
    """Load all optimization reports under a directory.

    Args:
        reports_dir: Directory to scan recursively for `.report.json` files.

    Returns:
        Report summary collection sorted by output path.
    """
    resolved_reports_dir = reports_dir.expanduser().resolve()
    report_paths = sorted(resolved_reports_dir.rglob("*.report.json"))
    reports = [load_report_summary(report_path) for report_path in report_paths]
    reports.sort(key=lambda report: (str(report.output_path), report.preset_name))
    return ReportSummaryCollection(reports_dir=resolved_reports_dir, reports=reports)


def format_report_summary(collection: ReportSummaryCollection) -> str:
    """Format report summaries as a plain-text table.

    Args:
        collection: Report summary collection.

    Returns:
        Human-readable summary text.
    """
    lines = [
        "USD Optimize report summary",
        f"  Reports dir: {collection.reports_dir}",
        f"  Reports: {collection.total_count}",
        f"  Succeeded: {collection.success_count}",
        f"  Failed: {collection.failure_count}",
        f"  Total duration: {collection.total_duration_seconds:.2f}s",
    ]
    if not collection.reports:
        lines.append("\nNo report files found.")
        return "\n".join(lines)

    lines.extend(["", _table_header(), _table_rule()])
    lines.extend(
        _format_report_row(report, collection.reports_dir) for report in collection.reports
    )
    return "\n".join(lines)


def summaries_to_json_data(collection: ReportSummaryCollection) -> dict[str, Any]:
    """Return a JSON-serializable version of a report summary collection."""
    return {
        "reports_dir": str(collection.reports_dir),
        "total_count": collection.total_count,
        "success_count": collection.success_count,
        "failure_count": collection.failure_count,
        "total_duration_seconds": collection.total_duration_seconds,
        "reports": [
            {
                "report_path": str(report.report_path),
                "input_path": str(report.input_path),
                "output_path": str(report.output_path),
                "preset_name": report.preset_name,
                "success": report.success,
                "duration_seconds": report.duration_seconds,
                "operation_count": report.operation_count,
                "warning_count": report.warning_count,
                "error_count": report.error_count,
                "output_size_bytes": report.output_size_bytes,
                "log_path": str(report.log_path) if report.log_path else None,
            }
            for report in collection.reports
        ],
    }


def _table_header() -> str:
    return (
        f"{'status':8} {'preset':18} {'duration':>9} {'size':>10} "
        f"{'ops':>4} {'warn':>4} {'err':>3} output"
    )


def _table_rule() -> str:
    return "-" * 100


def _format_report_row(report: ReportSummary, reports_dir: Path) -> str:
    status = "OK" if report.success else "FAILED"
    duration = f"{report.duration_seconds:.2f}s"
    size_text = format_file_size(report.output_size_bytes)
    return (
        f"{status:8} {report.preset_name[:18]:18} {duration:>9} {size_text:>10} "
        f"{report.operation_count:>4} {report.warning_count:>4} {report.error_count:>3} "
        f"{_relative_path_text(report.output_path, reports_dir)}"
    )


def _relative_path_text(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def _file_size(path: Path) -> int | None:
    try:
        return path.stat().st_size
    except OSError:
        return None
