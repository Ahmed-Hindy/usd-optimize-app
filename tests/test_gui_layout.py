from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFormLayout, QToolButton

from usd_optimize_app.gui.main_window import MainWindow


def test_gui_exposes_only_explicit_user_workflows(window: MainWindow) -> None:
    workflow_names = [
        window._workflow_combo.itemText(index) for index in range(window._workflow_combo.count())
    ]

    assert workflow_names == [
        "Safe Cleanup",
        "Geometry Optimization",
        "Find Overlaps",
    ]
    assert window._current_preset().name == "safe_publish"
    assert window._run_button.text() == "Run workflow"


def test_workflow_layout_and_result_tab_order(window: MainWindow) -> None:
    labels = []
    for row_index in range(window._file_form_layout.rowCount()):
        label_item = window._file_form_layout.itemAt(row_index, QFormLayout.ItemRole.LabelRole)
        labels.append(label_item.widget().text())

    workflow_item = window._file_form_layout.itemAt(1, QFormLayout.ItemRole.FieldRole)
    workflow_layout = window._workflow_field_widget.layout()
    tab_names = [window._tabs.tabText(index) for index in range(window._tabs.count())]

    assert labels == ["SOURCE USD", "WORKFLOW", "OUTPUT USD"]
    assert workflow_item.widget() is window._workflow_field_widget
    assert workflow_layout.itemAt(0).widget() is window._workflow_combo
    assert workflow_layout.itemAt(1).widget() is window._description_label
    assert window._output_row.itemAt(2).widget() is window._open_output_button
    assert isinstance(window._open_output_button, QToolButton)
    assert window._open_output_button.accessibleName() == "Open output folder"
    assert tab_names == ["Scene", "Diagnostics", "Analysis", "Log"]
    assert window._tabs.isTabVisible(window._scene_tab_index)
    assert window._tabs.isTabVisible(window._diagnostics_tab_index)


def test_operation_list_is_read_only(window: MainWindow) -> None:
    assert window._operation_list.count() == 4
    for index in range(window._operation_list.count()):
        item = window._operation_list.item(index)
        assert not item.flags() & Qt.ItemFlag.ItemIsUserCheckable
        assert not item.flags() & Qt.ItemFlag.ItemIsSelectable


def test_title_and_layout_fit_supported_window(window: MainWindow) -> None:
    minimum_size = window.minimumSizeHint()

    assert window.windowTitle().startswith("USD Optimize Tool -- ")
    assert minimum_size.width() <= 960
    assert minimum_size.height() <= 680
