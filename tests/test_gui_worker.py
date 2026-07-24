from pathlib import Path

from usd_optimize_app.backend import OptimizeJobSettings
from usd_optimize_app.gui import job_worker
from usd_optimize_app.gui.job_worker import (
    InputDiagnosticsThread,
    OptimizeJobThread,
    _read_log_tail,
)
from usd_optimize_app.models import OptimizeResult


def test_input_diagnostics_thread_runs_read_only_preset(monkeypatch, tmp_path: Path) -> None:
    input_path = tmp_path / "asset.usda"
    captured_settings = []

    def fake_run(settings):
        captured_settings.append(settings)
        return OptimizeResult(
            input_path=input_path,
            output_path=settings.output_path,
            preset_name="diagnostics",
            success=True,
            duration_seconds=0.1,
            operations=["printStats"],
            worker_output="| Total  1  0  0 |",
        )

    monkeypatch.setattr(job_worker, "run_optimize_job", fake_run)
    completed = []
    thread = InputDiagnosticsThread(input_path, request_id=7)
    thread.completed.connect(lambda request_id, result: completed.append((request_id, result)))

    thread.run()

    assert len(captured_settings) == 1
    settings = captured_settings[0]
    assert settings.preset_name == "diagnostics"
    assert settings.write_output is False
    assert settings.output_path.name == "diagnostics.usda"
    assert completed[0][0] == 7
    assert completed[0][1].worker_output == "| Total  1  0  0 |"


def test_optimize_thread_executes_a_prebuilt_normalized_request(
    monkeypatch,
    tmp_path: Path,
) -> None:
    input_path = tmp_path / "input.usda"
    output_path = tmp_path / "output.usda"
    input_path.write_text("#usda 1.0\n", encoding="utf-8")
    captured_requests = []

    def fake_run(request):
        captured_requests.append(request)
        return OptimizeResult(
            input_path=input_path,
            output_path=output_path,
            preset_name="safe_publish",
            success=True,
            duration_seconds=0.1,
            operations=["computeExtents"],
            prim_paths=request.prim_paths,
        )

    monkeypatch.setattr(job_worker, "run_optimization", fake_run)
    thread = OptimizeJobThread(
        OptimizeJobSettings(
            input_path=input_path,
            output_path=output_path,
            preset_name="safe_publish",
            prim_paths=("/World/Asset/Mesh", "/World/Asset"),
        )
    )
    output_messages = []
    thread.output_received.connect(output_messages.append)

    thread.run()

    assert captured_requests[0].prim_paths == ("/World/Asset",)
    assert "Scope: 1 selected prim root(s) and descendants.\n" in output_messages


def test_read_log_tail_limits_gui_log_output(tmp_path: Path) -> None:
    log_path = tmp_path / "worker.log"
    log_path.write_text("\n".join(f"line {index}" for index in range(10)), encoding="utf-8")

    log_tail = _read_log_tail(log_path, max_lines=3)

    assert log_tail == "line 7\nline 8\nline 9"


def test_read_log_tail_returns_empty_string_for_missing_file(tmp_path: Path) -> None:
    assert _read_log_tail(tmp_path / "missing.log") == ""


def test_read_log_tail_returns_empty_string_for_a_directory(tmp_path: Path) -> None:
    assert _read_log_tail(tmp_path) == ""


def test_read_log_tail_spans_multiple_blocks(monkeypatch, tmp_path: Path) -> None:
    log_path = tmp_path / "worker.log"
    log_path.write_text("\n".join(f"line {index}" for index in range(100)), encoding="utf-8")
    monkeypatch.setattr(job_worker, "_LOG_TAIL_BLOCK_BYTES", 16)

    assert _read_log_tail(log_path, max_lines=2) == "line 98\nline 99"
