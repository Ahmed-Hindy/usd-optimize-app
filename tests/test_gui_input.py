from __future__ import annotations

from pathlib import Path

import pytest
from gui_test_helpers import complete_scene_inspection
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from usd_optimize_app.backend import InputInspection, SceneGraphNode
from usd_optimize_app.gui.main_window import MainWindow
from usd_optimize_app.models import OptimizeResult


def test_scene_inspection_populates_hierarchy(window: MainWindow, tmp_path: Path) -> None:
    window._input_edit.setText(str(tmp_path / "asset.usda"))
    hierarchy = (
        SceneGraphNode(
            name="World",
            path="/World",
            type_name="Xform",
            children=(
                SceneGraphNode(
                    name="Mesh",
                    path="/World/Mesh",
                    type_name="Mesh",
                    has_references=True,
                ),
            ),
        ),
    )
    inspection = InputInspection(
        is_valid=True,
        message="Scene loaded · 2 prims",
        root_prim_count=1,
        authored_reference_count=1,
        prim_count=2,
        scene_graph=hierarchy,
    )

    complete_scene_inspection(window, inspection)

    assert window._input_state_label.isHidden()
    assert window._tabs.currentWidget() is window._scene_tab
    assert "2 prims" in window._scene_summary_label.text()
    root_item = window._scene_tree.topLevelItem(0)
    assert root_item.text(0) == "World"
    assert root_item.text(1) == "Xform"
    assert root_item.child(0).text(0) == "Mesh"
    assert "/World/Mesh" in root_item.child(0).toolTip(0)


def test_scene_tree_supports_multiple_prim_selection(window: MainWindow, tmp_path: Path) -> None:
    window._environment_usable = True
    window._update_run_readiness()
    window._input_edit.setText(str(tmp_path / "asset.usda"))
    hierarchy = (
        SceneGraphNode(
            name="World",
            path="/World",
            type_name="Xform",
            children=(
                SceneGraphNode(name="First", path="/World/First", type_name="Mesh"),
                SceneGraphNode(name="Second", path="/World/Second", type_name="Mesh"),
            ),
        ),
    )
    complete_scene_inspection(
        window,
        InputInspection(
            is_valid=True,
            message="Scene loaded · 3 prims",
            root_prim_count=1,
            prim_count=3,
            scene_graph=hierarchy,
        ),
    )
    root_item = window._scene_tree.topLevelItem(0)

    root_item.child(0).setSelected(True)
    root_item.child(1).setSelected(True)

    assert len(window._scene_tree.selectedItems()) == 2
    assert window._scene_scope_label.text().startswith(
        "Scope: 2 selected prim roots and all descendants"
    )
    assert "Skipped to preserve scope: Optimize materials" in window._scene_scope_label.text()
    assert "skipped for selected scope" in window._operation_list.item(2).text()
    assert window._clear_scope_button.isEnabled() is True

    window._clear_scope_button.click()

    assert window._scene_tree.selectedItems() == []
    assert "Scope: Entire stage" in window._scene_scope_label.text()
    assert window._clear_scope_button.isEnabled() is False


def test_parent_and_child_selection_collapses_to_one_scope_root(
    window: MainWindow,
    tmp_path: Path,
) -> None:
    window._environment_usable = True
    window._update_run_readiness()
    window._input_edit.setText(str(tmp_path / "asset.usda"))
    hierarchy = (
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
    )
    complete_scene_inspection(
        window,
        InputInspection(
            is_valid=True,
            message="Scene loaded · 3 prims",
            root_prim_count=1,
            prim_count=3,
            scene_graph=hierarchy,
        ),
    )
    asset_item = window._scene_tree.topLevelItem(0).child(0)
    asset_item.setSelected(True)
    asset_item.child(0).setSelected(True)

    assert len(window._scene_tree.selectedItems()) == 2
    assert window._scene_scope_label.text().startswith("Scope: /World/Asset and all descendants")


def test_invalid_input_shows_file_error(window: MainWindow, tmp_path: Path) -> None:
    window._input_edit.setText(str(tmp_path / "missing.usda"))

    complete_scene_inspection(window, InputInspection(False, "Input USD file does not exist."))

    assert "does not exist" in window._input_state_label.text()
    assert window._scene_tree.topLevelItemCount() == 0


def test_committed_input_rebuilds_manual_output(
    window: MainWindow,
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(window._inspection_controller, "inspect", lambda _path: None)
    first_input = tmp_path / "first.usda"
    second_input = tmp_path / "second.usda"
    manual_output = tmp_path / "manual.usda"

    window._input_edit.setText(str(first_input))
    window._on_input_text_edited()
    window._on_input_committed()
    window._output_edit.setText(str(manual_output))
    window._input_edit.setText(str(second_input))
    window._on_input_text_edited()

    assert window._output_edit.text() == str(manual_output)

    window._on_input_committed()

    assert window._output_edit.text() == str(tmp_path / "second.optimized.usda")


def test_clearing_output_restores_suggested_destination(
    window: MainWindow,
    tmp_path: Path,
) -> None:
    input_path = tmp_path / "asset.usda"
    window._input_edit.setText(str(input_path))
    window._output_edit.setText(str(tmp_path / "manual.usda"))

    window._output_edit.clear()

    assert window._output_edit.text() == str(tmp_path / "asset.optimized.usda")


def test_editing_input_clears_stale_scene(window: MainWindow, tmp_path: Path) -> None:
    window._input_edit.setText(str(tmp_path / "first.usda"))
    complete_scene_inspection(window, InputInspection(True, "Stage ready · 3 root prims", 3))

    window._input_edit.setText(str(tmp_path / "second.usda"))
    window._on_input_text_edited()

    assert window._inspection_controller.scene_result is None
    assert "Press Enter or leave the field" in window._input_state_label.text()
    assert window._scene_tree.topLevelItemCount() == 0


def test_typing_is_inert_until_input_is_committed(
    window: MainWindow,
    monkeypatch,
    qt_application: QApplication,
    tmp_path: Path,
) -> None:
    window._environment_usable = True
    window._update_run_readiness()
    inspected_paths = []

    def fake_inspect_input() -> None:
        input_text = window._input_edit.text().strip()
        inspected_paths.append(input_text)
        window._input_dirty = False
        window._last_inspected_input = input_text

    monkeypatch.setattr(window, "_inspect_input", fake_inspect_input)
    input_path = tmp_path / "asset.usda"
    previous_output = tmp_path / "previous.usda"
    window._input_edit.clear()
    window._output_edit.setText(str(previous_output))
    window.show()
    window._input_edit.setFocus()
    qt_application.processEvents()
    monkeypatch.setattr(
        Path,
        "exists",
        lambda _path: pytest.fail("Typing must not probe the filesystem."),
    )

    QTest.keyClicks(window._input_edit, str(input_path))
    qt_application.processEvents()

    assert inspected_paths == []
    assert window._output_edit.text() == str(previous_output)

    QTest.keyClick(window._input_edit, Qt.Key.Key_Tab)
    qt_application.processEvents()
    window._on_input_committed()

    assert inspected_paths == [str(input_path)]
    assert window._output_edit.text() == str(tmp_path / "asset.optimized.usda")

    window._on_input_return_pressed()

    assert inspected_paths == [str(input_path), str(input_path)]


def test_committed_input_delegates_to_inspection_controller(
    window: MainWindow,
    monkeypatch,
    tmp_path: Path,
) -> None:
    input_path = tmp_path / "asset.usda"
    inspected_paths = []
    monkeypatch.setattr(window._inspection_controller, "inspect", inspected_paths.append)
    window._input_edit.setText(str(input_path))

    window._inspect_input()

    assert inspected_paths == [input_path]


def test_automatic_diagnostics_populates_permanent_tab(
    window: MainWindow,
    tmp_path: Path,
) -> None:
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

    window._on_input_diagnostics_completed(result)

    assert window._diagnostic_table.rowCount() == 2
    assert "2 prims" in window._diagnostics_summary_label.text()
    assert "1,236 faces" in window._diagnostics_summary_label.text()
    assert "1,286 vertices" in window._diagnostics_summary_label.text()
