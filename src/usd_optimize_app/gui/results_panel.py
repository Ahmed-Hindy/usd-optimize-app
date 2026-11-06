"""Summary-led stage and workflow result views."""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
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
from usd_optimize_app.gui.scene_graph_view import configure_scene_tree, selected_prim_paths


@dataclass(frozen=True)
class OverviewState:
    """Text displayed in the result workspace's Overview tab."""

    stage: str = "Choose an input USD to inspect its hierarchy."
    scope: str = "Entire stage"
    workflow: str = "Choose a workflow"


class ResultsPanel(QFrame):
    """Own scene inspection, diagnostics, analysis, log, and result summary views."""

    scope_changed = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Card")
        self._build_widgets()
        self._build_layout()
        self.scene_tree.itemSelectionChanged.connect(self.scope_changed)
        self.clear_scope_button.clicked.connect(self.scene_tree.clearSelection)

    @property
    def selected_paths(self) -> tuple[str, ...]:
        """Return the selected scope roots, normalized by the tree helper."""
        return selected_prim_paths(self.scene_tree)

    def set_overview(self, state: OverviewState) -> None:
        """Render the current stage, scope, workflow, and latest result."""
        self.overview_stage_value.setText(state.stage)
        self.overview_scope_value.setText(state.scope)
        self.overview_workflow_value.setText(state.workflow)
        self.compact_stage_value.setText(state.stage)
        self.compact_scope_value.setText(state.scope)
        self.compact_workflow_value.setText(state.workflow)

    def show_overview(self, *, expand: bool = False) -> None:
        """Select the summary-led entry point for the results workspace."""
        if expand:
            self.set_details_expanded(True)
        self.tabs.setCurrentWidget(self.overview_tab)

    def show_scene(self) -> None:
        """Select the hierarchy drill-down."""
        self.set_details_expanded(True)
        self.tabs.setCurrentWidget(self.scene_tab)

    def show_analysis(self) -> None:
        """Select the structured analysis drill-down."""
        self.set_details_expanded(True)
        self.tabs.setCurrentWidget(self.analysis_edit)

    def show_log(self) -> None:
        """Select the raw worker-log drill-down."""
        self.set_details_expanded(True)
        self.tabs.setCurrentWidget(self.log_edit)

    def set_details_expanded(self, expanded: bool) -> None:
        """Keep initial stage review compact until the user needs the inspector."""
        self._details_expanded = expanded
        self.compact_summary.setVisible(not expanded)
        self.tabs.setVisible(expanded)
        self.heading_title.setText("Stage details" if expanded else "Stage summary")
        self.heading_hint.setText(
            "Review the current stage and latest workflow result."
            if expanded
            else "Review the loaded stage or open its hierarchy to choose a scope."
        )

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
        self.scene_summary_label.setObjectName("OverviewBody")
        self.scene_scope_label = self._wrapped_label(
            "Scope: Entire stage. Select prims to limit the operation."
        )
        self.scene_scope_label.setObjectName("SectionHint")
        self.clear_scope_button = QPushButton("Clear selection")
        self.clear_scope_button.setToolTip("Reset scope to the entire USD stage")
        self.clear_scope_button.setEnabled(False)
        self.scene_tree = QTreeWidget()
        configure_scene_tree(self.scene_tree)
        self.diagnostics_summary_label = self._wrapped_label(
            "Choose an input USD to inspect stage statistics."
        )
        self.diagnostics_summary_label.setObjectName("SectionHint")
        self.diagnostic_table = QTableWidget(0, 4)
        self._configure_diagnostic_table(self.diagnostic_table)
        self.analysis_edit = self._read_only_text("Run Find Overlaps to view affected meshes.")
        self.log_edit = self._read_only_text("Run an operation to view its log.")
        configure_log_view(self.log_edit)
        self.tabs = QTabWidget()

        self.overview_stage_value = self._wrapped_label()
        self.overview_scope_value = self._wrapped_label()
        self.overview_workflow_value = self._wrapped_label()
        self.compact_stage_value = self._wrapped_label()
        self.compact_scope_value = self._wrapped_label()
        self.compact_workflow_value = self._wrapped_label()
        self.empty_state_note = self._wrapped_label(
            "Tip: Drop a .usd, .usda, or .usdc file anywhere on this window or press Ctrl+O "
            "to inspect its prim hierarchy, stage statistics, and scope options."
        )
        self.empty_state_note.setObjectName("EmptyStateNote")
        self._details_expanded = False

    def _build_layout(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(14)
        heading = self._section_heading(
            "Stage summary", "Review the loaded stage or open its hierarchy to choose a scope."
        )
        layout.addLayout(heading)

        self.compact_summary = QWidget()
        compact_layout = QVBoxLayout(self.compact_summary)
        compact_layout.setContentsMargins(0, 0, 0, 0)
        compact_layout.setSpacing(12)
        compact_box = QFrame()
        compact_box.setObjectName("SummaryBox")
        compact_box_layout = QVBoxLayout(compact_box)
        compact_box_layout.setContentsMargins(14, 12, 14, 12)
        compact_box_layout.setSpacing(12)
        compact_box_layout.addLayout(self._overview_section("STAGE", self.compact_stage_value))
        compact_meta_row = QHBoxLayout()
        compact_meta_row.setContentsMargins(0, 0, 0, 0)
        compact_meta_row.setSpacing(16)
        compact_meta_row.addLayout(
            self._overview_section("SCOPE", self.compact_scope_value), stretch=1
        )
        compact_meta_row.addLayout(
            self._overview_section("WORKFLOW", self.compact_workflow_value), stretch=1
        )
        compact_box_layout.addLayout(compact_meta_row)
        compact_layout.addWidget(compact_box)
        compact_layout.addWidget(self.empty_state_note)
        compact_layout.addStretch(1)
        layout.addWidget(self.compact_summary, stretch=1)

        self.overview_tab = QWidget()
        overview_layout = QVBoxLayout(self.overview_tab)
        overview_layout.setContentsMargins(14, 14, 14, 14)
        overview_layout.setSpacing(12)
        overview_box = QFrame()
        overview_box.setObjectName("SummaryBox")
        overview_box_layout = QVBoxLayout(overview_box)
        overview_box_layout.setContentsMargins(12, 10, 12, 10)
        overview_box_layout.setSpacing(10)
        overview_box_layout.addLayout(self._overview_section("STAGE", self.overview_stage_value))
        overview_meta_row = QHBoxLayout()
        overview_meta_row.setContentsMargins(0, 0, 0, 0)
        overview_meta_row.setSpacing(16)
        overview_meta_row.addLayout(
            self._overview_section("SCOPE", self.overview_scope_value), stretch=1
        )
        overview_meta_row.addLayout(
            self._overview_section("WORKFLOW", self.overview_workflow_value), stretch=1
        )
        overview_box_layout.addLayout(overview_meta_row)
        overview_layout.addWidget(overview_box)

        statistics_title = QLabel("STAGE STATISTICS")
        statistics_title.setObjectName("StatusCaption")
        statistics_title.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed
        )
        overview_layout.addWidget(statistics_title)
        overview_layout.addWidget(self.diagnostics_summary_label)
        overview_layout.addWidget(self.diagnostic_table, stretch=1)
        self.overview_tab_index = self.tabs.addTab(self.overview_tab, "Overview")

        self.scene_tab = QWidget()
        scene_layout = QVBoxLayout(self.scene_tab)
        scene_layout.setContentsMargins(14, 14, 14, 14)
        scene_layout.setSpacing(10)
        scene_layout.addWidget(self.scene_summary_label)
        scope_box = QFrame()
        scope_box.setObjectName("SummaryBox")
        scope_row = QHBoxLayout(scope_box)
        scope_row.setContentsMargins(12, 8, 12, 8)
        scope_row.setSpacing(10)
        scope_row.addWidget(self.scene_scope_label, stretch=1)
        scope_row.addWidget(self.clear_scope_button)
        scene_layout.addWidget(scope_box)
        scene_layout.addWidget(self.scene_tree, stretch=1)
        self.scene_tab_index = self.tabs.addTab(self.scene_tab, "Scene")

        self.analysis_tab_index = self.tabs.addTab(self.analysis_edit, "Analysis")
        self.tabs.setTabVisible(self.analysis_tab_index, False)
        self.tabs.addTab(self.log_edit, "Log")
        layout.addWidget(self.tabs, stretch=1)
        self.set_details_expanded(False)

    @staticmethod
    def _configure_diagnostic_table(table: QTableWidget) -> None:
        table.setHorizontalHeaderLabels(("Prim type", "Count", "Inactive", "Invisible"))
        table.verticalHeader().setVisible(False)
        table.setAlternatingRowColors(True)
        table.setShowGrid(False)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        header = table.horizontalHeader()
        header.setStretchLastSection(False)
        header.setMinimumSectionSize(76)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for col in (1, 2, 3):
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)
        if table.horizontalHeaderItem(0) is not None:
            table.horizontalHeaderItem(0).setTextAlignment(
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
            )
        for col in (1, 2, 3):
            item = table.horizontalHeaderItem(col)
            if item is not None:
                item.setTextAlignment(
                    Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
                )

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
        label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Maximum)
        return label

    def _section_heading(self, title: str, hint: str) -> QVBoxLayout:
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        self.heading_title = QLabel(title)
        self.heading_title.setObjectName("SectionTitle")
        self.heading_title.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed
        )
        self.heading_hint = QLabel(hint)
        self.heading_hint.setObjectName("SectionHint")
        self.heading_hint.setWordWrap(True)
        self.heading_hint.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed
        )
        layout.addWidget(self.heading_title)
        layout.addWidget(self.heading_hint)
        layout.addSpacing(4)
        rule = QFrame()
        rule.setObjectName("SectionRule")
        rule.setFrameShape(QFrame.Shape.HLine)
        rule.setFrameShadow(QFrame.Shadow.Plain)
        layout.addWidget(rule)
        return layout

    @staticmethod
    def _overview_section(title: str, value: QLabel) -> QVBoxLayout:
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(3)
        caption = QLabel(title)
        caption.setObjectName("StatusCaption")
        caption.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        layout.addWidget(caption)
        layout.addWidget(value)
        return layout

