"""Application shell for the USD Optimize desktop interface."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSplitter,
    QStackedLayout,
    QVBoxLayout,
    QWidget,
)

from usd_optimize_app.backend import get_environment_status
from usd_optimize_app.constants import SUPPORTED_USD_EXTENSIONS
from usd_optimize_app.gui.icon import create_folder_icon
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
        self._runtime_retry_button.clicked.connect(self._controller.refresh_environment_status)
        QShortcut(QKeySequence("Escape"), self, activated=self._controller.cancel_job)
        self._controller.start(restore_session=restore_session)

    def _build_shell(self) -> None:
        self._workflow_panel = WorkflowPanel()
        self._workflow_panel.open_output_button.setIcon(create_folder_icon())
        self._results_panel = ResultsPanel()
        self._workspace_splitter = QSplitter(Qt.Orientation.Horizontal)
        self._workspace_splitter.setChildrenCollapsible(False)
        self._workspace_splitter.addWidget(self._workflow_panel)
        self._workspace_splitter.addWidget(self._results_panel)
        self._workspace_splitter.setStretchFactor(0, 11)
        self._workspace_splitter.setStretchFactor(1, 9)
        self._workspace_splitter.setSizes([590, 490])

        self._runtime_blocker_title = QLabel("USD Optimize runtime is unavailable")
        self._runtime_blocker_title.setObjectName("RuntimeBlockerTitle")
        self._runtime_blocker_detail = QLabel()
        self._runtime_blocker_detail.setObjectName("RuntimeBlockerDetail")
        self._runtime_blocker_detail.setWordWrap(True)
        self._runtime_retry_button = QPushButton("Retry runtime check")
        self._runtime_retry_button.setToolTip("Re-check the portable USD Optimize runtime")
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
        status_bar = self.statusBar()
        status_bar.setSizeGripEnabled(False)
        status_bar.addWidget(self._status_message_label, 1)

    def _build_runtime_blocker(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("RuntimeBlocker")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(48, 40, 48, 40)
        layout.setSpacing(12)
        layout.addStretch(1)
        caption = QLabel("ENVIRONMENT CHECK")
        caption.setObjectName("StatusCaption")
        layout.addWidget(caption)
        layout.addWidget(self._runtime_blocker_title)
        layout.addWidget(self._runtime_blocker_detail)
        retry_row = QHBoxLayout()
        retry_row.setContentsMargins(0, 8, 0, 0)
        retry_row.addWidget(self._runtime_retry_button)
        retry_row.addStretch(1)
        layout.addLayout(retry_row)
        layout.addStretch(1)
        return panel

    def _set_runtime_state(self, usable: bool, details: str) -> None:
        if usable:
            self._workspace_splitter.setEnabled(True)
            self._content_stack.setCurrentWidget(self._workspace_splitter)
            self.statusBar().setVisible(True)
        else:
            self._runtime_blocker_detail.setText(
                f"{details}\n\n"
                "Extract or reinstall the portable USD Optimize package, "
                "then click Retry runtime check."
            )
            self._workspace_splitter.setEnabled(False)
            self._content_stack.setCurrentWidget(self._runtime_blocker)
            self.statusBar().setVisible(False)

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

    def _set_drag_active(self, active: bool) -> None:
        self._workflow_panel.setProperty("dragActive", active)
        self._workflow_panel.style().unpolish(self._workflow_panel)
        self._workflow_panel.style().polish(self._workflow_panel)

    def dragEnterEvent(self, event) -> None:  # noqa: N802
        """Accept a local USD file dropped anywhere on the application shell."""
        if any(
            url.isLocalFile() and Path(url.toLocalFile()).suffix.lower() in SUPPORTED_USD_EXTENSIONS
            for url in event.mimeData().urls()
        ):
            self._set_drag_active(True)
            event.acceptProposedAction()

    def dragLeaveEvent(self, event) -> None:  # noqa: N802
        """Clear drag highlight when a dragged file leaves the window."""
        self._set_drag_active(False)
        super().dragLeaveEvent(event)

    def dropEvent(self, event) -> None:  # noqa: N802
        """Commit the first supported local USD file dropped on the shell."""
        self._set_drag_active(False)
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
