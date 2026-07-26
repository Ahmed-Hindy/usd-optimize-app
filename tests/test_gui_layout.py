from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFormLayout, QToolButton

from usd_optimize_app.gui.main_window import MainWindow


def test_workflow_panel_exposes_reviewed_workflows(window: MainWindow) -> None:
    panel = window._workflow_panel

    names = [panel.workflow_combo.itemText(index) for index in range(panel.workflow_combo.count())]

    assert names == ["Safe Cleanup", "Geometry Optimization", "Find Overlaps"]
    assert panel.workflow_name == "safe_publish"
    assert panel.run_button.text() == "Run workflow"


def test_panels_own_layout_and_summary_led_tab_order(window: MainWindow) -> None:
    workflow = window._workflow_panel
    results = window._results_panel
    labels = []
    for row_index in range(workflow.form_layout.rowCount()):
        label_item = workflow.form_layout.itemAt(row_index, QFormLayout.ItemRole.LabelRole)
        labels.append(label_item.widget().text())

    tab_names = [results.tabs.tabText(index) for index in range(results.tabs.count())]

    assert labels == ["SOURCE USD", "WORKFLOW", "OUTPUT USD"]
    assert (
        workflow.form_layout.itemAt(1, QFormLayout.ItemRole.FieldRole).widget()
        is workflow.workflow_field_widget
    )
    assert workflow.workflow_field_widget.layout().itemAt(0).widget() is workflow.workflow_combo
    assert workflow.output_row.itemAt(2).widget() is workflow.open_output_button
    assert isinstance(workflow.open_output_button, QToolButton)
    assert workflow.open_output_button.accessibleName() == "Open output folder"
    assert tab_names == ["Overview", "Scene", "Diagnostics", "Analysis", "Log"]
    assert results.tabs.currentWidget() is results.overview_tab
    assert results.tabs.isTabVisible(results.analysis_tab_index) is False


def test_operation_list_is_read_only(window: MainWindow) -> None:
    operation_list = window._workflow_panel.operation_list

    assert operation_list.count() == 4
    for index in range(operation_list.count()):
        item = operation_list.item(index)
        assert not item.flags() & Qt.ItemFlag.ItemIsUserCheckable
        assert not item.flags() & Qt.ItemFlag.ItemIsSelectable


def test_title_and_layout_fit_supported_window(window: MainWindow) -> None:
    minimum_size = window.minimumSizeHint()

    assert window.windowTitle().startswith("USD Optimize Tool -- ")
    assert minimum_size.width() <= 960
    assert minimum_size.height() <= 680
