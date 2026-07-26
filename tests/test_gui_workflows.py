from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QMessageBox

from usd_optimize_app.backend import InputInspection, SceneGraphNode
from usd_optimize_app.gui.main_window import MainWindow
from usd_optimize_app.models import OptimizeResult


def _complete_scene_inspection(window: MainWindow, inspection: InputInspection) -> None:
    window._controller._inspection_controller.scene_completed.emit(inspection)


def test_existing_output_is_confirmed_and_run_settings_are_scoped(
    window: MainWindow, monkeypatch, tmp_path: Path
) -> None:
    workflow = window._workflow_panel
    controller = window._controller
    input_path = tmp_path / "asset.usda"
    output_path = tmp_path / "asset.optimized.usda"
    input_path.write_text("#usda 1.0\n", encoding="utf-8")
    output_path.write_text("existing", encoding="utf-8")
    workflow.set_input_path(str(input_path))
    workflow.output_edit.setText(str(output_path))
    controller._environment_usable = True
    _complete_scene_inspection(window, InputInspection(True, "Stage ready", 1))
    captured_settings = []
    monkeypatch.setattr(controller, "_start_job", captured_settings.append)
    monkeypatch.setattr(controller, "_confirm_replacement", lambda *_args: True)

    controller.run_job()

    assert captured_settings[0].force is True
    assert captured_settings[0].output_path == output_path
    assert captured_settings[0].preset_name == "safe_publish"


def test_run_uses_selected_scene_prims_as_hierarchy_scope(
    window: MainWindow, monkeypatch, tmp_path: Path
) -> None:
    workflow = window._workflow_panel
    results = window._results_panel
    controller = window._controller
    input_path = tmp_path / "asset.usda"
    input_path.write_text("#usda 1.0\n", encoding="utf-8")
    workflow.set_input_path(str(input_path))
    controller._environment_usable = True
    _complete_scene_inspection(
        window,
        InputInspection(
            is_valid=True,
            message="Stage ready",
            root_prim_count=1,
            prim_count=2,
            scene_graph=(
                SceneGraphNode(
                    name="World",
                    path="/World",
                    type_name="Xform",
                    children=(
                        SceneGraphNode(
                            name="Asset",
                            path="/World/Asset",
                            type_name="Xform",
                        ),
                    ),
                ),
            ),
        ),
    )
    results.scene_tree.topLevelItem(0).child(0).setSelected(True)
    captured_settings = []
    monkeypatch.setattr(controller, "_start_job", captured_settings.append)

    controller.run_job()

    assert captured_settings[0].prim_paths == ("/World/Asset",)


def test_running_workflow_locks_scene_scope(window: MainWindow, tmp_path: Path) -> None:
    class FakeJob:
        def isRunning(self) -> bool:  # noqa: N802
            return False

    workflow = window._workflow_panel
    results = window._results_panel
    controller = window._controller
    workflow.set_input_path(str(tmp_path / "asset.usda"))
    _complete_scene_inspection(
        window,
        InputInspection(
            is_valid=True,
            message="Stage ready",
            root_prim_count=1,
            prim_count=1,
            scene_graph=(SceneGraphNode(name="Asset", path="/Asset", type_name="Xform"),),
        ),
    )
    results.scene_tree.topLevelItem(0).setSelected(True)
    controller._active_job = FakeJob()

    controller._refresh_presentation()

    assert results.scene_tree.isEnabled() is False
    assert results.clear_scope_button.isEnabled() is False


def test_workflow_and_scope_drive_operation_presentation(
    window: MainWindow, tmp_path: Path
) -> None:
    workflow = window._workflow_panel
    results = window._results_panel
    workflow.set_input_path(str(tmp_path / "asset.usda"))
    _complete_scene_inspection(
        window,
        InputInspection(
            is_valid=True,
            message="Stage ready",
            root_prim_count=1,
            prim_count=1,
            scene_graph=(SceneGraphNode(name="Asset", path="/Asset", type_name="Xform"),),
        ),
    )
    workflow.workflow_combo.setCurrentIndex(
        workflow.workflow_combo.findData("geometry_optimization")
    )
    results.scene_tree.topLevelItem(0).setSelected(True)

    labels = [
        workflow.operation_list.item(index).text()
        for index in range(workflow.operation_list.count())
    ]

    assert workflow.workflow_name == "geometry_optimization"
    assert labels == ["Scene cleanup · Compute extents", "Geometry data · Optimize primvars"]
    assert "Skipped" not in results.scene_scope_label.text()


def test_runtime_blocker_replaces_workspace(window: MainWindow) -> None:
    assert window._content_stack.currentWidget() is window._runtime_blocker
    assert window._workspace_splitter.isEnabled() is False
    assert window.statusBar().isVisible() is False
    assert window._runtime_blocker_title.text() == "USD Optimize runtime is unavailable"
    assert "Runtime unavailable for test." in window._runtime_blocker_detail.text()


def test_runtime_state_hides_status_bar_when_runtime_becomes_unavailable(
    window: MainWindow,
) -> None:
    window._set_runtime_state(True, "2 operations available")
    window._set_runtime_state(False, "Runtime disappeared.")

    assert window._content_stack.currentWidget() is window._runtime_blocker
    assert window.statusBar().isHidden()
    assert "Runtime disappeared." in window._runtime_blocker_detail.text()


def test_analysis_completion_is_summary_led(window: MainWindow, tmp_path: Path) -> None:
    result = OptimizeResult(
        input_path=tmp_path / "input.usda",
        output_path=tmp_path / "output.usda",
        preset_name="find_overlaps",
        success=True,
        duration_seconds=0.1,
        operations=["findOverlappingMeshes"],
        worker_output="Executed findOverlappingMeshes analysis (0.1s)\n",
        operation_results=[
            {
                "operation": "findOverlappingMeshes",
                "output": {"analysis": {"overlappingMeshes": ["/World/Mesh"]}},
            }
        ],
    )

    controller = window._controller
    controller._active_job = object()
    controller._show_diagnostics(result)

    results = window._results_panel
    assert results.tabs.currentWidget() is results.overview_tab
    assert results.tabs.isTabVisible(results.analysis_tab_index)
    controller._on_thread_finished()
    window._set_runtime_state(True, "test runtime")
    results.show_analysis()
    assert "Overlapping Meshes (1)" in results.analysis_edit.toPlainText()
    assert results.tabs.currentWidget() is results.analysis_edit


def test_cancellation_updates_summary_without_error(window: MainWindow) -> None:
    controller = window._controller
    controller._on_job_failed("Optimization cancelled.")

    assert "Workflow cancelled" in window._status_message_label.text()


def test_completion_popup_remains_owned_by_window(
    window: MainWindow, monkeypatch, tmp_path: Path
) -> None:
    result = OptimizeResult(
        input_path=tmp_path / "input.usda",
        output_path=tmp_path / "output.usda",
        preset_name="safe_publish",
        success=True,
        duration_seconds=1.25,
        operations=["computeExtents"],
    )
    captured_popup = []
    monkeypatch.setattr(QMessageBox, "information", lambda *args: captured_popup.append(args))

    window._controller._on_job_succeeded(result)

    assert captured_popup == [
        (
            window,
            "Conversion complete",
            f"New USD Scene saved to:\n\n'{result.output_path}'\n\nCompleted in 1.2s.",
        )
    ]


def test_shutdown_cancels_and_joins_active_job(window: MainWindow) -> None:
    class FakeJob:
        def __init__(self) -> None:
            self.cancelled = False
            self.wait_timeout = None

        def isRunning(self) -> bool:  # noqa: N802
            return True

        def cancel(self) -> None:
            self.cancelled = True

        def wait(self, timeout: int) -> bool:
            self.wait_timeout = timeout
            return True

    active_job = FakeJob()
    window._controller._active_job = active_job

    assert window._controller.shutdown() is True
    assert active_job.cancelled is True
    assert active_job.wait_timeout == 5_000
