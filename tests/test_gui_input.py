from __future__ import annotations

from pathlib import Path

from usd_optimize_app.backend import InputInspection, SceneGraphNode
from usd_optimize_app.gui.main_window import MainWindow
from usd_optimize_app.models import OptimizeResult


def _complete_scene_inspection(window: MainWindow, inspection: InputInspection) -> None:
    window._controller._inspection_controller.scene_completed.emit(inspection)


def test_scene_inspection_populates_results_and_overview(
    window: MainWindow, tmp_path: Path
) -> None:
    workflow = window._workflow_panel
    results = window._results_panel
    workflow.set_input_path(str(tmp_path / "asset.usda"))
    inspection = InputInspection(
        is_valid=True,
        message="Scene loaded · 2 prims",
        root_prim_count=1,
        authored_reference_count=1,
        prim_count=2,
        scene_graph=(
            SceneGraphNode(
                name="World",
                path="/World",
                type_name="Xform",
                children=(SceneGraphNode(name="Mesh", path="/World/Mesh", type_name="Mesh"),),
            ),
        ),
    )

    _complete_scene_inspection(window, inspection)

    assert results.tabs.currentWidget() is results.scene_tab
    assert not results.tabs.isHidden()
    assert results.compact_summary.isHidden()
    assert "2 prims" in results.scene_summary_label.text()
    assert "2 prims" in results.overview_stage_value.text()
    assert results.scene_tree.topLevelItem(0).child(0).text(0) == "Mesh"


def test_scope_refreshes_operation_disclosure_and_overview(
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
            prim_count=2,
            scene_graph=(
                SceneGraphNode(
                    name="World",
                    path="/World",
                    type_name="Xform",
                    children=(SceneGraphNode(name="Mesh", path="/World/Mesh", type_name="Mesh"),),
                ),
            ),
        ),
    )

    results.scene_tree.topLevelItem(0).child(0).setSelected(True)

    assert results.scene_scope_label.text().startswith("Scope: /World/Mesh")
    assert results.overview_scope_value.text() == "/World/Mesh"
    assert "skipped for selected scope" in workflow.operation_list.item(2).text()


def test_input_edit_is_inert_until_commit(window: MainWindow, monkeypatch, tmp_path: Path) -> None:
    workflow = window._workflow_panel
    controller = window._controller
    inspected_paths = []
    monkeypatch.setattr(controller._inspection_controller, "inspect", inspected_paths.append)
    first_input = tmp_path / "first.usda"
    second_input = tmp_path / "second.usda"

    workflow.set_input_path(str(first_input))
    controller.handle_input_edited()

    assert inspected_paths == []
    assert workflow.output_path == ""

    controller.commit_input(False)
    assert inspected_paths == [first_input]
    assert workflow.output_path == str(tmp_path / "first.optimized.usda")

    workflow.set_output_path(str(tmp_path / "manual.usda"))
    workflow.set_input_path(str(second_input))
    controller.handle_input_edited()
    controller.commit_input(False)

    assert workflow.output_path == str(tmp_path / "second.optimized.usda")


def test_clearing_output_restores_suggested_destination(window: MainWindow, tmp_path: Path) -> None:
    workflow = window._workflow_panel
    workflow.set_input_path(str(tmp_path / "asset.usda"))
    workflow.output_edit.setText(str(tmp_path / "manual.usda"))
    workflow.output_edit.clear()

    assert workflow.output_path == str(tmp_path / "asset.optimized.usda")


def test_diagnostics_are_rendered_in_results_panel(window: MainWindow, tmp_path: Path) -> None:
    result = OptimizeResult(
        input_path=tmp_path / "input.usda",
        output_path=tmp_path / "diagnostics.usda",
        preset_name="diagnostics",
        success=True,
        duration_seconds=0.1,
        operations=["printStats"],
        worker_output="""
| Faces: 1,236 |
| Vertices: 1,286 |
| Mesh  2  0  0 |
| Total  2  0  0 |
""",
    )

    window._controller._on_input_diagnostics_completed(result)

    results = window._results_panel
    assert results.diagnostic_table.rowCount() == 2
    assert "2 prims" in results.diagnostics_summary_label.text()
    assert "1,236 faces" in results.diagnostics_summary_label.text()


def test_analysis_tab_opens_result_drill_down(window: MainWindow) -> None:
    results = window._results_panel
    window._set_runtime_state(True, "test runtime")
    results.set_analysis_visible(True)
    results.show_analysis()

    assert results.tabs.currentWidget() is results.analysis_edit
