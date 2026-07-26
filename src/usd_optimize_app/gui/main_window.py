"""Application shell for the USD Optimize desktop interface."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QMainWindow,
    QMessageBox,
    QSizePolicy,
    QSplitter,
    QStackedLayout,
    QStyle,
    QVBoxLayout,
    QWidget,
)

from usd_optimize_app.backend import get_environment_status
from usd_optimize_app.constants import SUPPORTED_USD_EXTENSIONS
from usd_optimize_app.gui.preferences import GuiPreferences
from usd_optimize_app.gui.results_panel import ResultsPanel
from usd_optimize_app.gui.theme import APP_STYLE, STATUS_COLOR_BY_KIND
from usd_optimize_app.gui.workflow_controller import WorkflowController
from usd_optimize_app.gui.workflow_panel import WorkflowPanel
from usd_optimize_app.models import OptimizeResult
from usd_optimize_app.package_info import installed_version


class MainWindow(QMainWindow):
    """Compose the application shell, form, results workspace, and controller."""

    def __init__(
        self,
        *,
        restore_session: bool = True,
        preferences: GuiPreferences | None = None,
        environment_status_provider=None,
    ) -> None:
        """Initialize the application window.

        Args:
            restore_session: Restore the last committed source and output paths when true.
        """
        super().__init__()
        self.setWindowTitle(f"USD Optimize Tool -- {installed_version()}")
        self.setProperty("theme", "dark")
        self.setAcceptDrops(True)
        self.setStyleSheet(APP_STYLE)
        self._build_shell()
        self._controller = WorkflowController(
            self._workflow_panel,
            self._results_panel,
            preferences=preferences,
            environment_status_provider=environment_status_provider or get_environment_status,
            confirm_replacement=self._ask_confirmation,
            show_error=self._show_error,
            show_completion=self._show_conversion_complete,
            parent=self,
        )
        self._controller.status_changed.connect(self._set_status)
        self._controller.runtime_changed.connect(self._set_runtime_state)
        QShortcut(QKeySequence("Escape"), self, activated=self._controller.cancel_job)
        self._controller.start(restore_session=restore_session)

    def _build_shell(self) -> None:
        self._workflow_panel = WorkflowPanel()
        self._workflow_panel.open_output_button.setIcon(
            self.style().standardIcon(QStyle.StandardPixmap.SP_DirOpenIcon)
        )
        self._results_panel = ResultsPanel()
        self._workspace_splitter = QSplitter(Qt.Orientation.Horizontal)
        self._workspace_splitter.setChildrenCollapsible(False)
        self._workspace_splitter.addWidget(self._workflow_panel)
        self._workspace_splitter.addWidget(self._results_panel)
        self._workspace_splitter.setStretchFactor(0, 10)
        self._workspace_splitter.setStretchFactor(1, 10)
        self._workspace_splitter.setSizes([590, 530])

        self._runtime_blocker_title = QLabel("USD Optimize runtime is unavailable")
        self._runtime_blocker_title.setObjectName("RuntimeBlockerTitle")
        self._runtime_blocker_detail = QLabel()
        self._runtime_blocker_detail.setObjectName("RuntimeBlockerDetail")
        self._runtime_blocker_detail.setWordWrap(True)
        self._runtime_blocker = self._build_runtime_blocker()
        self._content_stack = QStackedLayout()
        self._content_stack.addWidget(self._workspace_splitter)
        self._content_stack.addWidget(self._runtime_blocker)

        central_widget = QWidget()
        root_layout = QVBoxLayout(central_widget)
        root_layout.setContentsMargins(18, 18, 18, 16)
        root_layout.setSpacing(12)
        root_layout.addLayout(self._content_stack, stretch=1)
        self.setCentralWidget(central_widget)

        self._status_message_label = QLabel()
        self._status_message_label.setObjectName("StatusMessage")
        self._status_message_label.setMinimumWidth(0)
        self._status_message_label.setSizePolicy(
            QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed
        )
        self._runtime_badge = QLabel()
        self._runtime_badge.setObjectName("BadgeReady")
        status_bar = self.statusBar()
        status_bar.setSizeGripEnabled(False)
        status_bar.addWidget(self._status_message_label, 1)
        status_bar.addPermanentWidget(self._runtime_badge)

    def _build_runtime_blocker(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("RuntimeBlocker")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(8)
        layout.addStretch(1)
        layout.addWidget(self._runtime_blocker_title)
        layout.addWidget(self._runtime_blocker_detail)
        layout.addStretch(1)
        return panel

    def _set_runtime_state(self, usable: bool, details: str) -> None:
        if usable:
            self._runtime_badge.setText("RUNTIME READY")
            self._runtime_badge.setToolTip(details)
            self._runtime_badge.setObjectName("BadgeReady")
            self._workspace_splitter.setEnabled(True)
            self._content_stack.setCurrentWidget(self._workspace_splitter)
            self.statusBar().setVisible(True)
        else:
            self._runtime_badge.setText("RUNTIME UNAVAILABLE")
            self._runtime_badge.setToolTip(details)
            self._runtime_badge.setObjectName("BadgeError")
            self._runtime_blocker_detail.setText(
                f"{details}\n\n"
                "Extract or reinstall the portable USD Optimize package, then reopen the app."
            )
            self._workspace_splitter.setEnabled(False)
            self._content_stack.setCurrentWidget(self._runtime_blocker)
            self.statusBar().setVisible(False)
        self._runtime_badge.setStyleSheet("")
        style = self._runtime_badge.style()
        style.unpolish(self._runtime_badge)
        style.polish(self._runtime_badge)

    def _set_status(self, message: str, kind: str) -> None:
        color = STATUS_COLOR_BY_KIND.get(kind, STATUS_COLOR_BY_KIND["neutral"])
        self._status_message_label.setText(f"● {message}")
        self._status_message_label.setToolTip(message)
        self._status_message_label.setStyleSheet(f"color: {color};")

    def _ask_confirmation(self, title: str, message: str) -> bool:
        answer = QMessageBox.question(
            self,
            title,
            message,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        return answer == QMessageBox.StandardButton.Yes

    def _show_error(self, message: str) -> None:
        QMessageBox.critical(self, "USD Optimize App", message)

    def _show_conversion_complete(self, result: OptimizeResult) -> None:
        QMessageBox.information(
            self,
            "Conversion complete",
            "New USD Scene saved to:\n\n"
            f"'{result.output_path}'\n\n"
            f"Completed in {result.duration_seconds:.1f}s.",
        )

    def dragEnterEvent(self, event) -> None:  # noqa: N802
        """Accept a local USD file dropped anywhere on the application shell."""
        if any(
            url.isLocalFile() and Path(url.toLocalFile()).suffix.lower() in SUPPORTED_USD_EXTENSIONS
            for url in event.mimeData().urls()
        ):
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:  # noqa: N802
        """Commit the first supported local USD file dropped on the shell."""
        for url in event.mimeData().urls():
            if not url.isLocalFile():
                continue
            input_path = Path(url.toLocalFile())
            if input_path.suffix.lower() not in SUPPORTED_USD_EXTENSIONS:
                continue
            self._workflow_panel.set_input_path(str(input_path))
            self._controller.commit_input(False)
            event.acceptProposedAction()
            return

    def closeEvent(self, event) -> None:  # noqa: N802
        """Wait for controller-owned workers before Qt destroys widgets."""
        if self._controller.shutdown():
            event.accept()
        else:
            event.ignore()
