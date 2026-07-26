"""Coordinate workflow form intent, inspection, and optimization jobs."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from time import monotonic

from PySide6.QtCore import QObject, QTimer, QUrl, Signal
from PySide6.QtGui import QDesktopServices

from usd_optimize_app.backend import (
    InputInspection,
    OptimizeJobSettings,
    PresetView,
    get_environment_status,
    get_gui_workflows,
    resolve_default_output_path,
)
from usd_optimize_app.constants import SUPPORTED_USD_EXTENSIONS
from usd_optimize_app.diagnostics import parse_stage_metrics, parse_stage_stats
from usd_optimize_app.gui.analysis_view import format_analysis_results
from usd_optimize_app.gui.job_worker import OptimizeJobThread
from usd_optimize_app.gui.log_view import append_log_text
from usd_optimize_app.gui.preferences import GuiPreferences
from usd_optimize_app.gui.report_views import populate_diagnostics_table
from usd_optimize_app.gui.results_panel import OverviewState, ResultsPanel
from usd_optimize_app.gui.scene_graph_view import populate_scene_tree
from usd_optimize_app.gui.stage_inspection import StageInspectionController
from usd_optimize_app.gui.workflow_panel import WorkflowFormState, WorkflowPanel
from usd_optimize_app.models import EnvironmentStatus, OptimizeResult
from usd_optimize_app.operation_scope import scoped_operation_skip_reason
from usd_optimize_app.operations import get_operation_presentation

THREAD_SHUTDOWN_TIMEOUT_MS = 5_000


class WorkflowController(QObject):
    """Own GUI workflow state without owning the application window layout."""

    status_changed = Signal(str, str)
    runtime_changed = Signal(bool, str)

    def __init__(
        self,
        workflow_panel: WorkflowPanel,
        results_panel: ResultsPanel,
        *,
        preferences: GuiPreferences | None = None,
        environment_status_provider: Callable[[], EnvironmentStatus] = get_environment_status,
        confirm_replacement: Callable[[str, str], bool] | None = None,
        show_error: Callable[[str], None] | None = None,
        show_completion: Callable[[OptimizeResult], None] | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._workflow_panel = workflow_panel
        self._results_panel = results_panel
        self._preferences = preferences or GuiPreferences()
        self._environment_status_provider = environment_status_provider
        self._confirm_replacement = confirm_replacement or (lambda _title, _message: False)
        self._show_error = show_error or (lambda _message: None)
        self._show_completion = show_completion or (lambda _result: None)
        self._presets = get_gui_workflows()
        self._inspection_controller = StageInspectionController(self)
        self._inspection_controller.scene_completed.connect(self._on_input_inspected)
        self._inspection_controller.diagnostics_completed.connect(
            self._on_input_diagnostics_completed
        )
        self._inspection_controller.diagnostics_failed.connect(self._on_input_diagnostics_failed)
        self._active_job: OptimizeJobThread | None = None
        self._environment_usable = False
        self._input_dirty = False
        self._last_inspected_input = ""
        self._output_is_auto_generated = True
        self._setting_auto_output = False
        self._run_started_at: float | None = None
        self._job_outcome: tuple[str, str] | None = None
        self._latest_outcome: tuple[str, str] | None = None
        self._latest_action: tuple[str, str] | None = None
        self._elapsed_timer = QTimer(self)
        self._elapsed_timer.setInterval(1000)
        self._elapsed_timer.timeout.connect(self._update_elapsed_status)
        self._connect_panels()

    @property
    def active_job(self) -> OptimizeJobThread | None:
        """Expose the active worker for shutdown coordination only."""
        return self._active_job

    def start(self, *, restore_session: bool) -> None:
        """Populate controls and inspect the optional restored stage."""
        self._workflow_panel.set_workflows(
            [(preset.display_name, preset.name) for preset in self._presets]
        )
        if restore_session:
            self._load_saved_paths()
        self.refresh_environment_status()
        self._refresh_presentation()

    def refresh_environment_status(self) -> None:
        """Read runtime status and notify the window shell."""
        status = self._environment_status_provider()
        self._environment_usable = status.is_usable
        if status.is_usable:
            details = f"{status.operation_count or 0} operations available"
            self.runtime_changed.emit(True, details)
        else:
            first_error = status.errors[0] if status.errors else "Unknown environment problem."
            self.runtime_changed.emit(False, first_error)
        self._refresh_presentation()

    def handle_input_edited(self) -> None:
        """Invalidate stage state while source text is being typed."""
        if not self._input_dirty:
            self._inspection_controller.reset()
        self._input_dirty = True
        self._clear_scene_view("Waiting for input confirmation.")
        self._clear_diagnostics_view("Waiting for input confirmation.")
        self._set_status("Input change pending", "neutral")
        self._refresh_presentation()

    def commit_input(self, force: bool) -> None:
        """Commit the selected source, derive output, and start inspection."""
        input_text = self._workflow_panel.input_path
        if not force and not self._input_dirty and input_text == self._last_inspected_input:
            return
        self._rebuild_output_from_input()
        self._preferences.save_input_path(input_text)
        self._preferences.save_output_path(self._workflow_panel.output_path)
        self._inspect_input()

    def handle_output_changed(self, output_text: str) -> None:
        """Persist manual output changes and restore automatic output when cleared."""
        if not self._setting_auto_output:
            self._output_is_auto_generated = not output_text.strip()
            if self._output_is_auto_generated:
                self._rebuild_output_from_input()
                if self._workflow_panel.output_path:
                    return
        self._preferences.save_output_path(output_text)

    def handle_workflow_changed(self) -> None:
        """Refresh presentation for a newly selected workflow."""
        self._refresh_presentation()

    def handle_scope_changed(self) -> None:
        """Refresh scoped operation disclosure and run settings."""
        self._refresh_presentation()

    def run_job(self) -> None:
        """Confirm replacement if needed and start one optimization worker."""
        preset = self._current_preset()
        input_text = self._workflow_panel.input_path
        if preset is None:
            self._show_error("Choose a workflow.")
            return
        if not input_text:
            self._show_error("Choose an input USD path.")
            return
        if not self._confirm_output_replacement(preset, Path(input_text)):
            return
        self._preferences.save_input_path(input_text)
        settings = OptimizeJobSettings(
            input_path=Path(input_text),
            output_path=self._effective_output_path(),
            preset_name=preset.name,
            force=True,
            write_output=preset.risk != "diagnostic",
            prim_paths=self._results_panel.selected_paths,
        )
        self._start_job(settings)

    def cancel_job(self) -> None:
        """Request cancellation of the active job."""
        if self._active_job is None:
            return
        self._active_job.cancel()
        self._workflow_panel.set_cancelling()
        self._set_status("Cancelling workflow…", "warning")

    def open_output_folder(self) -> None:
        """Open the effective output folder when it exists."""
        output_path = self._effective_output_path()
        folder = output_path.parent if output_path is not None else Path("reports")
        if not folder.exists():
            self._show_error(f"Folder does not exist yet: {folder}")
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder.resolve())))

    def open_overview_target(self, target: str) -> None:
        """Navigate from Overview to its relevant result drill-down."""
        if target == "analysis":
            self._results_panel.show_analysis()
        elif target == "diagnostics":
            self._results_panel.show_diagnostics()
        elif target == "log":
            self._results_panel.show_log()

    def shutdown(self, timeout_ms: int = THREAD_SHUTDOWN_TIMEOUT_MS) -> bool:
        """Cancel jobs and inspection work before Qt destroys its objects."""
        if self._active_job is not None and self._active_job.isRunning():
            self._active_job.cancel()
            if not self._active_job.wait(timeout_ms):
                self._set_status("Waiting for workflow cancellation…", "warning")
                return False
        if not self._inspection_controller.shutdown(timeout_ms):
            self._set_status("Waiting for stage inspection to finish…", "warning")
            return False
        return True

    def _connect_panels(self) -> None:
        self._workflow_panel.input_edited.connect(self.handle_input_edited)
        self._workflow_panel.input_committed.connect(self.commit_input)
        self._workflow_panel.output_changed.connect(self.handle_output_changed)
        self._workflow_panel.workflow_changed.connect(self.handle_workflow_changed)
        self._workflow_panel.run_requested.connect(self.run_job)
        self._workflow_panel.cancel_requested.connect(self.cancel_job)
        self._workflow_panel.open_output_requested.connect(self.open_output_folder)
        self._results_panel.scope_changed.connect(self.handle_scope_changed)
        self._results_panel.overview_action_requested.connect(self.open_overview_target)

    def _load_saved_paths(self) -> None:
        saved_paths = self._preferences.load_paths()
        self._workflow_panel.set_input_path(saved_paths.input_path)
        self._setting_auto_output = True
        self._workflow_panel.set_output_path(saved_paths.output_path)
        self._setting_auto_output = False
        self._output_is_auto_generated = not saved_paths.output_path
        if saved_paths.input_path and saved_paths.output_path:
            self._output_is_auto_generated = saved_paths.output_path == str(
                resolve_default_output_path(Path(saved_paths.input_path))
            )
        if saved_paths.input_path and not saved_paths.output_path:
            self._rebuild_output_from_input()
        if saved_paths.input_path:
            self._inspect_input()

    def _inspect_input(self) -> None:
        input_text = self._workflow_panel.input_path
        self._input_dirty = False
        self._last_inspected_input = input_text
        if not input_text:
            self._inspection_controller.reset()
            self._clear_scene_view("Choose an input USD to inspect its hierarchy.")
            self._clear_diagnostics_view("Choose an input USD to inspect stage statistics.")
            self._refresh_presentation()
            return
        self._clear_diagnostics_view("Inspecting stage statistics…")
        self._inspection_controller.inspect(Path(input_text))
        self._refresh_presentation()

    def _on_input_inspected(self, inspection: InputInspection) -> None:
        if inspection.is_valid:
            self._show_scene_inspection(inspection)
        else:
            self._clear_scene_view(inspection.message)
        self._refresh_presentation()
        self._results_panel.show_overview()

    def _on_input_diagnostics_completed(self, result: OptimizeResult) -> None:
        self._render_stage_diagnostics(result)
        self._refresh_presentation()

    def _on_input_diagnostics_failed(self, message: str) -> None:
        self._clear_diagnostics_view(f"Diagnostics unavailable: {message}")
        self._refresh_presentation()

    def _show_scene_inspection(self, inspection: InputInspection) -> None:
        input_name = Path(self._workflow_panel.input_path).name
        prim_label = "prim" if inspection.prim_count == 1 else "prims"
        root_label = "root" if inspection.root_prim_count == 1 else "roots"
        details = [
            f"{inspection.prim_count:,} {prim_label}",
            f"{inspection.root_prim_count or 0} {root_label}",
        ]
        if inspection.authored_reference_count:
            details.append(f"{inspection.authored_reference_count} references")
        if inspection.authored_payload_count:
            details.append(f"{inspection.authored_payload_count} payloads")
        if inspection.scene_graph_truncated:
            details.append("display truncated")
        message = f"{input_name} · {' · '.join(details)}"
        self._results_panel.scene_summary_label.setText(message)
        self._results_panel.scene_summary_label.setToolTip(inspection.message)
        populate_scene_tree(self._results_panel.scene_tree, inspection.scene_graph)

    def _clear_scene_view(self, message: str) -> None:
        self._results_panel.scene_summary_label.setText(message)
        self._results_panel.scene_summary_label.setToolTip(message)
        self._results_panel.scene_tree.clear()

    def _clear_diagnostics_view(self, message: str) -> None:
        self._results_panel.diagnostics_summary_label.setText(message)
        self._results_panel.diagnostics_summary_label.setToolTip(message)
        self._results_panel.diagnostic_table.setRowCount(0)

    def _render_stage_diagnostics(self, result: OptimizeResult) -> None:
        stats = parse_stage_stats(result.worker_output)
        metrics = parse_stage_metrics(result.worker_output)
        populate_diagnostics_table(self._results_panel.diagnostic_table, stats)
        total = next((stat for stat in stats if stat.prim_type == "Total"), None)
        details = [f"{total.numeric_count:,} prims"] if total is not None else []
        if metrics is not None and metrics.faces is not None:
            details.append(f"{metrics.faces:,} faces")
        if metrics is not None and metrics.vertices is not None:
            details.append(f"{metrics.vertices:,} vertices")
        summary = " · ".join(details) if details else "Stage diagnostics completed."
        self._results_panel.diagnostics_summary_label.setText(summary)
        self._results_panel.diagnostics_summary_label.setToolTip(summary)

    def _refresh_presentation(self) -> None:
        preset = self._current_preset()
        paths = self._results_panel.selected_paths
        self._update_scope(preset, paths)
        reason = self._run_blocking_reason()
        input_message, input_kind = self._input_presentation(reason)
        running = self._active_job is not None
        job_label = ""
        if running and self._run_started_at is not None:
            job_label = f"Running · {int(monotonic() - self._run_started_at)}s"
        self._workflow_panel.set_form_state(
            WorkflowFormState(
                input_message=input_message,
                input_kind=input_kind,
                run_enabled=reason is None,
                running=running,
                job_label=job_label,
            )
        )
        self._update_workflow_details(preset, bool(paths))
        self._refresh_overview(preset, paths)
        if not running:
            if reason is None:
                self._set_status("Ready to run", "success")
            else:
                kind = (
                    "error"
                    if not self._environment_usable or self._inspection_controller.has_error
                    else "neutral"
                )
                if "Inspecting" in reason or "Press Enter" in reason:
                    kind = "info"
                self._set_status(reason, kind)

    def _update_scope(self, preset: PresetView | None, paths: tuple[str, ...]) -> None:
        if not paths:
            message = "Scope: Entire stage. Select prims to limit the operation."
        elif len(paths) == 1:
            message = f"Scope: {paths[0]} and all descendants"
        else:
            message = f"Scope: {len(paths)} selected prim roots and all descendants"
        if paths and preset is not None:
            skipped_labels = [
                get_operation_presentation(operation_name).label
                for operation_name in preset.operations
                if scoped_operation_skip_reason(operation_name) is not None
            ]
            if skipped_labels:
                message += f" · Skipped to preserve scope: {', '.join(skipped_labels)}"
        self._results_panel.scene_scope_label.setText(message)
        self._results_panel.scene_scope_label.setToolTip(message)
        scope_controls_enabled = self._active_job is None
        self._results_panel.scene_tree.setEnabled(scope_controls_enabled)
        self._results_panel.clear_scope_button.setEnabled(bool(paths) and scope_controls_enabled)

    def _update_workflow_details(self, preset: PresetView | None, is_scoped: bool) -> None:
        if preset is None:
            return
        operations: list[tuple[str, str]] = []
        for operation_name in preset.operations:
            presentation = get_operation_presentation(operation_name)
            label = f"{presentation.category} · {presentation.label}"
            tooltip = presentation.description
            skip_reason = scoped_operation_skip_reason(operation_name) if is_scoped else None
            if skip_reason is not None:
                label += " · skipped for selected scope"
                tooltip += f"\n\nSkipped for selected prims: {skip_reason}"
            operations.append((label, tooltip))
        self._workflow_panel.set_workflow_details(
            description=preset.description,
            operations=operations,
            is_diagnostic=preset.risk == "diagnostic",
        )

    def _refresh_overview(self, preset: PresetView | None, paths: tuple[str, ...]) -> None:
        inspection = self._inspection_controller.scene_result
        stage = self._results_panel.scene_summary_label.text()
        scope = (
            "Entire stage"
            if not paths
            else (paths[0] if len(paths) == 1 else f"{len(paths)} selected prim roots")
        )
        workflow = preset.display_name if preset is not None else "Choose a workflow"
        outcome = "No workflow has run for this stage."
        action_label = ""
        action_target = ""
        if self._latest_outcome is not None:
            outcome = self._latest_outcome[0]
            action_label, action_target = self._latest_action or ("View log", "log")
        elif self._active_job is not None:
            outcome = "Workflow running. Open Log to follow worker output."
            action_label, action_target = "View log", "log"
        elif inspection is None and self._workflow_panel.input_path:
            outcome = "Inspecting the selected USD stage."
        elif inspection is not None and not inspection.is_valid:
            outcome = inspection.message
        self._results_panel.set_overview(
            OverviewState(
                stage=stage,
                scope=scope,
                workflow=workflow,
                outcome=outcome,
                action_label=action_label,
                action_target=action_target,
            )
        )

    def _input_presentation(self, reason: str | None) -> tuple[str, str]:
        inspection = self._inspection_controller.scene_result
        if self._input_dirty:
            return "Press Enter or leave the field to inspect.", "neutral"
        if inspection is not None:
            return inspection.message, "success" if inspection.is_valid else "error"
        if not self._workflow_panel.input_path:
            return "Choose a USD file to inspect the stage.", "neutral"
        if reason and "Inspecting" in reason:
            return "Inspecting stage…", "neutral"
        return "Choose a USD file to inspect the stage.", "neutral"

    def _run_blocking_reason(self) -> str | None:
        if self._active_job is not None:
            return "A workflow is already running."
        if not self._environment_usable:
            return "Runtime setup is required before running a workflow."
        if self._current_preset() is None:
            return "Choose a workflow."
        if not self._workflow_panel.input_path:
            return "Choose an input USD."
        if self._input_dirty:
            return "Press Enter or leave the input field to inspect."
        return self._inspection_controller.blocking_reason()

    def _rebuild_output_from_input(self) -> None:
        input_text = self._workflow_panel.input_path
        output_text = ""
        if input_text:
            input_path = Path(input_text)
            if input_path.suffix.lower() in SUPPORTED_USD_EXTENSIONS:
                output_text = str(resolve_default_output_path(input_path))
        self._output_is_auto_generated = True
        self._setting_auto_output = True
        self._workflow_panel.set_output_path(output_text)
        self._setting_auto_output = False

    def _effective_output_path(self) -> Path | None:
        preset = self._current_preset()
        if preset is not None and preset.risk == "diagnostic":
            return None
        if self._workflow_panel.output_path:
            return Path(self._workflow_panel.output_path).expanduser()
        if not self._workflow_panel.input_path:
            return None
        return resolve_default_output_path(Path(self._workflow_panel.input_path))

    def _confirm_output_replacement(self, preset: PresetView, input_path: Path) -> bool:
        if preset.risk == "diagnostic":
            return True
        output_path = self._effective_output_path()
        if output_path is None or not output_path.exists():
            return True
        resolved_input = input_path.expanduser().resolve()
        resolved_output = output_path.expanduser().resolve()
        if resolved_input == resolved_output:
            return self._confirm_replacement(
                "Confirm source replacement",
                "The output is the source USD. Continuing permanently replaces the source file.",
            )
        return self._confirm_replacement(
            "Confirm output replacement", f"Replace the existing output file?\n\n{resolved_output}"
        )

    def _start_job(self, settings: OptimizeJobSettings) -> None:
        self._results_panel.clear_log()
        self._active_job = OptimizeJobThread(settings)
        self._run_started_at = monotonic()
        self._job_outcome = None
        self._latest_outcome = None
        self._latest_action = None
        self._active_job.output_received.connect(
            lambda text: append_log_text(self._results_panel.log_edit, text)
        )
        self._active_job.succeeded.connect(self._on_job_succeeded)
        self._active_job.failed.connect(self._on_job_failed)
        self._active_job.finished.connect(self._on_thread_finished)
        self._active_job.finished.connect(self._active_job.deleteLater)
        self._elapsed_timer.start()
        self._refresh_presentation()
        self._results_panel.show_overview()
        self._set_status("Workflow running…", "info")
        self._active_job.start()

    def _on_job_succeeded(self, result: OptimizeResult) -> None:
        append_log_text(self._results_panel.log_edit, "\nFinished successfully.\n")
        if result.worker_output:
            self._show_diagnostics(result)
            return
        self._job_outcome = ("Optimized copy completed", "success")
        self._latest_outcome = self._job_outcome
        self._latest_action = ("View log", "log")
        self._show_completion(result)
        self._results_panel.show_overview()
        self._refresh_presentation()

    def _show_diagnostics(self, result: OptimizeResult) -> None:
        stats = parse_stage_stats(result.worker_output)
        action_label, action_target = "View log", "log"
        if stats:
            self._render_stage_diagnostics(result)
            action_label, action_target = "View diagnostics", "diagnostics"
        if result.operation_results:
            self._results_panel.analysis_edit.setPlainText(
                format_analysis_results(result.operation_results)
            )
            self._results_panel.set_analysis_visible(True)
            action_label, action_target = "View analysis", "analysis"
            completion_message = "Analysis complete"
        elif stats:
            completion_message = "Diagnostics complete"
        else:
            completion_message = "Workflow complete"
        self._job_outcome = (completion_message, "success")
        self._latest_outcome = self._job_outcome
        self._latest_action = (action_label, action_target)
        self._refresh_presentation()
        self._results_panel.show_overview()

    def _on_job_failed(self, message: str) -> None:
        if message == "Optimization cancelled.":
            append_log_text(self._results_panel.log_edit, "\nCancelled.\n")
            self._job_outcome = ("Workflow cancelled", "warning")
        else:
            append_log_text(self._results_panel.log_edit, f"\nFailed: {message}\n")
            self._job_outcome = ("Workflow failed", "error")
            self._show_error(message)
        self._latest_outcome = self._job_outcome
        self._latest_action = ("View log", "log")
        self._refresh_presentation()
        self._set_status(*self._job_outcome)
        self._results_panel.show_overview()

    def _on_thread_finished(self) -> None:
        self._elapsed_timer.stop()
        self._run_started_at = None
        self._active_job = None
        self._refresh_presentation()
        if self._job_outcome is not None:
            self._set_status(*self._job_outcome)
        self._job_outcome = None

    def _update_elapsed_status(self) -> None:
        if self._run_started_at is not None:
            self._workflow_panel.set_elapsed_seconds(int(monotonic() - self._run_started_at))

    def _current_preset(self) -> PresetView | None:
        name = self._workflow_panel.workflow_name
        return next((preset for preset in self._presets if preset.name == name), None)

    def _set_status(self, message: str, kind: str) -> None:
        self.status_changed.emit(message, kind)
