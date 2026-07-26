from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication

from usd_optimize_app.gui.main_window import MainWindow
from usd_optimize_app.gui.preferences import GuiPreferences
from usd_optimize_app.models import EnvironmentStatus


@pytest.fixture(scope="session")
def qt_application() -> QApplication:
    application = QApplication.instance() or QApplication([])
    application.setStyle("Fusion")
    return application


@pytest.fixture
def window(qt_application: QApplication, monkeypatch, tmp_path) -> MainWindow:
    del qt_application
    settings = QSettings(str(tmp_path / "preferences.ini"), QSettings.Format.IniFormat)
    preferences = GuiPreferences(settings)
    environment_status = EnvironmentStatus(
        runtime_root=None,
        required_python=None,
        current_python="3.12",
        has_python_dir=False,
        has_usdpy_dir=False,
        has_lib_dir=False,
        has_extra_libs_dir=False,
        pxr_import_ok=False,
        usd_optimize_import_ok=False,
        operation_count=0,
        errors=("Runtime unavailable for test.",),
    )
    created_window = MainWindow(
        preferences=preferences,
        environment_status_provider=lambda: environment_status,
    )
    yield created_window
    created_window.close()
