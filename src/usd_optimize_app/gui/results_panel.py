"""Summary-led stage and workflow result views."""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QSizePolicy,
    QTableWidget,
    QTabWidget,
    QTreeWidget,
    QVBoxLayout,
    QWidget,
)

from usd_optimize_app.gui.log_view import configure_log_view
from usd_optimize_app.gui.scene_graph_view import configure_scene_tree


@dataclass(frozen=True)
class OverviewState:
    """Text displayed in the result workspace's Overview tab."""

    stage: str = "Choose an input USD to inspect its hierarchy."
    scope: str = "Entire stage"
    workflow: str = "Choose a workflow"
    outcome: str = "No workflow has run for this stage."
    action_label: str = ""
    action_target: str = ""


class ResultsPanel(QFrame):
    """Own scene inspection, diagnostics, analysis, log, and result summary views."""

    scope_changed = Signal()
    overview_action_requested = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Card")
        self._build_widgets()
        self._build_layout()
        self.scene_tree.itemSelectionChanged.connect(self.scope_changed)
        self.clear_scope_button.clicked.connect(self.scene_tree.clearSelection)
        self.overview_action_button.clicked.connect(self._emit_overview_action)

    @property
    def selected_paths(self) -> tuple[str, ...]:
        """Return the selected scope roots, normalized by the tree helper."""
        from usd_optimize_app.gui.scene_graph_view import selected_prim_paths

        return selected_prim_paths(self.scene_tree)

    def set_overview(self, state: OverviewState) -> None:
        """Render the current stage, scope, workflow, and latest result."""
        self.overview_stage_value.setText(state.stage)
        self.overview_scope_value.setText(state.scope)
        self.overview_workflow_value.setText(state.workflow)
        self.overview_outcome_value.setText(state.outcome)
        self.overview_action_button.setText(state.action_label)
        self._overview_action_target = state.action_target
        self.overview_action_button.setVisible(bool(state.action_label and state.action_target))

    def show_overview(self) -> None:
        """Select the summary-led entry point for the results workspace."""
        self.tabs.setCurrentWidget(self.overview_tab)

    def show_scene(self) -> None:
        """Select the hierarchy drill-down."""
        self.tabs.setCurrentWidget(self.scene_tab)

    def show_diagnostics(self) -> None:
        """Select the diagnostics drill-down."""
        self.tabs.setCurrentWidget(self.diagnostics_tab)

    def show_analysis(self) -> None:
        """Select the structured analysis drill-down."""
        self.tabs.setCurrentWidget(self.analysis_edit)

    def show_log(self) -> None:
        """Select the raw worker-log drill-down."""
        self.tabs.setCurrentWidget(self.log_edit)

    def set_analysis_visible(self, visible: bool) -> None:
        """Show Analysis only after it contains structured findings."""
        self.tabs.setTabVisible(self.analysis_tab_index, visible)

    def clear_log(self) -> None:
        """Remove stale worker output before a new run."""
        self.log_edit.clear()

    def _build_widgets(self) -> None:
        self.scene_summary_label = self._wrapped_label(
            "Choose an input USD to inspect its hierarchy."
        )
        self.scene_summary_label.setObjectName("SectionHint")
        self.scene_scope_label = self._wrapped_label(
            "Scope: Entire stage. Select prims to limit the operation."
        )
        self.scene_scope_label.setObjectName("SectionHint")
        self.clear_scope_button = QPushButton("Clear selection")
        self.clear_scope_button.setEnabled(False)
        self.scene_tree = QTreeWidget()
        configure_scene_tree(self.scene_tree)
        self.diagnostics_summary_label = self._wrapped_label(
            "Choose an input USD to inspect stage statistics."
        )
        self.diagnostics_summary_label.setObjectName("SectionHint")
        self.diagnostic_table = QTableWidget(0, 4)
        self.analysis_edit = self._read_only_text("Run Find Overlaps to view affected meshes.")
        self.log_edit = self._read_only_text("Run an operation to view its log.")
        configure_log_view(self.log_edit)
        self.tabs = QTabWidget()

        self.overview_stage_value = self._wrapped_label()
        self.overview_scope_value = self._wrapped_label()
        self.overview_workflow_value = self._wrapped_label()
        self.overview_outcome_value = self._wrapped_label()
        self.overview_action_button = QPushButton()
        self.overview_action_button.setVisible(False)
        self._overview_action_target = ""

    def _build_layout(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 15, 16, 16)
        layout.setSpacing(12)
        layout.addLayout(
            self._section_heading(
                "Stage details", "Review the current stage and latest workflow result."
            )
        )

        self.overview_tab = QWidget()
        overview_layout = QVBoxLayout(self.overview_tab)
        overview_layout.setContentsMargins(0, 0, 0, 0)
        overview_layout.setSpacing(12)
        overview_layout.addLayout(self._overview_section("STAGE", self.overview_stage_value))
        overview_layout.addLayout(self._overview_section("SCOPE", self.overview_scope_value))
        overview_layout.addLayout(self._overview_section("WORKFLOW", self.overview_workflow_value))
        overview_layout.addLayout(
            self._overview_section("LATEST RESULT", self.overview_outcome_value)
        )
        overview_layout.addWidget(self.overview_action_button)
        overview_layout.addStretch(1)
        self.overview_tab_index = self.tabs.addTab(self.overview_tab, "Overview")

        self.scene_tab = QWidget()
        scene_layout = QVBoxLayout(self.scene_tab)
        scene_layout.setContentsMargins(0, 0, 0, 0)
        scene_layout.setSpacing(8)
        scene_layout.addWidget(self.scene_summary_label)
        scope_row = QHBoxLayout()
        scope_row.addWidget(self.scene_scope_label, stretch=1)
        scope_row.addWidget(self.clear_scope_button)
        scene_layout.addLayout(scope_row)
        scene_layout.addWidget(self.scene_tree, stretch=1)
        self.scene_tab_index = self.tabs.addTab(self.scene_tab, "Scene")

        self.diagnostics_tab = QWidget()
        diagnostics_layout = QVBoxLayout(self.diagnostics_tab)
        diagnostics_layout.setContentsMargins(0, 0, 0, 0)
        diagnostics_layout.setSpacing(8)
        diagnostics_layout.addWidget(self.diagnostics_summary_label)
        diagnostics_layout.addWidget(self.diagnostic_table, stretch=1)
        self.diagnostic_table.setHorizontalHeaderLabels(
            ("Prim type", "Count", "Inactive", "Invisible")
        )
        self.diagnostic_table.verticalHeader().setVisible(False)
        self.diagnostic_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents
        )
        self.diagnostic_table.horizontalHeader().setStretchLastSection(True)
        self.diagnostics_tab_index = self.tabs.addTab(self.diagnostics_tab, "Diagnostics")
        self.analysis_tab_index = self.tabs.addTab(self.analysis_edit, "Analysis")
        self.tabs.setTabVisible(self.analysis_tab_index, False)
        self.tabs.addTab(self.log_edit, "Log")
        layout.addWidget(self.tabs)

    def _emit_overview_action(self) -> None:
        if self._overview_action_target:
            self.overview_action_requested.emit(self._overview_action_target)

    @staticmethod
    def _read_only_text(placeholder: str) -> QPlainTextEdit:
        text_edit = QPlainTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setPlaceholderText(placeholder)
        return text_edit

    @staticmethod
    def _wrapped_label(text: str = "") -> QLabel:
        label = QLabel(text)
        label.setWordWrap(True)
        label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        return label

    @staticmethod
    def _section_heading(title: str, hint: str) -> QVBoxLayout:
        layout = QVBoxLayout()
        layout.setSpacing(4)
        title_label = QLabel(title)
        title_label.setObjectName("SectionTitle")
        hint_label = QLabel(hint)
        hint_label.setObjectName("SectionHint")
        hint_label.setWordWrap(True)
        layout.addWidget(title_label)
        layout.addWidget(hint_label)
        rule = QFrame()
        rule.setObjectName("SectionRule")
        rule.setFrameShape(QFrame.Shape.HLine)
        rule.setFrameShadow(QFrame.Shadow.Plain)
        layout.addWidget(rule)
        return layout

    @staticmethod
    def _overview_section(title: str, value: QLabel) -> QVBoxLayout:
        layout = QVBoxLayout()
        layout.setSpacing(3)
        caption = QLabel(title)
        caption.setObjectName("StatusCaption")
        layout.addWidget(caption)
        layout.addWidget(value)
        return layout
