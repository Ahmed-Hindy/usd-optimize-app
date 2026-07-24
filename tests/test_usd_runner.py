import json
import subprocess
from pathlib import Path
from threading import Event

import pytest

from usd_optimize_app import usd_runner
from usd_optimize_app.errors import OptimizeError
from usd_optimize_app.models import EnvironmentStatus, OptimizeRequest
from usd_optimize_app.presets import load_preset
from usd_optimize_app.reports import _to_json_data
from usd_optimize_app.usd_runner import WorkerExecution, WorkerJob, run_optimization


def test_dry_run_writes_only_a_report(tmp_path: Path) -> None:
    input_path = tmp_path / "input.usda"
    output_path = tmp_path / "output.usda"
    input_path.write_text("#usda 1.0\n", encoding="utf-8")

    result = run_optimization(
        OptimizeRequest(
            input_path=input_path,
            output_path=output_path,
            preset=load_preset("safe_publish"),
            dry_run=True,
        )
    )

    assert output_path.exists() is False
    assert result.log_path is None
    assert result.report_path is not None
    report_data = json.loads(result.report_path.read_text(encoding="utf-8"))
    assert report_data["log_path"] is None


def test_diagnostics_mode_skips_usd_export_report_and_log(monkeypatch, tmp_path: Path) -> None:
    input_path = tmp_path / "input.usda"
    output_path = tmp_path / "diagnostics.usda"
    input_path.write_text("#usda 1.0\n", encoding="utf-8")
    output_path.write_text("existing output", encoding="utf-8")
    status = EnvironmentStatus(
        runtime_root=tmp_path,
        required_python=None,
        current_python="3.12",
        has_python_dir=True,
        has_usdpy_dir=True,
        has_lib_dir=True,
        has_extra_libs_dir=True,
        pxr_import_ok=True,
        usd_optimize_import_ok=True,
    )
    monkeypatch.setattr("usd_optimize_app.usd_runner.check_environment", lambda: status)
    monkeypatch.setattr("usd_optimize_app.usd_runner.configure_environment", lambda _root: tmp_path)

    def fake_worker(job: WorkerJob) -> WorkerExecution:
        assert job.write_output is False
        return WorkerExecution(
            "printStats: 1 root prim\n",
            [{"operation": "findOverlappingMeshes", "output": {"analysis": {}}}],
        )

    monkeypatch.setattr("usd_optimize_app.usd_runner._run_worker_process", fake_worker)

    result = run_optimization(
        OptimizeRequest(
            input_path=input_path,
            output_path=output_path,
            preset=load_preset("diagnostics"),
            write_output=False,
        )
    )

    assert output_path.read_text(encoding="utf-8") == "existing output"
    assert result.report_path == output_path.with_suffix(".usda.report.json")
    assert result.log_path is None
    assert result.worker_output == "printStats: 1 root prim\n"
    assert result.operation_results == [
        {"operation": "findOverlappingMeshes", "output": {"analysis": {}}}
    ]
    report_data = json.loads(result.report_path.read_text(encoding="utf-8"))
    assert report_data["operation_results"] == result.operation_results


def test_normal_result_does_not_keep_worker_output_in_report(monkeypatch, tmp_path: Path) -> None:
    input_path = tmp_path / "input.usda"
    output_path = tmp_path / "output.usda"
    input_path.write_text("#usda 1.0\n", encoding="utf-8")
    status = EnvironmentStatus(
        runtime_root=tmp_path,
        required_python=None,
        current_python="3.12",
        has_python_dir=True,
        has_usdpy_dir=True,
        has_lib_dir=True,
        has_extra_libs_dir=True,
        pxr_import_ok=True,
        usd_optimize_import_ok=True,
    )
    monkeypatch.setattr("usd_optimize_app.usd_runner.check_environment", lambda: status)
    monkeypatch.setattr("usd_optimize_app.usd_runner.configure_environment", lambda _root: tmp_path)
    monkeypatch.setattr(
        "usd_optimize_app.usd_runner._run_worker_process",
        lambda _job: WorkerExecution("verbose worker log", []),
    )

    result = run_optimization(
        OptimizeRequest(
            input_path=input_path, output_path=output_path, preset=load_preset("safe_publish")
        )
    )

    assert result.worker_output == ""
    assert "worker_output" not in _to_json_data(result)


def test_selected_prims_scope_worker_operations_and_report(monkeypatch, tmp_path: Path) -> None:
    input_path = tmp_path / "input.usda"
    output_path = tmp_path / "output.usda"
    input_path.write_text("#usda 1.0\n", encoding="utf-8")
    status = EnvironmentStatus(
        runtime_root=tmp_path,
        required_python=None,
        current_python="3.12",
        has_python_dir=True,
        has_usdpy_dir=True,
        has_lib_dir=True,
        has_extra_libs_dir=True,
        pxr_import_ok=True,
        usd_optimize_import_ok=True,
    )
    monkeypatch.setattr("usd_optimize_app.usd_runner.check_environment", lambda: status)
    monkeypatch.setattr("usd_optimize_app.usd_runner.configure_environment", lambda _root: tmp_path)

    def fake_worker(job: WorkerJob) -> WorkerExecution:
        assert [operation["operation"] for operation in job.operations] == [
            "executionContext",
            "computeExtents",
            "optimizePrimvars",
            "optimizeTimeSamples",
        ]
        assert job.operations[1]["paths"] == ["/World/Asset//"]
        assert job.operations[2]["paths"] == ["/World/Asset//"]
        assert job.operations[3]["paths"] == ["/World/Asset//"]
        return WorkerExecution("", [])

    monkeypatch.setattr("usd_optimize_app.usd_runner._run_worker_process", fake_worker)

    result = run_optimization(
        OptimizeRequest(
            input_path=input_path,
            output_path=output_path,
            preset=load_preset("safe_publish"),
            prim_paths=("/World/Asset/Mesh", "/World/Asset"),
        )
    )

    assert result.prim_paths == ("/World/Asset",)
    assert "optimizeMaterials" not in result.operations
    assert result.warnings == [
        "Skipped optimizeMaterials: Material deduplication can rebind consumers outside the "
        "selected hierarchy."
    ]
    report_data = json.loads(result.report_path.read_text(encoding="utf-8"))
    assert report_data["prim_paths"] == ["/World/Asset"]
    assert report_data["warnings"] == result.warnings


def test_worker_communication_drains_pipes_while_polling() -> None:
    class FakeProcess:
        def __init__(self) -> None:
            self.returncode = None
            self.timeouts: list[float | None] = []

        def communicate(self, timeout=None):
            self.timeouts.append(timeout)
            if len(self.timeouts) == 1:
                raise subprocess.TimeoutExpired("worker", timeout)
            self.returncode = 0
            return "worker output", "worker error"

    process = FakeProcess()

    assert usd_runner._communicate_worker(process, None) == (
        "worker output",
        "worker error",
    )
    assert process.timeouts == [
        usd_runner._WORKER_POLL_INTERVAL_SECONDS,
        usd_runner._WORKER_POLL_INTERVAL_SECONDS,
    ]


def test_worker_cancellation_escalates_to_kill() -> None:
    class StubbornProcess:
        def __init__(self) -> None:
            self.returncode = None
            self.communicate_timeouts: list[float | None] = []
            self.terminated = False
            self.killed = False

        def communicate(self, timeout=None):
            self.communicate_timeouts.append(timeout)
            if len(self.communicate_timeouts) <= 2:
                raise subprocess.TimeoutExpired("worker", timeout)
            self.returncode = -9
            return "partial output", ""

        def terminate(self) -> None:
            self.terminated = True

        def kill(self) -> None:
            self.killed = True

    process = StubbornProcess()
    cancel_event = Event()
    cancel_event.set()

    with pytest.raises(OptimizeError, match="Optimization cancelled"):
        usd_runner._communicate_worker(process, cancel_event)

    assert process.terminated is True
    assert process.killed is True
    assert process.communicate_timeouts == [
        usd_runner._WORKER_POLL_INTERVAL_SECONDS,
        usd_runner._WORKER_TERMINATE_TIMEOUT_SECONDS,
        None,
    ]
