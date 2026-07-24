"""GUI application entry point."""

import sys

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from usd_optimize_app.gui.icon import create_app_icon
from usd_optimize_app.gui.main_window import MainWindow


def main(argv: list[str] | None = None) -> int:
    """Launch the PySide6 GUI.

    Args:
        argv: Optional process arguments. Uses ``sys.argv`` when omitted.

    Returns:
        Process exit code.
    """
    application_args = list(sys.argv if argv is None else argv)
    startup_smoke_test = "--startup-smoke-test" in application_args
    if startup_smoke_test:
        application_args.remove("--startup-smoke-test")

    app = QApplication(application_args)
    app.setApplicationName("USD Optimize Tool")
    app.setWindowIcon(create_app_icon())
    app.setStyle("Fusion")
    window = MainWindow(restore_session=not startup_smoke_test)
    window.setMinimumSize(960, 680)
    window.resize(1180, 820)
    window.show()
    if startup_smoke_test:
        QTimer.singleShot(0, window.close)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
