import json
from pathlib import Path

from usd_optimize_app.report_summary import (
    format_report_summary,
    load_report_summaries,
    load_report_summary,
    summaries_to_json_data,
)


def test_load_report_summary_reads_counts_and_output_size(tmp_path: Path) -> None:
    output_path = tmp_path / "asset.safe_publish.usda"
    output_path.write_text("#usda 1.0\n", encoding="utf-8")
    report_path = tmp_path / "asset.safe_publish.usda.report.json"
    report_path.write_text(
        json.dumps(
            {
                "input_path": str(tmp_path / "asset.usda"),
                "output_path": str(output_path),
                "preset_name": "safe_publish",
                "success": True,
                "duration_seconds": 1.25,
                "operations": ["executionContext", "computeExtents"],
                "report_path": str(report_path),
                "log_path": str(tmp_path / "asset.log"),
                "warnings": ["warning"],
                "errors": [],
            }
        ),
        encoding="utf-8",
    )

    summary = load_report_summary(report_path)

    assert summary.preset_name == "safe_publish"
    assert summary.success is True
    assert summary.duration_seconds == 1.25
    assert summary.operation_count == 2
    assert summary.warning_count == 1
    assert summary.error_count == 0
    assert summary.output_size_bytes == output_path.stat().st_size


def test_load_report_summaries_and_format_text(tmp_path: Path) -> None:
    output_path = tmp_path / "asset.diagnostics.usda"
    output_path.write_text("#usda 1.0\n", encoding="utf-8")
    report_path = tmp_path / "asset.diagnostics.usda.report.json"
    report_path.write_text(
        json.dumps(
            {
                "input_path": str(tmp_path / "asset.usda"),
                "output_path": str(output_path),
                "preset_name": "diagnostics",
                "success": True,
                "duration_seconds": 0.5,
                "operations": ["executionContext", "printStats"],
                "report_path": str(report_path),
                "log_path": None,
                "warnings": [],
                "errors": [],
            }
        ),
        encoding="utf-8",
    )

    collection = load_report_summaries(tmp_path)
    text = format_report_summary(collection)
    json_data = summaries_to_json_data(collection)

    assert collection.total_count == 1
    assert collection.success_count == 1
    assert collection.failure_count == 0
    assert "USD Optimize report summary" in text
    assert "diagnostics" in text
    assert json_data["total_count"] == 1
    assert json_data["reports"][0]["preset_name"] == "diagnostics"
