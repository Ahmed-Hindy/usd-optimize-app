"""GUI entry-point tests."""

from __future__ import annotations

import os
import subprocess
import sys


def test_gui_modules_import() -> None:
    """Import the Qt window and worker modules."""
    from usd_optimize_app.gui.job_worker import OptimizeJobThread
    from usd_optimize_app.gui.main_window import MainWindow

    assert MainWindow is not None
    assert OptimizeJobThread is not None


def test_app_icon_contains_common_sizes(monkeypatch) -> None:
    """Build non-empty pixmaps for common Windows icon sizes."""
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    from PySide6.QtWidgets import QApplication

    from usd_optimize_app.gui.icon import create_app_icon

    app = QApplication.instance() or QApplication([])
    icon = create_app_icon()

    assert app is not None
    assert not icon.isNull()
    for size in (16, 32, 256):
        assert not icon.pixmap(size, size).isNull()


def test_gui_module_entry_point_starts_and_exits() -> None:
    """Run the same module entry point used by the portable GUI launcher."""
    environment = os.environ.copy()
    environment["QT_QPA_PLATFORM"] = "offscreen"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "usd_optimize_app.gui.app",
            "--startup-smoke-test",
        ],
        check=False,
        capture_output=True,
        env=environment,
        text=True,
        timeout=15,
    )

    assert result.returncode == 0, result.stderr
