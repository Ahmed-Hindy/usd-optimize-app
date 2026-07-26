from __future__ import annotations

from pathlib import Path

from gui_test_helpers import complete_scene_inspection
from PySide6.QtGui import QPalette
from PySide6.QtWidgets import QApplication, QMessageBox

from usd_optimize_app.backend import InputInspection, SceneGraphNode
from usd_optimize_app.gui import main_window
from usd_optimize_app.gui.main_window import MainWindow
from usd_optimize_app.models import OptimizeResult


def test_existing_output_is_confirmed_and_runs_with_force(
    window: MainWindow,
    monkeypatch,
    tmp_path: Path,
) -> None:
    input_path = tmp_path / "asset.usda"
    output_path = tmp_path / "asset.optimized.usda"
    input_path.write_text("#usda 1.0\n", encoding="utf-8")
    output_path.write_text("existing", encoding="utf-8")
    window._environment_usable = True
    window._input_edit.setText(str(input_path))
    complete_scene_inspection(window, InputInspection(True, "Stage ready · 1 root prims", 1))
    window._output_edit.setText(str(output_path))
    captured_settings = []
    monkeypatch.setattr(
        main_window.QMessageBox,
        "question",
        lambda *args, **kwargs: QMessageBox.StandardButton.Yes,
    )
    monkeypatch.setattr(window, "_start_job", captured_settings.append)

    window._run_job()

    assert captured_settings[0].force is True
    assert captured_settings[0].output_path == output_path
    assert captured_settings[0].preset_name == "safe_publish"


def test_geometry_optimization_keeps_all_operations_in_selected_scope(
    window: MainWindow,
    tmp_path: Path,
) -> None:
    window._input_edit.setText(str(tmp_path / "asset.usda"))
    complete_scene_inspection(
        window,
        InputInspection(
            is_valid=True,
            message="Scene loaded · 1 prim",
            root_prim_count=1,
            prim_count=1,
            scene_graph=(
                SceneGraphNode(
                    name="Asset",
                    path="/Asset",
                    type_name="Xform",
                ),
            ),
        ),
    )
    workflow_index = window._workflow_combo.findData("geometry_optimization")
    window._workflow_combo.setCurrentIndex(workflow_index)
    window._scene_tree.topLevelItem(0).setSelected(True)

    operation_labels = [
        window._operation_list.item(index).text() for index in range(window._operation_list.count())
    ]

    assert window._current_preset().name == "geometry_optimization"
    assert operation_labels == [
        "Scene cleanup · Compute extents",
        "Geometry data · Optimize primvars",
    ]
    assert "Skipped" not in window._scene_scope_label.text()


def test_run_uses_selected_scene_prims_as_hierarchy_scope(
    window: MainWindow,
    monkeypatch,
    tmp_path: Path,
) -> None:
    input_path = tmp_path / "asset.usda"
    input_path.write_text("#usda 1.0\n", encoding="utf-8")
    window._input_edit.setText(str(input_path))
    complete_scene_inspection(
        window,
        InputInspection(
            is_valid=True,
            message="Scene loaded · 2 prims",
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
                            children=(
                                SceneGraphNode(
                                    name="Mesh",
                                    path="/World/Asset/Mesh",
                                    type_name="Mesh",
                                ),
                            ),
                        ),
                    ),
                ),
            ),
        ),
    )
    asset_item = window._scene_tree.topLevelItem(0).child(0)
    asset_item.setSelected(True)
    asset_item.child(0).setSelected(True)
    captured_settings = []
    monkeypatch.setattr(window, "_start_job", captured_settings.append)

    window._run_job()

    assert captured_settings[0].prim_paths == ("/World/Asset",)


def test_missing_runtime_disables_and_dims_run_button(
    window: MainWindow,
    qt_application: QApplication,
) -> None:
    window._environment_usable = False
    window._update_run_readiness()
    window.show()
    qt_application.processEvents()

    disabled_text_color = window._run_button.palette().color(QPalette.ColorRole.ButtonText)

    assert window._run_button.isEnabled() is False
    assert disabled_text_color.name() == "#7d756a"
    assert "Runtime setup is required" in window._status_message_label.text()


def test_missing_runtime_replaces_workspace_with_one_blocking_message(
    window: MainWindow,
) -> None:
    assert window._content_stack.currentWidget() is window._runtime_blocker
    assert window._workspace_splitter.isEnabled() is False
    assert window.statusBar().isVisible() is False
    assert window._runtime_blocker_title.text() == "USD Optimize runtime is unavailable"
    assert "Runtime unavailable for test." in window._runtime_blocker_detail.text()


def test_run_readiness_requires_valid_inspection(window: MainWindow, tmp_path: Path) -> None:
    input_path = tmp_path / "asset.usda"
    input_path.write_text("#usda 1.0\n", encoding="utf-8")
    window._environment_usable = True
    window._input_edit.setText(str(input_path))

    assert window._run_button.isEnabled() is False

    complete_scene_inspection(window, InputInspection(True, "Stage ready · 1 root prims", 1))

    assert window._run_button.isEnabled() is True
    assert window._status_message_label.text() == "● Ready to run"


def test_analysis_results_are_shown_in_analysis_tab(window: MainWindow, tmp_path: Path) -> None:
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

    window._show_diagnostics(result)

    assert window._tabs.currentWidget() is window._analysis_edit
    assert window._tabs.isTabVisible(window._analysis_tab_index)
    analysis_text = window._analysis_edit.toPlainText()
    assert "Find overlaps" in analysis_text
    assert "Overlapping Meshes (1)" in analysis_text
    assert "  • /World/Mesh" in analysis_text
    assert "{" not in analysis_text


def test_completion_status_survives_thread_cleanup(
    window: MainWindow,
    monkeypatch,
    tmp_path: Path,
) -> None:
    result = OptimizeResult(
        input_path=tmp_path / "input.usda",
        output_path=tmp_path / "output.usda",
        preset_name="safe_publish",
        success=True,
        duration_seconds=0.1,
        operations=["computeExtents"],
    )
    monkeypatch.setattr(main_window.QMessageBox, "information", lambda *args: None)

    window._on_job_succeeded(result)
    window._on_thread_finished()

    assert window._status_message_label.text() == "● Optimized copy completed"


def test_successful_conversion_shows_saved_output_popup(
    window: MainWindow,
    monkeypatch,
    tmp_path: Path,
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
    monkeypatch.setattr(
        main_window.QMessageBox,
        "information",
        lambda *args: captured_popup.append(args),
    )

    window._on_job_succeeded(result)

    assert captured_popup == [
        (
            window,
            "Conversion complete",
            f"New USD Scene saved to:\n\n'{result.output_path}'\n\nCompleted in 1.2s.",
        )
    ]


def test_cancellation_is_not_shown_as_an_error(window: MainWindow, monkeypatch) -> None:
    shown_errors = []
    monkeypatch.setattr(window, "_show_error", shown_errors.append)

    window._on_job_failed("Optimization cancelled.")
    window._on_thread_finished()

    assert shown_errors == []
    assert window._job_state_label.text() == ""
    assert window._job_state_label.isHidden()
    assert window._status_message_label.text() == "● Workflow cancelled"


def test_single_action_button_switches_between_run_and_cancel(window: MainWindow) -> None:
    class FakeJob:
        def __init__(self) -> None:
            self.cancelled = False

        def cancel(self) -> None:
            self.cancelled = True

    window._environment_usable = True
    window._update_run_readiness()
    active_job = FakeJob()
    window._active_job = active_job
    window._set_running_state()

    assert window._run_button.text() == "Cancel workflow"
    window._run_button.click()

    assert active_job.cancelled is True
    assert window._run_button.text() == "Cancelling…"

    window._active_job = None
    window._set_idle_controls()
    assert window._run_button.text() == "Run workflow"


def test_close_event_cancels_and_joins_active_job(window: MainWindow) -> None:
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

    class FakeCloseEvent:
        def __init__(self) -> None:
            self.accepted = False
            self.ignored = False

        def accept(self) -> None:
            self.accepted = True

        def ignore(self) -> None:
            self.ignored = True

    active_job = FakeJob()
    close_event = FakeCloseEvent()
    window._active_job = active_job

    window.closeEvent(close_event)

    assert active_job.cancelled is True
    assert active_job.wait_timeout == 5_000
    assert close_event.accepted is True
    assert close_event.ignored is False
    window._active_job = None
