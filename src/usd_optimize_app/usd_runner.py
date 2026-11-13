"""Optimization runner that calls NVIDIA usd-optimize."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from threading import Event, Lock, Thread
from typing import Any, TextIO

from usd_optimize_app.errors import OptimizeError
from usd_optimize_app.models import OptimizeRequest, OptimizeResult
from usd_optimize_app.operation_scope import build_operation_scope_plan
from usd_optimize_app.path_utils import default_log_path, default_report_path
from usd_optimize_app.reports import write_result_report
from usd_optimize_app.usd_env import check_environment, configure_environment, get_runtime_paths

_WORKER_POLL_INTERVAL_SECONDS = 0.1
_WORKER_TERMINATE_TIMEOUT_SECONDS = 5.0


@dataclass(frozen=True)
class WorkerExecution:
    """Log text and structured operation output from one isolated worker."""

    worker_output: str
    operation_results: list[dict[str, Any]]


@dataclass(frozen=True)
class WorkerJob:
    """Complete input required to launch one isolated optimizer worker."""

    runtime_root: Path
    input_path: Path
    output_path: Path
    operations: list[dict[str, object]]
    log_path: Path
    write_output: bool
    cancel_event: Event | None = None
    on_output: Callable[[str], None] | None = None


def run_optimization(request: OptimizeRequest) -> OptimizeResult:
    """Run one usd-optimize job.

    Args:
        request: Optimization request.

    Returns:
        Result object describing the job outcome.

    Raises:
        OptimizeError: If the job cannot run or fails.
    """
    input_path = request.input_path.expanduser().resolve()
    output_path = request.output_path.expanduser().resolve()
    report_path = request.report_path or default_report_path(output_path)
    log_path = request.log_path or default_log_path(output_path)

    if not input_path.exists():
        raise OptimizeError(f"Input USD does not exist: {input_path}")
    if request.write_output and input_path == output_path and not request.force:
        message = (
            "Input and output paths are identical. Use --force only for intentional overwrite."
        )
        raise OptimizeError(message)
    if request.write_output and output_path.exists() and not request.force:
        raise OptimizeError(f"Output already exists: {output_path}. Use --force to replace it.")

    scope_plan = build_operation_scope_plan(request.preset.operations, request.prim_paths)
    operation_list = list(scope_plan.operation_names)
    start_time = time.perf_counter()

    if request.dry_run:
        duration_seconds = time.perf_counter() - start_time
        result = OptimizeResult(
            input_path=input_path,
            output_path=output_path,
            preset_name=request.preset.name,
            success=True,
            duration_seconds=duration_seconds,
            operations=operation_list,
            prim_paths=scope_plan.prim_paths,
            report_path=report_path,
            log_path=None,
            warnings=[*scope_plan.warnings, "Dry run only. No USD file was written."],
        )
        write_result_report(result, report_path)
        return result

    status = check_environment()
    if not status.is_usable:
        problem_text = "; ".join(status.errors) if status.errors else "unknown problem"
        raise OptimizeError(f"usd-optimize environment is not usable: {problem_text}")
    if status.runtime_root is None:
        raise OptimizeError("usd-optimize runtime artifact is unavailable.")

    configure_environment(status.runtime_root)
    if request.write_output:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.parent.mkdir(parents=True, exist_ok=True)

    worker_execution = _run_worker_process(
        WorkerJob(
            runtime_root=status.runtime_root,
            input_path=input_path,
            output_path=output_path,
            operations=scope_plan.operations,
            log_path=log_path,
            write_output=request.write_output,
            cancel_event=request.cancel_event,
            on_output=request.on_output,
        )
    )

    duration_seconds = time.perf_counter() - start_time
    result = OptimizeResult(
        input_path=input_path,
        output_path=output_path,
        preset_name=request.preset.name,
        success=True,
        duration_seconds=duration_seconds,
        operations=operation_list,
        prim_paths=scope_plan.prim_paths,
        report_path=report_path,
        log_path=log_path if request.write_output else None,
        worker_output=worker_execution.worker_output if not request.write_output else "",
        operation_results=worker_execution.operation_results,
        warnings=list(scope_plan.warnings),
    )
    write_result_report(result, report_path)
    return result


def _run_worker_process(job: WorkerJob) -> WorkerExecution:
    """Run one isolated usd-optimize worker subprocess.

    Args:
        job: Complete worker input and output specification.

    Raises:
        OptimizeError: If the worker fails.
    """
    with tempfile.TemporaryDirectory(prefix="usdopt_job_") as temp_dir:
        job_path = Path(temp_dir) / "job.json"
        result_path = Path(temp_dir) / "result.json"
        job_data = {
            "runtime_root": str(job.runtime_root),
            "input_path": str(job.input_path),
            "output_path": str(job.output_path),
            "operations": job.operations,
            "write_output": job.write_output,
            "result_path": str(result_path),
        }
        job_path.write_text(json.dumps(job_data, indent=2), encoding="utf-8")
        environment = _build_worker_environment(job.runtime_root)
        command = [
            sys.executable,
            "-u",
            "-m",
            "usd_optimize_app.runtime_worker",
            "--job",
            str(job_path),
        ]
        process = subprocess.Popen(
            command,
            env=environment,
            text=True,
            bufsize=1,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        stdout, stderr = _communicate_worker(process, job.cancel_event, job.on_output)
        operation_results = _read_operation_results(result_path) if process.returncode == 0 else []

    log_text = ""
    if stdout:
        log_text += stdout
    if stderr:
        log_text += "\n[stderr]\n" + stderr
    if job.write_output:
        job.log_path.write_text(log_text, encoding="utf-8")

    if process.returncode != 0:
        tail = "\n".join(log_text.splitlines()[-20:])
        message = f"usd-optimize worker exit code {process.returncode}.\n{tail}"
        raise OptimizeError(message)
    return WorkerExecution(log_text, operation_results)


def _stream_worker_output(
    process: subprocess.Popen[str],
    cancel_event: Event | None,
    on_output: Callable[[str], None],
) -> tuple[str, str]:
    """Drain worker pipes line-by-line while forwarding output and checking cancellation."""
    stdout_chunks: list[str] = []
    stderr_chunks: list[str] = []
    emit_lock = Lock()

    def drain_stream(stream: TextIO, chunks: list[str], prefix: str = "") -> None:
        try:
            for line in stream:
                chunks.append(line)
                with emit_lock:
                    on_output(f"{prefix}{line}" if prefix else line)
        finally:
            stream.close()

    stdout_thread = Thread(target=drain_stream, args=(process.stdout, stdout_chunks), daemon=True)
    stderr_thread = Thread(
        target=drain_stream, args=(process.stderr, stderr_chunks, "[stderr] "), daemon=True
    )
    stdout_thread.start()
    stderr_thread.start()

    try:
        while True:
            try:
                process.wait(timeout=_WORKER_POLL_INTERVAL_SECONDS)
                break
            except subprocess.TimeoutExpired:
                if cancel_event is None or not cancel_event.is_set():
                    continue
                process.terminate()
                try:
                    process.wait(timeout=_WORKER_TERMINATE_TIMEOUT_SECONDS)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
                raise OptimizeError("Optimization cancelled.") from None
    finally:
        stdout_thread.join(timeout=1.0)
        stderr_thread.join(timeout=1.0)

    return "".join(stdout_chunks), "".join(stderr_chunks)


def _communicate_worker(
    process: subprocess.Popen[str],
    cancel_event: Event | None,
    on_output: Callable[[str], None] | None = None,
) -> tuple[str, str]:
    """Drain worker output while periodically checking for cancellation."""
    if on_output is not None:
        return _stream_worker_output(process, cancel_event, on_output)
    while True:
        try:
            return process.communicate(timeout=_WORKER_POLL_INTERVAL_SECONDS)
        except subprocess.TimeoutExpired:
            if cancel_event is None or not cancel_event.is_set():
                continue
            _terminate_worker(process)
            raise OptimizeError("Optimization cancelled.") from None


def _terminate_worker(process: subprocess.Popen[str]) -> None:
    """Terminate a worker and escalate to a kill if it does not exit promptly."""
    process.terminate()
    try:
        process.communicate(timeout=_WORKER_TERMINATE_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        process.kill()
        process.communicate()


def _read_operation_results(result_path: Path) -> list[dict[str, Any]]:
    """Load structured operation output written by a successful worker."""
    if not result_path.is_file():
        raise OptimizeError("usd-optimize worker did not return operation results.")
    try:
        payload = json.loads(result_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise OptimizeError("Could not read usd-optimize worker operation results.") from error
    operation_results = payload.get("operation_results")
    if not isinstance(operation_results, list) or not all(
        isinstance(result, dict) for result in operation_results
    ):
        raise OptimizeError("usd-optimize worker returned invalid operation results.")
    return operation_results


def _build_worker_environment(runtime_root: Path) -> dict[str, str]:
    environment = os.environ.copy()
    runtime_paths = get_runtime_paths(runtime_root)
    python_paths = [
        str(runtime_paths.python_dir),
        str(runtime_paths.usdpy_dir),
        environment.get("PYTHONPATH", ""),
    ]
    dll_paths = [
        str(runtime_paths.lib_dir),
        str(runtime_paths.operations_dir),
        str(runtime_paths.extra_libs_dir),
        environment.get("PATH", ""),
    ]
    environment["PYTHONPATH"] = os.pathsep.join(path for path in python_paths if path)
    environment["PATH"] = os.pathsep.join(path for path in dll_paths if path)
    return environment
