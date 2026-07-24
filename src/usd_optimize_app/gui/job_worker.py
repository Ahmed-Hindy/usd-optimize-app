"""Qt worker for running shared-backend optimization jobs."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Event, Lock

from PySide6.QtCore import QThread, Signal

from usd_optimize_app.backend import (
    InputInspection,
    OptimizeJobSettings,
    build_optimize_request,
    inspect_input_path,
    run_optimize_job,
)
from usd_optimize_app.models import OptimizeResult
from usd_optimize_app.usd_runner import run_optimization

MAX_LOG_TAIL_LINES = 80
_LOG_TAIL_BLOCK_BYTES = 8 * 1024
_INSPECTION_LOCK = Lock()


class OptimizeJobThread(QThread):
    """Run one optimization job without blocking the GUI thread."""

    output_received = Signal(str)
    succeeded = Signal(object)
    failed = Signal(str)

    def __init__(self, settings: OptimizeJobSettings) -> None:
        super().__init__()
        self._cancel_event = Event()
        self._settings = replace(settings, cancel_event=self._cancel_event)

    def cancel(self) -> None:
        """Request cancellation of the worker subprocess at its next poll."""
        self._cancel_event.set()

    def run(self) -> None:
        """Run the optimization job and emit the result."""
        try:
            self.output_received.emit("Starting optimization...\n")
            request = build_optimize_request(self._settings)
            if request.prim_paths:
                selected_count = len(request.prim_paths)
                self.output_received.emit(
                    f"Scope: {selected_count} selected prim root(s) and descendants.\n"
                )
            else:
                self.output_received.emit("Scope: entire stage.\n")
            result = run_optimization(request)
        except Exception as error:
            self.failed.emit(str(error))
            return

        self._emit_result_summary(result)
        self.succeeded.emit(result)

    def _emit_result_summary(self, result: OptimizeResult) -> None:
        if result.worker_output:
            self.output_received.emit(
                "Diagnostics completed in the side panel. No USD output was written.\n"
            )
        else:
            self.output_received.emit(f"Optimized: {result.output_path}\n")
        if result.report_path:
            self.output_received.emit(f"Report: {result.report_path}\n")
        if result.log_path:
            self.output_received.emit(f"Log: {result.log_path}\n")
            self._emit_log_tail(result.log_path)
        elif result.worker_output:
            self.output_received.emit("\nWorker results:\n")
            self.output_received.emit(result.worker_output + "\n")
        if result.operation_results:
            self.output_received.emit("\nOperation results:\n")
            self.output_received.emit(json.dumps(result.operation_results, indent=2) + "\n")
        for warning in result.warnings:
            self.output_received.emit(f"Warning: {warning}\n")

    def _emit_log_tail(self, log_path: Path) -> None:
        log_tail = _read_log_tail(log_path)
        if not log_tail:
            return
        self.output_received.emit(f"\nWorker log tail ({MAX_LOG_TAIL_LINES} lines max):\n")
        self.output_received.emit(log_tail + "\n")


class InputDiagnosticsThread(QThread):
    """Run the read-only diagnostics preset for one inspected input."""

    completed = Signal(int, object)
    failed = Signal(int, str)

    def __init__(self, input_path: Path, request_id: int) -> None:
        super().__init__()
        self._input_path = input_path
        self._request_id = request_id
        self._cancel_event = Event()

    def cancel(self) -> None:
        """Request cancellation of the diagnostics subprocess."""
        self._cancel_event.set()

    def run(self) -> None:
        """Run diagnostics without leaving report files beside the source USD."""
        try:
            with TemporaryDirectory(prefix="usdopt_gui_diagnostics_") as temp_dir:
                result = run_optimize_job(
                    OptimizeJobSettings(
                        input_path=self._input_path,
                        output_path=Path(temp_dir) / "diagnostics.usda",
                        preset_name="diagnostics",
                        force=True,
                        write_output=False,
                        cancel_event=self._cancel_event,
                    )
                )
        except Exception as error:
            self.failed.emit(self._request_id, str(error))
            return
        self.completed.emit(self._request_id, result)


class InputInspectionThread(QThread):
    """Inspect one input USD path without blocking the Qt event loop."""

    inspected = Signal(int, object)

    def __init__(self, input_path: Path, request_id: int) -> None:
        super().__init__()
        self._input_path = input_path
        self._request_id = request_id

    def run(self) -> None:
        """Inspect the stage and retain the requested path for stale-result checks."""
        # USD's Python bindings are not safe to import concurrently in this process.
        with _INSPECTION_LOCK:
            inspection: InputInspection = inspect_input_path(self._input_path)
        self.inspected.emit(self._request_id, inspection)


def _read_log_tail(log_path: Path, max_lines: int = MAX_LOG_TAIL_LINES) -> str:
    """Return the final lines of a log without loading the complete file."""
    if max_lines <= 0:
        return ""
    try:
        with log_path.open("rb") as log_file:
            log_file.seek(0, 2)
            position = log_file.tell()
            chunks: list[bytes] = []
            newline_count = 0
            while position > 0 and newline_count <= max_lines:
                read_size = min(_LOG_TAIL_BLOCK_BYTES, position)
                position -= read_size
                log_file.seek(position)
                chunk = log_file.read(read_size)
                chunks.append(chunk)
                newline_count += chunk.count(b"\n")
    except OSError:
        return ""

    tail_text = b"".join(reversed(chunks)).decode("utf-8", errors="replace")
    return "\n".join(tail_text.splitlines()[-max_lines:]).strip()
