from pathlib import Path

from usd_optimize_app.models import OptimizeResult
from usd_optimize_app.presets import load_preset
from usd_optimize_app.smoke_tests import SmokeAsset, _run_asset_preset


def test_diagnostic_smoke_step_does_not_write_usd(monkeypatch, tmp_path: Path) -> None:
    asset = SmokeAsset("asset", tmp_path / "asset.usda", ())
    captured_requests = []

    def fake_run_optimization(request):
        captured_requests.append(request)
        return OptimizeResult(
            input_path=request.input_path,
            output_path=request.output_path,
            preset_name=request.preset.name,
            success=True,
            duration_seconds=0.1,
            operations=["printStats"],
            worker_output="diagnostics",
        )

    monkeypatch.setattr("usd_optimize_app.smoke_tests.run_optimization", fake_run_optimization)

    _run_asset_preset(asset, load_preset("diagnostics"), tmp_path / "reports")

    assert captured_requests[0].write_output is False


def test_safe_cleanup_smoke_step_writes_usd(monkeypatch, tmp_path: Path) -> None:
    asset = SmokeAsset("asset", tmp_path / "asset.usda", ())
    captured_requests = []

    def fake_run_optimization(request):
        captured_requests.append(request)
        return OptimizeResult(
            input_path=request.input_path,
            output_path=request.output_path,
            preset_name=request.preset.name,
            success=True,
            duration_seconds=0.1,
            operations=["computeExtents"],
        )

    monkeypatch.setattr("usd_optimize_app.smoke_tests.run_optimization", fake_run_optimization)

    _run_asset_preset(asset, load_preset("safe_publish"), tmp_path / "reports")

    assert captured_requests[0].write_output is True
