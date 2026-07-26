"""Shared Qt theme constants for the desktop interface."""

STATUS_COLOR_BY_KIND = {
    "neutral": "#92969b",
    "info": "#72a9bd",
    "success": "#70b48b",
    "warning": "#d0a05c",
    "error": "#d36b62",
}
JOB_STATE_STYLE_BY_KIND = {
    "running": "color: #72a9bd; font-weight: bold;",
    "success": "color: #70b48b; font-weight: bold;",
    "error": "color: #d36b62; font-weight: bold;",
}
APP_STYLE = """
/* USD stage workbench: dense, quiet, and built around scene data. */
QWidget {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Noto Sans", Helvetica, Arial;
    font-size: 14px;
    outline: none;
}
[theme="dark"] { background-color: #17191c; color: #e5e1d8; }
[theme="dark"] QLabel { color: #e5e1d8; }

QLabel#SectionHint, QLabel#StatusCaption { color: #92969b; font-size: 12px; }
QLabel#SectionTitle { color: #f2eee5; font-size: 17px; font-weight: 650; }
QLabel#StatusCaption { font-size: 11px; font-weight: 700; color: #b58a57; }
QLabel#FieldLabel { color: #b58a57; font-size: 10px; font-weight: 700; letter-spacing: 0.8px; }
QLabel#StatusValue { color: #f2eee5; font-weight: 600; }
QLabel#InlineState { color: #92969b; font-size: 12px; font-weight: 500; }
QLabel#StatusMessage { font-size: 12px; font-weight: 600; padding-left: 6px; }
QFrame#Card { background-color: #1e2125; border: 1px solid #35393e; border-radius: 3px; }
QFrame#SectionRule { background-color: #3c3934; color: #3c3934; max-height: 1px; }
QFrame#RuntimeBlocker { background-color: #1e2125; border: 1px solid #6c3936; border-radius: 3px; }
QLabel#RuntimeBlockerTitle { color: #e27a72; font-size: 19px; font-weight: 650; }
QLabel#RuntimeBlockerDetail { color: #d7b2ad; font-size: 13px; max-width: 600px; }

QPushButton {
    background-color: transparent; border: 1px solid #4a4e53; border-radius: 3px;
    color: #d8d3c9; font-weight: 600; padding: 6px 12px; min-height: 20px;
}
QPushButton:hover { background-color: #2a2e33; border-color: #777166; color: #f2eee5; }
QPushButton:pressed { background-color: #343028; }
QPushButton:disabled { border-color: #35393e; color: #6f7479; }
QPushButton#PrimaryButton {
    background-color: #b47b43; border-color: #c38c55; color: #17191c; font-weight: 700;
}
QPushButton#PrimaryButton:hover {
    background-color: #d09a61; border-color: #d09a61; color: #17191c;
}
QPushButton#PrimaryButton:disabled {
    background-color: #302c28; border-color: #49443d; color: #7d756a;
}
QToolButton#OpenOutputButton {
    background-color: transparent; border: 1px solid #4a4e53; border-radius: 3px;
    padding: 5px;
}
QToolButton#OpenOutputButton:hover { background-color: #2a2e33; border-color: #777166; }
QToolButton#OpenOutputButton:pressed { background-color: #343028; }
QToolButton#OpenOutputButton:disabled { border-color: #35393e; }

QLineEdit, QComboBox {
    background-color: #181a1d; border: 1px solid #3d4247; border-radius: 3px;
    color: #e5e1d8; padding: 6px 10px; min-height: 20px;
}
QLineEdit:hover, QComboBox:hover { border-color: #777166; background-color: #1c1f23; }
QLineEdit:focus, QComboBox:focus { border-color: #c38c55; }
QComboBox::drop-down { border: none; width: 20px; }
QComboBox QAbstractItemView, QListView#ComboBoxPopup, QAbstractItemView#ComboBoxPopup {
    background-color: #1e2125; color: #e5e1d8; selection-background-color: #3a3027;
    selection-color: #f2eee5; border: 1px solid #4a4e53;
}
QComboBox QAbstractItemView::item, QListView#ComboBoxPopup::item,
QAbstractItemView#ComboBoxPopup::item { padding: 4px 8px; }

QListWidget, QPlainTextEdit, QTableWidget, QTreeWidget {
    background-color: #181a1d; border: 1px solid #35393e; border-radius: 3px;
    color: #e5e1d8; alternate-background-color: #1e2125; selection-background-color: #3a3027;
}
QListWidget::item, QTreeWidget::item { padding: 5px 8px; border-bottom: 1px solid #30343a; }
QListWidget::item:hover, QTreeWidget::item:hover { background-color: #282c30; }
QTreeWidget::item:selected { background-color: #3a3027; color: #f2eee5; }
QTableWidget::item { padding: 4px 8px; border-bottom: 1px solid #30343a; }
QHeaderView::section {
    background-color: #24272b; border: 0; border-bottom: 1px solid #42464b;
    color: #aeb0ae; font-size: 11px; font-weight: 600; padding: 7px;
}
QTabWidget::pane { border: 1px solid #35393e; border-radius: 3px; top: -1px; }
QTabBar::tab {
    background-color: #24272b; color: #92969b; border: 1px solid #35393e; border-bottom: none;
    border-top-left-radius: 3px; border-top-right-radius: 3px; padding: 7px 14px; margin-right: 2px;
}
QTabBar::tab:selected {
    background-color: #181a1d; color: #f2eee5; border-top: 2px solid #b47b43;
    border-bottom-color: #181a1d;
}
QTabBar::tab:hover:!selected { color: #d8d3c9; background-color: #282c30; }
QSplitter::handle { background-color: #35393e; }
QSplitter::handle:hover { background-color: #b47b43; }
QSplitter::handle:horizontal { width: 2px; }

QStatusBar {
    background-color: #1e2125; border-top: 1px solid #35393e; color: #92969b; min-height: 26px;
}
QScrollBar:vertical { border: none; background: transparent; width: 8px; margin: 0; }
QScrollBar::handle:vertical { background-color: #5c6267; border-radius: 4px; min-height: 20px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QProgressBar {
    background-color: #181a1d; border: 1px solid #35393e; border-radius: 4px;
    min-height: 5px; max-height: 5px;
}
QProgressBar::chunk { background-color: #b47b43; border-radius: 4px; }

QLabel#BadgeReady {
    padding: 2px 8px; border-radius: 3px; font-size: 10px; font-weight: 700;
    background: rgba(112, 180, 139, 0.10); color: #70b48b;
    border: 1px solid rgba(112, 180, 139, 0.20);
}
QLabel#BadgeError {
    padding: 2px 8px; border-radius: 3px; font-size: 10px; font-weight: 700;
    background: rgba(211, 107, 98, 0.10); color: #d36b62;
    border: 1px solid rgba(211, 107, 98, 0.20);
}
"""
