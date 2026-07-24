from __future__ import annotations

from usd_optimize_app.backend import InputInspection
from usd_optimize_app.gui.main_window import MainWindow


def select_workflow(window: MainWindow, preset_name: str) -> None:
    index = window._workflow_combo.findData(preset_name)
    assert index >= 0
    window._workflow_combo.setCurrentIndex(index)


def complete_scene_inspection(window: MainWindow, inspection: InputInspection) -> None:
    controller = window._inspection_controller
    controller._on_scene_completed(controller._request_id, inspection)
