"""Main PySide6 window for USD Optimize App."""

from __future__ import annotations

from pathlib import Path
from time import monotonic

from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtGui import QDesktopServices, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QSplitter,
    QStackedLayout,
    QStyle,
    QTableWidget,
    QTabWidget,
    QToolButton,
    QTreeWidget,
    QVBoxLayout,
    QWidget,
)

from usd_optimize_app.backend import (
    InputInspection,
    OptimizeJobSettings,
    PresetView,
    get_environment_status,
    get_gui_workflows,
    resolve_default_output_path,
)
from usd_optimize_app.constants import SUPPORTED_USD_EXTENSIONS
from usd_optimize_app.diagnostics import parse_stage_metrics, parse_stage_stats
from usd_optimize_app.gui.analysis_view import format_analysis_results
from usd_optimize_app.gui.job_worker import OptimizeJobThread
from usd_optimize_app.gui.log_view import append_log_text, configure_log_view
from usd_optimize_app.gui.preferences import GuiPreferences
from usd_optimize_app.gui.report_views import populate_diagnostics_table
from usd_optimize_app.gui.scene_graph_view import (
    configure_scene_tree,
    populate_scene_tree,
    selected_prim_paths,
)
from usd_optimize_app.gui.stage_inspection import StageInspectionController
from usd_optimize_app.gui.theme import (
    APP_STYLE,
    JOB_STATE_STYLE_BY_KIND,
    STATUS_COLOR_BY_KIND,
)
from usd_optimize_app.gui.widgets import NoWheelComboBox
from usd_optimize_app.models import OptimizeResult
from usd_optimize_app.operation_scope import scoped_operation_skip_reason
from usd_optimize_app.operations import get_operation_presentation
from usd_optimize_app.package_info import installed_version

FILE_DIALOG_FILTER = "USD Files (*.usd *.usda *.usdc);;All Files (*)"
THREAD_SHUTDOWN_TIMEOUT_MS = 5_000


class MainWindow(QMainWindow):
    """Desktop interface for USD cleanup, analysis, and automatic diagnostics."""

    def __init__(self, *, restore_session: bool = True) -> None:
        """Initialize the main window.

        Args:
            restore_session: Restore the last input and output paths when true.
        """
        super().__init__()
        self._restore_session = restore_session
        self._configure_window()
        self._initialize_state()
        self._create_widgets()
        self._build_ui()
        self._initialize_content()

    def _configure_window(self) -> None:
        self.setWindowTitle(f"USD Optimize Tool -- {installed_version()}")
        self.setProperty("theme", "dark")
        self.setAcceptDrops(True)
        self.setStyleSheet(APP_STYLE)

    def _initialize_state(self) -> None:
        self._preferences = GuiPreferences()
        self._presets = get_gui_workflows()
        self._active_job: OptimizeJobThread | None = None
        self._environment_usable = False
        self._status_generation = 0
        self._inspection_controller = StageInspectionController(self)
        self._inspection_controller.scene_completed.connect(self._on_input_inspected)
        self._inspection_controller.diagnostics_completed.connect(
            self._on_input_diagnostics_completed
        )
        self._inspection_controller.diagnostics_failed.connect(self._on_input_diagnostics_failed)
        self._input_dirty = False
        self._last_inspected_input = ""
        self._output_is_auto_generated = True
        self._setting_auto_output = False
        self._run_started_at: float | None = None
        self._job_outcome: tuple[str, str] | None = None

    def _create_widgets(self) -> None:
        self._input_edit = QLineEdit()
        self._input_edit.setPlaceholderText("Choose a USD file")
        self._input_edit.setToolTip("Enter a local .usd, .usda, or .usdc path.")
        self._output_edit = QLineEdit()
        self._output_edit.setPlaceholderText("A separate optimized copy is suggested automatically")
        self._workflow_combo = NoWheelComboBox()
        self._configure_expanding_combo(self._workflow_combo)
        self._description_label = self._create_wrapped_label()
        self._description_label.setObjectName("SectionHint")
        self._operation_list = QListWidget()
        self._operation_list.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        self._operation_list.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._operation_list.setMinimumHeight(104)
        self._operation_list.setMaximumHeight(180)
        self._input_state_label = self._create_wrapped_label(
            "Choose a USD file to inspect the stage."
        )
        self._scene_summary_label = self._create_wrapped_label(
            "Choose an input USD to inspect its hierarchy."
        )
        self._scene_summary_label.setObjectName("SectionHint")
        self._scene_scope_label = self._create_wrapped_label(
            "Scope: Entire stage · select one or more prims to limit the workflow."
        )
        self._scene_scope_label.setObjectName("SectionHint")
        self._clear_scope_button = QPushButton("Clear selection")
        self._clear_scope_button.setEnabled(False)
        self._clear_scope_button.clicked.connect(self._scene_tree_clear_selection)
        self._scene_tree = QTreeWidget()
        configure_scene_tree(self._scene_tree)
        self._scene_tree.itemSelectionChanged.connect(self._update_scene_scope)
        self._log_edit = self._create_read_only_text("Run a workflow to see worker messages.")
        configure_log_view(self._log_edit)
        self._analysis_edit = self._create_read_only_text(
            "Run Find Overlaps to see structured findings."
        )
        self._diagnostics_summary_label = self._create_wrapped_label(
            "Choose an input USD to inspect stage statistics."
        )
        self._diagnostics_summary_label.setObjectName("SectionHint")
        self._diagnostic_table = QTableWidget(0, 4)
        self._status_message_label = QLabel()
        self._status_message_label.setObjectName("StatusMessage")
        self._status_message_label.setMinimumWidth(0)
        self._status_message_label.setSizePolicy(
            QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed
        )
        self._run_button = QPushButton("Run workflow")
        self._run_button.setObjectName("PrimaryButton")
        self._run_button.setDefault(True)
        self._run_button.setMinimumSize(120, 34)
        self._open_output_button = QToolButton()
        self._open_output_button.setObjectName("OpenOutputButton")
        self._open_output_button.setIcon(
            self.style().standardIcon(QStyle.StandardPixmap.SP_DirOpenIcon)
        )
        self._open_output_button.setToolTip("Open output folder")
        self._open_output_button.setAccessibleName("Open output folder")
        self._open_output_button.setFixedSize(34, 34)
        self._job_state_label = QLabel()
        self._job_state_label.setVisible(False)
        self._runtime_badge = QLabel()
        self._runtime_blocker_title = QLabel("USD Optimize runtime is unavailable")
        self._runtime_blocker_title.setObjectName("RuntimeBlockerTitle")
        self._runtime_blocker_detail = self._create_wrapped_label()
        self._runtime_blocker_detail.setObjectName("RuntimeBlockerDetail")
        self._job_progress = QProgressBar()
        self._job_progress.setVisible(False)
        self._elapsed_timer = QTimer(self)
        self._elapsed_timer.setInterval(1000)
        self._elapsed_timer.timeout.connect(self._update_elapsed_status)
        self._tabs = QTabWidget()

    @staticmethod
    def _configure_expanding_combo(combo: QComboBox) -> None:
        combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        combo.setMinimumContentsLength(16)
        combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    @staticmethod
    def _create_wrapped_label(text: str = "") -> QLabel:
        label = QLabel(text)
        label.setWordWrap(True)
        label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        return label

    @staticmethod
    def _create_read_only_text(placeholder: str) -> QPlainTextEdit:
        text_edit = QPlainTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setPlaceholderText(placeholder)
        return text_edit

    def _initialize_content(self) -> None:
        self._setup_shortcuts()
        self._populate_workflows()
        if self._restore_session:
            self._load_saved_paths()
        self._refresh_environment_status()
        self._update_run_readiness()

    def _build_ui(self) -> None:
        central_widget = QWidget()
        root_layout = QVBoxLayout(central_widget)
        root_layout.setContentsMargins(18, 18, 18, 16)
        root_layout.setSpacing(12)

        self._workspace_splitter = QSplitter(Qt.Orientation.Horizontal)
        self._workspace_splitter.setChildrenCollapsible(False)
        self._workspace_splitter.addWidget(self._build_workflow_panel())
        self._workspace_splitter.addWidget(self._build_results_panel())
        self._workspace_splitter.setStretchFactor(0, 10)
        self._workspace_splitter.setStretchFactor(1, 10)
        self._workspace_splitter.setSizes([590, 530])

        self._runtime_blocker = self._build_runtime_blocker()
        self._content_stack = QStackedLayout()
        self._content_stack.addWidget(self._workspace_splitter)
        self._content_stack.addWidget(self._runtime_blocker)
        root_layout.addLayout(self._content_stack, stretch=1)

        self.setCentralWidget(central_widget)
        self._build_status_bar()

    def _build_runtime_blocker(self) -> QFrame:
        """Build the sole failure surface for an unavailable packaged runtime."""
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

    def _build_status_bar(self) -> None:
        status_bar = self.statusBar()
        status_bar.setSizeGripEnabled(False)
        status_bar.addWidget(self._status_message_label, 1)
        self._runtime_badge.setObjectName("BadgeReady")
        status_bar.addPermanentWidget(self._runtime_badge)

    def _build_workflow_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("Card")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(16, 15, 16, 16)
        layout.setSpacing(14)
        layout.addLayout(
            self._build_section_heading(
                "Build a clean derivative",
                "Select a stage and run one of the reviewed USD workflows.",
            )
        )
        layout.addWidget(self._build_file_group())
        layout.addWidget(self._build_workflow_group(), stretch=1)
        return panel

    @staticmethod
    def _build_section_heading(title: str, hint: str) -> QVBoxLayout:
        layout = QVBoxLayout()
        layout.setSpacing(4)
        title_label = QLabel(title)
        title_label.setObjectName("SectionTitle")
        hint_label = QLabel(hint)
        hint_label.setObjectName("SectionHint")
        hint_label.setWordWrap(True)
        hint_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        layout.addWidget(title_label)
        layout.addWidget(hint_label)
        rule = QFrame()
        rule.setObjectName("SectionRule")
        rule.setFrameShape(QFrame.Shape.HLine)
        rule.setFrameShadow(QFrame.Shadow.Plain)
        layout.addWidget(rule)
        return layout

    @staticmethod
    def _create_field_label(text: str) -> QLabel:
        """Create a compact label for one stage-workflow field."""
        label = QLabel(text)
        label.setObjectName("FieldLabel")
        return label

    def _build_file_group(self) -> QFrame:
        group = QFrame()
        layout = QFormLayout(group)
        self._file_form_layout = layout
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        layout.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)

        self._input_browse_button = QPushButton("Browse")
        self._input_browse_button.setMaximumWidth(100)
        self._input_browse_button.clicked.connect(self._browse_input)
        self._output_browse_button = QPushButton("Browse")
        self._output_browse_button.setMaximumWidth(100)
        self._output_browse_button.clicked.connect(self._browse_output)

        input_stack = QVBoxLayout()
        input_stack.setSpacing(4)
        input_row = QHBoxLayout()
        input_row.addWidget(self._input_edit)
        input_row.addWidget(self._input_browse_button)
        input_stack.addLayout(input_row)
        self._input_state_label.setObjectName("InlineState")
        input_stack.addWidget(self._input_state_label)

        self._workflow_field_widget = QWidget()
        workflow_stack = QVBoxLayout(self._workflow_field_widget)
        workflow_stack.setContentsMargins(0, 0, 0, 0)
        workflow_stack.setSpacing(5)
        workflow_stack.addWidget(self._workflow_combo)
        workflow_stack.addWidget(self._description_label)

        output_row = QHBoxLayout()
        self._output_row = output_row
        output_row.addWidget(self._output_edit)
        output_row.addWidget(self._output_browse_button)
        output_row.addWidget(self._open_output_button)

        layout.addRow(self._create_field_label("SOURCE USD"), input_stack)
        layout.addRow(self._create_field_label("WORKFLOW"), self._workflow_field_widget)
        layout.addRow(self._create_field_label("OUTPUT USD"), output_row)
        return group

    def _build_workflow_group(self) -> QFrame:
        group = QFrame()
        layout = QVBoxLayout(group)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        operations_label = QLabel("WORKFLOW STEPS")
        operations_label.setObjectName("StatusCaption")
        layout.addWidget(operations_label)
        layout.addWidget(self._operation_list)
        layout.addStretch(1)
        button_row = QHBoxLayout()
        button_row.addWidget(self._job_state_label)
        button_row.addStretch(1)
        button_row.addWidget(self._run_button)
        layout.addWidget(self._job_progress)
        layout.addLayout(button_row)

        self._run_button.clicked.connect(self._on_action_button_clicked)
        self._workflow_combo.currentIndexChanged.connect(self._on_workflow_changed)
        self._input_edit.textEdited.connect(self._on_input_text_edited)
        self._input_edit.returnPressed.connect(self._on_input_return_pressed)
        self._input_edit.editingFinished.connect(self._on_input_committed)
        self._output_edit.textChanged.connect(self._on_output_path_changed)
        return group

    def _build_results_panel(self) -> QFrame:
        group = QFrame()
        group.setObjectName("Card")
        layout = QVBoxLayout(group)
        layout.setContentsMargins(16, 15, 16, 16)
        layout.setSpacing(12)
        layout.addLayout(
            self._build_section_heading(
                "Stage inspector",
                "Check the hierarchy, diagnostics, and results without leaving the app.",
            )
        )

        self._open_output_button.clicked.connect(self._open_output_folder)

        self._scene_tab = QWidget()
        scene_layout = QVBoxLayout(self._scene_tab)
        scene_layout.setContentsMargins(0, 0, 0, 0)
        scene_layout.setSpacing(8)
        scene_layout.addWidget(self._scene_summary_label)
        scope_row = QHBoxLayout()
        scope_row.addWidget(self._scene_scope_label, stretch=1)
        scope_row.addWidget(self._clear_scope_button)
        scene_layout.addLayout(scope_row)
        scene_layout.addWidget(self._scene_tree, stretch=1)
        self._scene_tab_index = self._tabs.addTab(self._scene_tab, "Scene")

        self._diagnostics_tab = QWidget()
        diagnostics_layout = QVBoxLayout(self._diagnostics_tab)
        diagnostics_layout.setContentsMargins(0, 0, 0, 0)
        diagnostics_layout.setSpacing(8)
        diagnostics_layout.addWidget(self._diagnostics_summary_label)
        diagnostics_layout.addWidget(self._diagnostic_table, stretch=1)
        self._diagnostic_table.setHorizontalHeaderLabels(
            ("Prim type", "Count", "Inactive", "Invisible")
        )
        self._diagnostic_table.verticalHeader().setVisible(False)
        self._diagnostic_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents
        )
        self._diagnostic_table.horizontalHeader().setStretchLastSection(True)
        self._diagnostics_tab_index = self._tabs.addTab(self._diagnostics_tab, "Diagnostics")
        self._analysis_tab_index = self._tabs.addTab(self._analysis_edit, "Analysis")
        self._tabs.setTabVisible(self._analysis_tab_index, False)
        self._tabs.addTab(self._log_edit, "Log")
        layout.addWidget(self._tabs)
        return group

    def _populate_workflows(self) -> None:
        self._workflow_combo.blockSignals(True)
        self._workflow_combo.clear()
        for preset in self._presets:
            self._workflow_combo.addItem(preset.display_name, preset.name)
        default_index = self._workflow_combo.findData("safe_publish")
        self._workflow_combo.setCurrentIndex(default_index if default_index >= 0 else 0)
        self._workflow_combo.blockSignals(False)
        self._on_workflow_changed()

    def _load_saved_paths(self) -> None:
        saved_paths = self._preferences.load_paths()
        self._input_edit.setText(saved_paths.input_path)
        self._setting_auto_output = True
        self._output_edit.setText(saved_paths.output_path)
        self._setting_auto_output = False
        self._output_is_auto_generated = not saved_paths.output_path
        if saved_paths.input_path and saved_paths.output_path:
            self._output_is_auto_generated = saved_paths.output_path == str(
                resolve_default_output_path(Path(saved_paths.input_path))
            )
        if saved_paths.input_path and not saved_paths.output_path:
            self._rebuild_output_from_input()
        if saved_paths.input_path:
            self._inspect_input()

    def _refresh_environment_status(self) -> None:
        status = get_environment_status()
        self._environment_usable = status.is_usable
        if status.is_usable:
            details = f"{status.operation_count or 0} operations available"
            self._set_runtime_badge("RUNTIME READY", details, "BadgeReady")
            self._workspace_splitter.setEnabled(True)
            self._content_stack.setCurrentWidget(self._workspace_splitter)
            self.statusBar().setVisible(True)
        else:
            first_error = status.errors[0] if status.errors else "Unknown environment problem."
            self._runtime_blocker_detail.setText(
                f"{first_error}\n\n"
                "Extract or reinstall the portable USD Optimize package, then reopen the app."
            )
            self._workspace_splitter.setEnabled(False)
            self._content_stack.setCurrentWidget(self._runtime_blocker)
            self.statusBar().setVisible(False)
        self._update_run_readiness()

    def _set_runtime_badge(
        self,
        text: str,
        tooltip: str,
        object_name: str,
    ) -> None:
        self._runtime_badge.setText(text)
        self._runtime_badge.setToolTip(tooltip)
        self._runtime_badge.setObjectName(object_name)
        self._runtime_badge.setStyleSheet("")
        self._repolish_runtime_badge()

    def _repolish_runtime_badge(self) -> None:
        style = self._runtime_badge.style()
        style.unpolish(self._runtime_badge)
        style.polish(self._runtime_badge)

    def _set_status(
        self,
        message: str,
        kind: str = "neutral",
        *,
        timeout_ms: int | None = None,
    ) -> None:
        """Show one colored message in the bottom status bar."""
        self._status_generation += 1
        generation = self._status_generation
        color = STATUS_COLOR_BY_KIND.get(kind, STATUS_COLOR_BY_KIND["neutral"])
        self._status_message_label.setText(f"● {message}")
        self._status_message_label.setToolTip(message)
        self._status_message_label.setStyleSheet(f"color: {color};")
        if timeout_ms is not None:
            QTimer.singleShot(timeout_ms, lambda: self._restore_readiness_status(generation))

    def _restore_readiness_status(self, generation: int) -> None:
        if generation == self._status_generation:
            self._update_run_readiness()

    def _setup_shortcuts(self) -> None:
        QShortcut(QKeySequence.Open, self, activated=self._browse_input)
        QShortcut(QKeySequence("Ctrl+Return"), self, activated=self._activate_run_shortcut)
        QShortcut(QKeySequence("Escape"), self, activated=self._cancel_job)

    def _activate_run_shortcut(self) -> None:
        if self._active_job is None:
            self._run_button.click()

    def _on_action_button_clicked(self) -> None:
        if self._active_job is None:
            self._run_job()
            return
        self._cancel_job()

    def _browse_input(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Choose USD file",
            "",
            FILE_DIALOG_FILTER,
        )
        if file_path:
            self._input_edit.setText(file_path)
            self._on_input_committed()

    def _browse_output(self) -> None:
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Choose output USD file",
            "",
            FILE_DIALOG_FILTER,
        )
        if file_path:
            self._output_edit.setText(file_path)

    def _on_input_text_edited(self) -> None:
        """Mark typed input as pending without touching files or output state."""
        if not self._input_dirty:
            self._inspection_controller.reset()
        self._input_dirty = True
        self._run_button.setEnabled(False)
        self._input_state_label.setVisible(True)
        self._input_state_label.setText("● Press Enter or leave the field to inspect.")
        self._input_state_label.setToolTip("Input changes are applied after editing is committed.")
        self._input_state_label.setStyleSheet(f"color: {STATUS_COLOR_BY_KIND['neutral']};")
        self._clear_scene_view("Waiting for input confirmation.")
        self._clear_diagnostics_view("Waiting for input confirmation.")
        self._set_status("Input change pending", "neutral")

    def _on_input_return_pressed(self) -> None:
        self._commit_input(force=True)

    def _on_input_committed(self) -> None:
        self._commit_input(force=False)

    def _commit_input(self, *, force: bool) -> None:
        """Apply one edited input, rebuild its output, and inspect the stage."""
        input_text = self._input_edit.text().strip()
        if not force and not self._input_dirty and input_text == self._last_inspected_input:
            return
        self._rebuild_output_from_input()
        self._preferences.save_input_path(input_text)
        self._preferences.save_output_path(self._output_edit.text().strip())
        self._inspect_input()

    def _inspect_input(self) -> None:
        """Start scene hierarchy and diagnostics inspection for the selected input."""
        input_text = self._input_edit.text().strip()
        self._input_dirty = False
        self._last_inspected_input = input_text
        if not input_text:
            self._inspection_controller.reset()
            self._set_input_state("Choose a USD file to inspect the stage.", "neutral")
            self._clear_scene_view("Choose an input USD to inspect its hierarchy.")
            self._clear_diagnostics_view("Choose an input USD to inspect stage statistics.")
            return

        self._set_input_state("Inspecting stage…", "neutral")
        self._clear_diagnostics_view("Inspecting stage statistics…")
        self._inspection_controller.inspect(Path(input_text))

    def _on_input_diagnostics_completed(self, result: OptimizeResult) -> None:
        self._render_stage_diagnostics(result)
        self._update_run_readiness()

    def _on_input_diagnostics_failed(self, message: str) -> None:
        self._clear_diagnostics_view(f"Diagnostics unavailable: {message}")
        self._update_run_readiness()

    def _on_input_inspected(self, inspection: InputInspection) -> None:
        kind = "success" if inspection.is_valid else "error"
        self._set_input_state(inspection.message, kind)
        if inspection.is_valid:
            self._show_scene_inspection(inspection)
            self._tabs.setCurrentWidget(self._scene_tab)
        else:
            self._clear_scene_view(inspection.message)

    def _set_input_state(self, message: str, kind: str) -> None:
        is_success = kind == "success"
        self._input_state_label.setVisible(not is_success)
        self._input_state_label.setText("" if is_success else f"● {message}")
        self._input_state_label.setToolTip(message)
        color = STATUS_COLOR_BY_KIND.get(kind, STATUS_COLOR_BY_KIND["neutral"])
        self._input_state_label.setStyleSheet(f"color: {color};")
        self._update_run_readiness()

    def _show_scene_inspection(self, inspection: InputInspection) -> None:
        """Render scene counts and the bounded prim hierarchy."""
        input_name = Path(self._input_edit.text().strip()).name
        prim_label = "prim" if inspection.prim_count == 1 else "prims"
        root_label = "root" if inspection.root_prim_count == 1 else "roots"
        details = [
            f"{inspection.prim_count:,} {prim_label}",
            f"{inspection.root_prim_count or 0} {root_label}",
        ]
        if inspection.authored_reference_count:
            details.append(f"{inspection.authored_reference_count} references")
        if inspection.authored_payload_count:
            details.append(f"{inspection.authored_payload_count} payloads")
        if inspection.scene_graph_truncated:
            details.append("display truncated")
        self._scene_summary_label.setText(f"{input_name} · {' · '.join(details)}")
        self._scene_summary_label.setToolTip(inspection.message)
        populate_scene_tree(self._scene_tree, inspection.scene_graph)
        self._update_scene_scope()

    def _scene_tree_clear_selection(self) -> None:
        self._scene_tree.clearSelection()

    def _update_scene_scope(self) -> None:
        paths = selected_prim_paths(self._scene_tree)
        preset = self._current_preset()
        if not paths:
            message = "Scope: Entire stage · select one or more prims to limit the workflow."
        elif len(paths) == 1:
            message = f"Scope: {paths[0]} and all descendants"
        else:
            message = f"Scope: {len(paths)} selected prim roots and all descendants"

        if paths and preset is not None:
            skipped_labels = [
                get_operation_presentation(operation_name).label
                for operation_name in preset.operations
                if scoped_operation_skip_reason(operation_name) is not None
            ]
            if skipped_labels:
                message += f" · Skipped to preserve scope: {', '.join(skipped_labels)}"

        self._scene_scope_label.setText(message)
        self._scene_scope_label.setToolTip(message)
        self._clear_scope_button.setEnabled(bool(paths) and self._active_job is None)
        if preset is not None:
            self._populate_operation_list(preset)

    def _clear_scene_view(self, message: str) -> None:
        self._scene_summary_label.setText(message)
        self._scene_summary_label.setToolTip(message)
        self._scene_tree.clear()
        self._update_scene_scope()

    def _clear_diagnostics_view(self, message: str) -> None:
        self._diagnostics_summary_label.setText(message)
        self._diagnostics_summary_label.setToolTip(message)
        self._diagnostic_table.setRowCount(0)

    def _render_stage_diagnostics(self, result: OptimizeResult) -> None:
        """Render automatic stage statistics from the diagnostics workflow."""
        stats = parse_stage_stats(result.worker_output)
        metrics = parse_stage_metrics(result.worker_output)
        populate_diagnostics_table(self._diagnostic_table, stats)

        total = next((stat for stat in stats if stat.prim_type == "Total"), None)
        details = [f"{total.numeric_count:,} prims"] if total is not None else []
        if metrics is not None and metrics.faces is not None:
            details.append(f"{metrics.faces:,} faces")
        if metrics is not None and metrics.vertices is not None:
            details.append(f"{metrics.vertices:,} vertices")
        summary = " · ".join(details) if details else "Stage diagnostics completed."
        self._diagnostics_summary_label.setText(summary)
        self._diagnostics_summary_label.setToolTip(summary)

    def _on_output_path_changed(self, output_text: str) -> None:
        if not self._setting_auto_output:
            self._output_is_auto_generated = not output_text.strip()
            if self._output_is_auto_generated:
                self._rebuild_output_from_input()
                if self._output_edit.text().strip():
                    return
        self._preferences.save_output_path(output_text)

    def _on_workflow_changed(self) -> None:
        preset = self._current_preset()
        if preset is None:
            return
        is_analysis = preset.risk == "diagnostic"
        controls_available = self._active_job is None
        self._output_edit.setEnabled(not is_analysis and controls_available)
        self._output_browse_button.setEnabled(not is_analysis and controls_available)
        self._open_output_button.setEnabled(not is_analysis and controls_available)
        self._description_label.setText(preset.description)
        self._update_scene_scope()
        self._update_run_readiness()

    def _populate_operation_list(self, preset: PresetView) -> None:
        self._operation_list.clear()
        is_scoped = bool(selected_prim_paths(self._scene_tree))
        for operation_name in preset.operations:
            presentation = get_operation_presentation(operation_name)
            label = f"{presentation.category} · {presentation.label}"
            tooltip = presentation.description
            skip_reason = scoped_operation_skip_reason(operation_name) if is_scoped else None
            if skip_reason is not None:
                label += " · skipped for selected scope"
                tooltip += f"\n\nSkipped for selected prims: {skip_reason}"
            item = QListWidgetItem(label)
            item.setToolTip(tooltip)
            item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            self._operation_list.addItem(item)

    def _rebuild_output_from_input(self) -> None:
        """Replace the suggested output string whenever the input string changes."""
        input_text = self._input_edit.text().strip()
        output_text = ""
        if input_text:
            input_path = Path(input_text)
            if input_path.suffix.lower() in SUPPORTED_USD_EXTENSIONS:
                output_text = str(resolve_default_output_path(input_path))

        self._output_is_auto_generated = True
        self._setting_auto_output = True
        signals_were_blocked = self._output_edit.blockSignals(True)
        self._output_edit.setText(output_text)
        self._output_edit.blockSignals(signals_were_blocked)
        self._setting_auto_output = False

    def _effective_output_path(self) -> Path | None:
        preset = self._current_preset()
        if preset is not None and preset.risk == "diagnostic":
            return None
        output_text = self._output_edit.text().strip()
        if output_text:
            return Path(output_text).expanduser()
        input_text = self._input_edit.text().strip()
        if not input_text:
            return None
        return resolve_default_output_path(Path(input_text))

    def _run_blocking_reason(self) -> str | None:
        if self._active_job is not None:
            return "A workflow is already running."
        if not self._environment_usable:
            return "Runtime setup is required before running a workflow."
        if self._current_preset() is None:
            return "Choose a workflow."
        if not self._input_edit.text().strip():
            return "Choose an input USD."
        if self._input_dirty:
            return "Press Enter or leave the input field to inspect."
        return self._inspection_controller.blocking_reason()

    def _update_run_readiness(self) -> None:
        if self._environment_usable:
            self._workspace_splitter.setEnabled(True)
            self._content_stack.setCurrentWidget(self._workspace_splitter)
            self.statusBar().setVisible(True)
        if self._active_job is not None:
            return
        reason = self._run_blocking_reason()
        self._run_button.setEnabled(reason is None)
        if reason is None:
            self._set_status("Ready to run", "success")
            return
        if not self._environment_usable or self._inspection_controller.has_error:
            kind = "error"
        elif "Inspecting" in reason or "Press Enter" in reason:
            kind = "info"
        else:
            kind = "neutral"
        self._set_status(reason, kind)

    def _run_job(self) -> None:
        preset = self._current_preset()
        if preset is None:
            self._show_error("Choose a workflow.")
            return
        input_text = self._input_edit.text().strip()
        if not input_text:
            self._show_error("Choose an input USD path.")
            return
        if not self._confirm_output_replacement(preset, Path(input_text)):
            return

        self._preferences.save_input_path(input_text)
        settings = OptimizeJobSettings(
            input_path=Path(input_text),
            output_path=self._effective_output_path(),
            preset_name=preset.name,
            force=True,
            write_output=preset.risk != "diagnostic",
            prim_paths=selected_prim_paths(self._scene_tree),
        )
        self._start_job(settings)

    def _confirm_output_replacement(self, preset: PresetView, input_path: Path) -> bool:
        if preset.risk == "diagnostic":
            return True
        output_path = self._effective_output_path()
        if output_path is None or not output_path.exists():
            return True
        resolved_input = input_path.expanduser().resolve()
        resolved_output = output_path.expanduser().resolve()
        if resolved_input == resolved_output:
            return self._ask_confirmation(
                "Confirm source replacement",
                "The output is the source USD. Continuing permanently replaces the source file.",
            )
        return self._ask_confirmation(
            "Confirm output replacement",
            f"Replace the existing output file?\n\n{resolved_output}",
        )

    def _ask_confirmation(self, title: str, message: str) -> bool:
        answer = QMessageBox.question(
            self,
            title,
            message,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        return answer == QMessageBox.StandardButton.Yes

    def _start_job(self, settings: OptimizeJobSettings) -> None:
        self._log_edit.clear()
        self._set_running_state()
        self._active_job = OptimizeJobThread(settings)
        self._active_job.output_received.connect(self._append_log)
        self._active_job.succeeded.connect(self._on_job_succeeded)
        self._active_job.failed.connect(self._on_job_failed)
        self._active_job.finished.connect(self._on_thread_finished)
        self._active_job.finished.connect(self._active_job.deleteLater)
        self._active_job.start()

    def _on_job_succeeded(self, result: OptimizeResult) -> None:
        self._append_log("\nFinished successfully.\n")
        if result.worker_output:
            self._show_diagnostics(result)
            return
        self._job_outcome = ("Optimized copy completed", "success")
        self._set_status(*self._job_outcome)
        self._tabs.setCurrentWidget(self._log_edit)

    def _show_diagnostics(self, result: OptimizeResult) -> None:
        """Render structured results from a user-triggered analysis workflow."""
        stats = parse_stage_stats(result.worker_output)
        if stats:
            self._render_stage_diagnostics(result)

        if result.operation_results:
            self._analysis_edit.setPlainText(format_analysis_results(result.operation_results))
            self._tabs.setTabVisible(self._analysis_tab_index, True)
            self._tabs.setCurrentWidget(self._analysis_edit)
            completion_message = "Analysis complete"
        elif stats:
            self._tabs.setCurrentWidget(self._diagnostics_tab)
            completion_message = "Diagnostics complete"
        else:
            self._tabs.setCurrentWidget(self._log_edit)
            completion_message = "Workflow complete"

        self._job_outcome = (completion_message, "success")
        self._set_status(*self._job_outcome)

    def _on_job_failed(self, message: str) -> None:
        if message == "Optimization cancelled.":
            self._append_log("\nCancelled.\n")
            self._job_outcome = ("Workflow cancelled", "warning")
            self._set_status(*self._job_outcome)
            return
        self._append_log(f"\nFailed: {message}\n")
        self._set_job_state("Failed", "error")
        self._job_outcome = ("Workflow failed", "error")
        self._set_status(*self._job_outcome)
        self._show_error(message)

    def _on_thread_finished(self) -> None:
        job_outcome = self._job_outcome
        self._set_idle_controls()
        if job_outcome is not None:
            self._set_status(*job_outcome)
        self._job_outcome = None

    def _cancel_job(self) -> None:
        if self._active_job is None:
            return
        self._active_job.cancel()
        self._run_button.setText("Cancelling…")
        self._run_button.setEnabled(False)
        self._job_state_label.setText("Cancelling…")
        self._set_status("Cancelling workflow…", "warning")

    def _set_running_state(self) -> None:
        self._job_outcome = None
        self._run_button.setText("Cancel workflow")
        self._run_button.setDefault(False)
        self._run_button.setEnabled(True)
        for control in self._job_defining_controls():
            control.setEnabled(False)
        self._run_started_at = monotonic()
        self._elapsed_timer.start()
        self._job_progress.setRange(0, 0)
        self._job_progress.setVisible(True)
        self._set_job_state("Running · 0s", "running")
        self._set_status("Workflow running…", "info")
        self._tabs.setCurrentWidget(self._log_edit)

    def _set_idle_controls(self) -> None:
        self._run_button.setText("Run workflow")
        self._run_button.setDefault(True)
        self._input_edit.setEnabled(True)
        self._input_browse_button.setEnabled(True)
        self._workflow_combo.setEnabled(True)
        self._operation_list.setEnabled(True)
        self._scene_tree.setEnabled(True)
        self._elapsed_timer.stop()
        self._job_progress.setVisible(False)
        self._job_state_label.clear()
        self._job_state_label.setVisible(False)
        self._run_started_at = None
        self._active_job = None
        self._update_scene_scope()
        self._on_workflow_changed()

    def _set_job_state(self, text: str, kind: str) -> None:
        self._job_state_label.setVisible(True)
        self._job_state_label.setText(text)
        self._job_state_label.setStyleSheet(JOB_STATE_STYLE_BY_KIND[kind])

    def _update_elapsed_status(self) -> None:
        if self._run_started_at is None:
            return
        elapsed_seconds = int(monotonic() - self._run_started_at)
        self._job_state_label.setText(f"Running · {elapsed_seconds}s")

    def dragEnterEvent(self, event) -> None:  # noqa: N802
        """Accept a local USD file dropped anywhere on the main window."""
        if any(
            url.isLocalFile() and Path(url.toLocalFile()).suffix.lower() in SUPPORTED_USD_EXTENSIONS
            for url in event.mimeData().urls()
        ):
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:  # noqa: N802
        """Use the first dropped local USD file as the current source."""
        for url in event.mimeData().urls():
            if not url.isLocalFile():
                continue
            input_path = Path(url.toLocalFile())
            if input_path.suffix.lower() not in SUPPORTED_USD_EXTENSIONS:
                continue
            self._input_edit.setText(str(input_path))
            self._on_input_committed()
            event.acceptProposedAction()
            return

    def _open_output_folder(self) -> None:
        output_path = self._effective_output_path()
        folder = output_path.parent if output_path is not None else Path("reports")
        if not folder.exists():
            self._show_error(f"Folder does not exist yet: {folder}")
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder.resolve())))

    def _job_defining_controls(self) -> tuple[QWidget, ...]:
        return (
            self._input_edit,
            self._input_browse_button,
            self._output_edit,
            self._output_browse_button,
            self._workflow_combo,
            self._operation_list,
            self._scene_tree,
            self._clear_scope_button,
            self._open_output_button,
        )

    def closeEvent(self, event) -> None:  # noqa: N802
        """Cancel active work and join all threads before Qt destroys them."""
        active_job = self._active_job
        if active_job is not None and active_job.isRunning():
            active_job.cancel()
            if not active_job.wait(THREAD_SHUTDOWN_TIMEOUT_MS):
                self._set_status("Waiting for workflow cancellation…", "warning")
                event.ignore()
                return

        if not self._inspection_controller.shutdown(THREAD_SHUTDOWN_TIMEOUT_MS):
            self._set_status("Waiting for stage inspection to finish…", "warning")
            event.ignore()
            return
        event.accept()

    def _append_log(self, text: str) -> None:
        append_log_text(self._log_edit, text)

    def _current_preset(self) -> PresetView | None:
        preset_name = self._workflow_combo.currentData(Qt.ItemDataRole.UserRole)
        if not isinstance(preset_name, str):
            return None
        return next((preset for preset in self._presets if preset.name == preset_name), None)

    def _show_error(self, message: str) -> None:
        QMessageBox.critical(self, "USD Optimize App", message)
