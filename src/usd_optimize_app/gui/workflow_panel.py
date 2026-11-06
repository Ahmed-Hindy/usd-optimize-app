"""Input and workflow controls for the USD Optimize desktop interface."""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from usd_optimize_app.gui.theme import JOB_STATE_STYLE_BY_KIND, STATUS_COLOR_BY_KIND
from usd_optimize_app.gui.widgets import NoWheelComboBox

FILE_DIALOG_FILTER = "USD Files (*.usd *.usda *.usdc);;All Files (*)"


@dataclass(frozen=True)
class WorkflowFormState:
    """The visible workflow-form state supplied by the coordinator."""

    input_message: str = ""
    input_kind: str = "neutral"
    run_enabled: bool = False
    running: bool = False
    job_label: str = ""
    job_kind: str = "running"


class WorkflowPanel(QFrame):
    """Own the source, workflow, output, and execution controls."""

    input_edited = Signal()
    input_committed = Signal(bool)
    output_changed = Signal(str)
    workflow_changed = Signal()
    run_requested = Signal()
    cancel_requested = Signal()
    open_output_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Card")
        self._build_widgets()
        self._build_layout()
        self._connect_signals()

    @property
    def input_path(self) -> str:
        """Return the current source path."""
        return self.input_edit.text().strip()

    @property
    def output_path(self) -> str:
        """Return the current output path."""
        return self.output_edit.text().strip()

    @property
    def workflow_name(self) -> str | None:
        """Return the selected workflow identifier."""
        value = self.workflow_combo.currentData(Qt.ItemDataRole.UserRole)
        return value if isinstance(value, str) else None

    def set_workflows(self, workflows: list[tuple[str, str]]) -> None:
        """Populate workflow choices as display-name/identifier pairs."""
        self.workflow_combo.blockSignals(True)
        self.workflow_combo.clear()
        for display_name, name in workflows:
            self.workflow_combo.addItem(display_name, name)
        default_index = self.workflow_combo.findData("safe_publish")
        self.workflow_combo.setCurrentIndex(default_index if default_index >= 0 else 0)
        self.workflow_combo.blockSignals(False)

    def set_input_path(self, path: str) -> None:
        """Set the visible source path without emitting a user edit."""
        self.input_edit.setText(path)

    def set_output_path(self, path: str) -> None:
        """Set the visible output path without treating it as manual input."""
        signals_were_blocked = self.output_edit.blockSignals(True)
        self.output_edit.setText(path)
        self.output_edit.blockSignals(signals_were_blocked)

    def set_workflow_details(
        self,
        *,
        description: str,
        operations: list[tuple[str, str]],
        is_diagnostic: bool,
    ) -> None:
        """Render the selected workflow's description and operations."""
        self.description_label.setText(description)
        self.operation_list.clear()
        for label, tooltip in operations:
            item = QListWidgetItem(label)
            item.setToolTip(tooltip)
            item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            if "skipped for selected scope" in label:
                item.setForeground(QColor(STATUS_COLOR_BY_KIND["warning"]))
            self.operation_list.addItem(item)
        self._sync_operation_list_height()
        enabled = not is_diagnostic and not self._running
        self.output_edit.setEnabled(enabled)
        self.output_edit.setPlaceholderText(
            "Not used for diagnostic workflows"
            if is_diagnostic
            else "Output path is based on the source file"
        )
        self.output_edit.setToolTip(
            "Diagnostic workflows analyze the stage without writing an output USD file."
            if is_diagnostic
            else "Destination path for the optimized USD file."
        )
        self.output_browse_button.setEnabled(enabled)
        self.open_output_button.setEnabled(enabled)

    def set_form_state(self, state: WorkflowFormState) -> None:
        """Render input readiness and the run/cancel control state."""
        self._running = state.running
        is_success = state.input_kind == "success"
        show_inline_state = not is_success and bool(state.input_message)
        self.input_state_label.setVisible(show_inline_state)
        self.input_state_label.setText(f"● {state.input_message}" if show_inline_state else "")
        self.input_state_label.setToolTip(state.input_message)
        color = STATUS_COLOR_BY_KIND.get(state.input_kind, STATUS_COLOR_BY_KIND["neutral"])
        self.input_state_label.setStyleSheet(f"color: {color};")

        self.run_button.setText("Cancel workflow" if state.running else "Run workflow")
        self.run_button.setToolTip(
            "Cancel the active workflow (Esc)"
            if state.running
            else "Run the selected workflow (Ctrl+Enter)"
        )
        self.run_button.setDefault(not state.running)
        self.run_button.setEnabled(state.running or state.run_enabled)
        self.job_progress.setVisible(state.running)
        if state.running:
            self.job_progress.setRange(0, 0)
        self.job_state_label.setVisible(bool(state.job_label))
        self.job_state_label.setText(state.job_label)
        self.job_state_label.setStyleSheet(
            JOB_STATE_STYLE_BY_KIND.get(state.job_kind, JOB_STATE_STYLE_BY_KIND["running"])
        )

        for control in self._job_defining_controls():
            control.setEnabled(not state.running)

    def set_cancelling(self) -> None:
        """Show the non-interactive cancellation transition."""
        self.run_button.setText("Cancelling…")
        self.run_button.setEnabled(False)
        self.job_state_label.setVisible(True)
        self.job_state_label.setText("Cancelling…")

    def set_elapsed_seconds(self, seconds: int) -> None:
        """Refresh the active-job elapsed-time label."""
        if self._running:
            self.job_state_label.setText(f"Running · {seconds}s")

    def _build_widgets(self) -> None:
        self._running = False
        self.input_edit = QLineEdit()
        self.input_edit.setPlaceholderText("Choose a USD file or drop it here")
        self.input_edit.setToolTip(
            "Enter or drop a local .usd, .usda, or .usdc path, then press Enter."
        )
        self.output_edit = QLineEdit()
        self.output_edit.setPlaceholderText("Output path is based on the source file")
        self.output_edit.setToolTip("Destination path for the optimized USD file.")
        self.workflow_combo = NoWheelComboBox()
        self.workflow_combo.setToolTip("Choose an optimization or diagnostic workflow.")
        self._configure_expanding_combo(self.workflow_combo)
        self.description_label = self._wrapped_label()
        self.description_label.setObjectName("SectionHint")
        self.operation_list = QListWidget()
        self.operation_list.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        self.operation_list.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.operation_list.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.operation_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.operation_list.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        self.input_state_label = self._wrapped_label("")
        self.input_state_label.setObjectName("InlineState")
        self.input_state_label.setVisible(False)
        self.input_browse_button = QPushButton("Browse")
        self.input_browse_button.setToolTip("Browse for a source USD file (Ctrl+O)")
        self.input_browse_button.setMaximumWidth(100)
        self.output_browse_button = QPushButton("Browse")
        self.output_browse_button.setToolTip("Choose output USD file path")
        self.output_browse_button.setMaximumWidth(100)
        self.open_output_button = QToolButton()
        self.open_output_button.setObjectName("OpenOutputButton")
        self.open_output_button.setToolTip("Open output folder")
        self.open_output_button.setAccessibleName("Open output folder")
        self.open_output_button.setFixedSize(34, 34)
        self.run_button = QPushButton("Run workflow")
        self.run_button.setObjectName("PrimaryButton")
        self.run_button.setToolTip("Run the selected workflow (Ctrl+Enter)")
        self.run_button.setDefault(True)
        self.run_button.setMinimumSize(132, 34)
        self.job_state_label = QLabel()
        self.job_state_label.setVisible(False)
        self.job_progress = QProgressBar()
        self.job_progress.setVisible(False)

    def _build_layout(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(16)
        layout.addLayout(
            self._section_heading(
                "Create an optimized USD copy",
                "Choose a USD file, then select an operation.",
            )
        )
        form = QFormLayout()
        self.form_layout = form
        form.setContentsMargins(0, 0, 0, 0)
        form.setHorizontalSpacing(14)
        form.setVerticalSpacing(14)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)

        input_stack = QVBoxLayout()
        input_stack.setContentsMargins(0, 0, 0, 0)
        input_stack.setSpacing(4)
        input_row = QHBoxLayout()
        input_row.setSpacing(8)
        input_row.addWidget(self.input_edit)
        input_row.addWidget(self.input_browse_button)
        input_stack.addLayout(input_row)
        input_stack.addWidget(self.input_state_label)

        self.workflow_field_widget = QWidget()
        workflow_stack = QVBoxLayout(self.workflow_field_widget)
        workflow_stack.setContentsMargins(0, 0, 0, 0)
        workflow_stack.setSpacing(6)
        workflow_stack.addWidget(self.workflow_combo)
        workflow_stack.addWidget(self.description_label)

        output_row = QHBoxLayout()
        output_row.setSpacing(8)
        self.output_row = output_row
        output_row.addWidget(self.output_edit)
        output_row.addWidget(self.output_browse_button)
        output_row.addWidget(self.open_output_button)

        form.addRow(self._field_label("SOURCE USD"), input_stack)
        form.addRow(self._field_label("WORKFLOW"), self.workflow_field_widget)
        form.addRow(self._field_label("OUTPUT USD"), output_row)
        layout.addLayout(form)

        steps_stack = QVBoxLayout()
        steps_stack.setContentsMargins(0, 2, 0, 0)
        steps_stack.setSpacing(6)
        operations_label = QLabel("WORKFLOW STEPS")
        operations_label.setObjectName("StatusCaption")
        operations_label.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed
        )
        steps_stack.addWidget(operations_label)
        steps_stack.addWidget(self.operation_list)
        layout.addLayout(steps_stack)

        layout.addStretch(1)

        footer_stack = QVBoxLayout()
        footer_stack.setContentsMargins(0, 0, 0, 0)
        footer_stack.setSpacing(10)
        footer_rule = QFrame()
        footer_rule.setObjectName("SectionRule")
        footer_rule.setFrameShape(QFrame.Shape.HLine)
        footer_rule.setFrameShadow(QFrame.Shadow.Plain)
        footer_stack.addWidget(footer_rule)
        footer_stack.addWidget(self.job_progress)
        button_row = QHBoxLayout()
        button_row.setContentsMargins(0, 0, 0, 0)
        button_row.addWidget(self.job_state_label)
        button_row.addStretch(1)
        button_row.addWidget(self.run_button)
        footer_stack.addLayout(button_row)
        layout.addLayout(footer_stack)

    def _sync_operation_list_height(self) -> None:
        count = max(self.operation_list.count(), 1)
        row_height = self.operation_list.sizeHintForRow(0)
        if row_height <= 0:
            row_height = 33
        frame = self.operation_list.frameWidth() * 2
        target_height = min(max(count * row_height + frame + 2, 35), 200)
        self.operation_list.setFixedHeight(target_height)

    def _connect_signals(self) -> None:
        self.input_edit.textEdited.connect(self.input_edited)
        self.input_edit.returnPressed.connect(lambda: self.input_committed.emit(True))
        self.input_edit.editingFinished.connect(lambda: self.input_committed.emit(False))
        self.output_edit.textChanged.connect(self.output_changed)
        self.workflow_combo.currentIndexChanged.connect(self.workflow_changed)
        self.input_browse_button.clicked.connect(self._browse_input)
        self.output_browse_button.clicked.connect(self._browse_output)
        self.run_button.clicked.connect(self._on_action_button_clicked)
        self.open_output_button.clicked.connect(self.open_output_requested)
        QShortcut(QKeySequence.StandardKey.Open, self, activated=self._browse_input)
        QShortcut(QKeySequence("Ctrl+Return"), self, activated=self._activate_run_shortcut)

    def _browse_input(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(self, "Choose USD file", "", FILE_DIALOG_FILTER)
        if file_path:
            self.input_edit.setText(file_path)
            self.input_committed.emit(False)

    def _browse_output(self) -> None:
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Choose output USD file", "", FILE_DIALOG_FILTER
        )
        if file_path:
            self.output_edit.setText(file_path)

    def _activate_run_shortcut(self) -> None:
        if not self._running:
            self.run_button.click()

    def _on_action_button_clicked(self) -> None:
        if self._running:
            self.cancel_requested.emit()
        else:
            self.run_requested.emit()

    def _job_defining_controls(self) -> tuple[QWidget, ...]:
        return (
            self.input_edit,
            self.input_browse_button,
            self.output_edit,
            self.output_browse_button,
            self.workflow_combo,
            self.operation_list,
            self.open_output_button,
        )

    @staticmethod
    def _configure_expanding_combo(combo: QComboBox) -> None:
        combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        combo.setMinimumContentsLength(16)
        combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    @staticmethod
    def _wrapped_label(text: str = "") -> QLabel:
        label = QLabel(text)
        label.setWordWrap(True)
        label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Maximum)
        return label

    @staticmethod
    def _field_label(text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("FieldLabel")
        label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        return label

    @staticmethod
    def _section_heading(title: str, hint: str) -> QVBoxLayout:
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        title_label = QLabel(title)
        title_label.setObjectName("SectionTitle")
        title_label.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        hint_label = QLabel(hint)
        hint_label.setObjectName("SectionHint")
        hint_label.setWordWrap(True)
        hint_label.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        layout.addWidget(title_label)
        layout.addWidget(hint_label)
        layout.addSpacing(4)
        rule = QFrame()
        rule.setObjectName("SectionRule")
        rule.setFrameShape(QFrame.Shape.HLine)
        rule.setFrameShadow(QFrame.Shadow.Plain)
        layout.addWidget(rule)
        return layout

