from pathlib import Path

from usd_optimize_app.path_utils import default_log_path, default_output_path, default_report_path


def test_default_output_path_adds_optimized_suffix() -> None:
    assert default_output_path(Path("asset.usd")) == Path("asset.optimized.usd")


def test_default_report_path_adds_report_json_suffix() -> None:
    expected_path = Path("asset.optimized.usd.report.json")
    assert default_report_path(Path("asset.optimized.usd")) == expected_path


def test_default_log_path_adds_log_suffix() -> None:
    assert default_log_path(Path("asset.optimized.usd")) == Path("asset.optimized.usd.log")
