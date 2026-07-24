"""Coordinate scene hierarchy and automatic diagnostics inspection."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, Signal

from usd_optimize_app.backend import InputInspection
from usd_optimize_app.gui.job_worker import InputDiagnosticsThread, InputInspectionThread
from usd_optimize_app.models import OptimizeResult


class StageInspectionController(QObject):
    """Own the background work associated with one committed input stage."""

    scene_completed = Signal(object)
    diagnostics_completed = Signal(object)
    diagnostics_failed = Signal(str)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._request_id = 0
        self._scene_result: InputInspection | None = None
        self._diagnostics_pending = False
        self._diagnostics_error: str | None = None
        self._inspection_threads: list[InputInspectionThread] = []
        self._diagnostics_threads: list[InputDiagnosticsThread] = []

    @property
    def scene_result(self) -> InputInspection | None:
        return self._scene_result

    @property
    def diagnostics_pending(self) -> bool:
        return self._diagnostics_pending

    @property
    def diagnostics_error(self) -> str | None:
        return self._diagnostics_error

    @property
    def has_error(self) -> bool:
        return self._diagnostics_error is not None or (
            self._scene_result is not None and not self._scene_result.is_valid
        )

    def blocking_reason(self) -> str | None:
        """Return why a workflow cannot run while inspection is incomplete."""
        if self._scene_result is None:
            return "Inspecting the selected USD scene."
        if not self._scene_result.is_valid:
            return self._scene_result.message
        if self._diagnostics_pending:
            return "Inspecting stage diagnostics."
        if self._diagnostics_error:
            return f"Stage diagnostics failed: {self._diagnostics_error}"
        return None

    def inspect(self, input_path: Path) -> None:
        """Start hierarchy inspection and diagnostics for one input path."""
        self.reset()
        request_id = self._request_id
        self._diagnostics_pending = True

        inspection_thread = InputInspectionThread(input_path, request_id)
        inspection_thread.inspected.connect(self._on_scene_completed)
        inspection_thread.finished.connect(
            lambda: self._remove_inspection_thread(inspection_thread)
        )
        inspection_thread.finished.connect(inspection_thread.deleteLater)
        self._inspection_threads.append(inspection_thread)

        diagnostics_thread = InputDiagnosticsThread(input_path, request_id)
        diagnostics_thread.completed.connect(self._on_diagnostics_completed)
        diagnostics_thread.failed.connect(self._on_diagnostics_failed)
        diagnostics_thread.finished.connect(
            lambda: self._remove_diagnostics_thread(diagnostics_thread)
        )
        diagnostics_thread.finished.connect(diagnostics_thread.deleteLater)
        self._diagnostics_threads.append(diagnostics_thread)

        inspection_thread.start()
        diagnostics_thread.start()

    def reset(self) -> None:
        """Invalidate current results and cancel obsolete diagnostics work."""
        self._request_id += 1
        self._scene_result = None
        self._diagnostics_pending = False
        self._diagnostics_error = None
        for thread in tuple(self._diagnostics_threads):
            if thread.isRunning():
                thread.cancel()

    def shutdown(self, timeout_ms: int) -> bool:
        """Cancel and join all inspection work before application shutdown."""
        for thread in tuple(self._diagnostics_threads):
            if thread.isRunning():
                thread.cancel()
                if not thread.wait(timeout_ms):
                    return False
        for thread in tuple(self._inspection_threads):
            if thread.isRunning() and not thread.wait(timeout_ms):
                return False
        return True

    def _on_scene_completed(self, request_id: int, result: InputInspection) -> None:
        if request_id != self._request_id:
            return
        self._scene_result = result
        self.scene_completed.emit(result)

    def _on_diagnostics_completed(self, request_id: int, result: OptimizeResult) -> None:
        if request_id != self._request_id:
            return
        self._diagnostics_pending = False
        self._diagnostics_error = None
        self.diagnostics_completed.emit(result)

    def _on_diagnostics_failed(self, request_id: int, message: str) -> None:
        if request_id != self._request_id:
            return
        self._diagnostics_pending = False
        self._diagnostics_error = message
        self.diagnostics_failed.emit(message)

    def _remove_inspection_thread(self, thread: InputInspectionThread) -> None:
        if thread in self._inspection_threads:
            self._inspection_threads.remove(thread)

    def _remove_diagnostics_thread(self, thread: InputDiagnosticsThread) -> None:
        if thread in self._diagnostics_threads:
            self._diagnostics_threads.remove(thread)
