from __future__ import annotations

from pathlib import Path

from usd_optimize_app.backend import InputInspection
from usd_optimize_app.gui import stage_inspection
from usd_optimize_app.gui.stage_inspection import StageInspectionController
from usd_optimize_app.models import OptimizeResult


class _FakeSignal:
    def __init__(self) -> None:
        self._callbacks = []

    def connect(self, callback) -> None:
        self._callbacks.append(callback)

    def emit(self, *args) -> None:
        for callback in tuple(self._callbacks):
            callback(*args)


class _FakeInspectionThread:
    instances = []

    def __init__(self, input_path: Path, request_id: int) -> None:
        self.input_path = input_path
        self.request_id = request_id
        self.inspected = _FakeSignal()
        self.finished = _FakeSignal()
        self.started = False
        self.running = False
        self.wait_timeout = None
        self.instances.append(self)

    def start(self) -> None:
        self.started = True
        self.running = True

    def isRunning(self) -> bool:  # noqa: N802
        return self.running

    def wait(self, timeout_ms: int) -> bool:
        self.wait_timeout = timeout_ms
        self.running = False
        return True

    def deleteLater(self) -> None:  # noqa: N802
        pass


class _FakeDiagnosticsThread(_FakeInspectionThread):
    instances = []

    def __init__(self, input_path: Path, request_id: int) -> None:
        super().__init__(input_path, request_id)
        self.completed = _FakeSignal()
        self.failed = _FakeSignal()
        self.cancelled = False

    def cancel(self) -> None:
        self.cancelled = True


def _install_fake_threads(monkeypatch) -> None:
    _FakeInspectionThread.instances.clear()
    _FakeDiagnosticsThread.instances.clear()
    monkeypatch.setattr(stage_inspection, "InputInspectionThread", _FakeInspectionThread)
    monkeypatch.setattr(stage_inspection, "InputDiagnosticsThread", _FakeDiagnosticsThread)


def _diagnostics_result(input_path: Path) -> OptimizeResult:
    return OptimizeResult(
        input_path=input_path,
        output_path=Path("diagnostics.usda"),
        preset_name="diagnostics",
        success=True,
        duration_seconds=0.1,
        operations=["printStats"],
        worker_output="| Total  1  0  0 |",
    )


def test_controller_starts_scene_and_diagnostics_together(monkeypatch, tmp_path: Path) -> None:
    _install_fake_threads(monkeypatch)
    controller = StageInspectionController()
    input_path = tmp_path / "asset.usda"

    controller.inspect(input_path)

    inspection_thread = _FakeInspectionThread.instances[0]
    diagnostics_thread = _FakeDiagnosticsThread.instances[0]
    assert inspection_thread.started is True
    assert diagnostics_thread.started is True
    assert inspection_thread.request_id == diagnostics_thread.request_id
    assert controller.diagnostics_pending is True


def test_controller_ignores_results_from_replaced_input(monkeypatch, tmp_path: Path) -> None:
    _install_fake_threads(monkeypatch)
    controller = StageInspectionController()
    completed_scenes = []
    controller.scene_completed.connect(completed_scenes.append)

    controller.inspect(tmp_path / "first.usda")
    stale_thread = _FakeInspectionThread.instances[-1]
    stale_diagnostics = _FakeDiagnosticsThread.instances[-1]
    controller.inspect(tmp_path / "second.usda")
    current_thread = _FakeInspectionThread.instances[-1]

    stale_thread.inspected.emit(stale_thread.request_id, InputInspection(True, "stale"))
    current_result = InputInspection(True, "current")
    current_thread.inspected.emit(current_thread.request_id, current_result)

    assert stale_diagnostics.cancelled is True
    assert completed_scenes == [current_result]
    assert controller.scene_result is current_result


def test_controller_blocks_workflows_until_diagnostics_finish(monkeypatch, tmp_path: Path) -> None:
    _install_fake_threads(monkeypatch)
    controller = StageInspectionController()
    input_path = tmp_path / "asset.usda"
    controller.inspect(input_path)
    inspection_thread = _FakeInspectionThread.instances[-1]
    inspection_thread.inspected.emit(
        inspection_thread.request_id, InputInspection(True, "Scene loaded · 1 prim", 1)
    )

    assert controller.blocking_reason() == "Inspecting stage diagnostics."

    diagnostics_thread = _FakeDiagnosticsThread.instances[-1]
    diagnostics_thread.completed.emit(
        diagnostics_thread.request_id, _diagnostics_result(input_path)
    )

    assert controller.blocking_reason() is None


def test_controller_tracks_diagnostics_completion(monkeypatch, tmp_path: Path) -> None:
    _install_fake_threads(monkeypatch)
    controller = StageInspectionController()
    completed_results = []
    controller.diagnostics_completed.connect(completed_results.append)
    input_path = tmp_path / "asset.usda"
    controller.inspect(input_path)
    diagnostics_thread = _FakeDiagnosticsThread.instances[-1]
    result = _diagnostics_result(input_path)

    diagnostics_thread.completed.emit(diagnostics_thread.request_id, result)

    assert completed_results == [result]
    assert controller.diagnostics_pending is False
    assert controller.diagnostics_error is None


def test_controller_shutdown_cancels_and_joins_threads(monkeypatch, tmp_path: Path) -> None:
    _install_fake_threads(monkeypatch)
    controller = StageInspectionController()
    controller.inspect(tmp_path / "asset.usda")
    inspection_thread = _FakeInspectionThread.instances[-1]
    diagnostics_thread = _FakeDiagnosticsThread.instances[-1]

    assert controller.shutdown(5_000) is True

    assert diagnostics_thread.cancelled is True
    assert diagnostics_thread.wait_timeout == 5_000
    assert inspection_thread.wait_timeout == 5_000
