"""Shared Qt theme constants for the desktop interface."""

STATUS_COLOR_BY_KIND = {
    "neutral": "#9e9a91",
    "info": "#72a9bd",
    "success": "#70b48b",
    "warning": "#d0a05c",
    "error": "#d36b62",
}
JOB_STATE_STYLE_BY_KIND = {
    "running": "color: #72a9bd; font-weight: 600;",
    "success": "color: #70b48b; font-weight: 600;",
    "error": "color: #d36b62; font-weight: 600;",
}
APP_STYLE = """
/* USD stage workbench: dense, quiet, and built around scene data. */
QWidget {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Noto Sans", Helvetica, Arial;
    font-size: 13px;
    outline: none;
}
[theme="dark"] { background-color: #17191c; color: #e5e1d8; }
[theme="dark"] QLabel { color: #e5e1d8; background: transparent; }

QLabel#SectionTitle {
    color: #f2eee5; font-size: 16px; font-weight: 650; letter-spacing: -0.2px;
}
QLabel#SectionHint { color: #9e9a91; font-size: 12px; }
QLabel#StatusCaption {
    color: #9e9a91; font-size: 10px; font-weight: 700; letter-spacing: 0.7px;
}
QLabel#FieldLabel {
    color: #9e9a91; font-size: 10px; font-weight: 700; letter-spacing: 0.7px;
    padding-top: 8px; padding-bottom: 8px;
}
QLabel#StatusValue { color: #f2eee5; font-size: 13px; font-weight: 600; }
QLabel#EmptyStateNote { color: #9e9a91; font-size: 12px; }
QLabel#InlineState { color: #9e9a91; font-size: 12px; font-weight: 500; padding-top: 2px; }
QLabel#StatusMessage { font-size: 12px; font-weight: 600; padding-left: 6px; }

QFrame#Card {
    background-color: #1e2125; border: 1px solid #32363b; border-radius: 4px;
}
QFrame#Card[dragActive="true"] {
    border: 1px solid #b47b43; background-color: #212428;
}
QFrame#SummaryBox {
    background-color: #181a1d; border: 1px solid #2e3237; border-radius: 3px;
}
QFrame#SectionRule {
    background-color: #2e3136; color: #2e3136; min-height: 1px; max-height: 1px; border: none;
}
QFrame#RuntimeBlocker {
    background-color: #1e2125; border: 1px solid #6c3936; border-radius: 4px;
}
QLabel#RuntimeBlockerTitle { color: #e27a72; font-size: 18px; font-weight: 650; }
QLabel#RuntimeBlockerDetail { color: #d7b2ad; font-size: 13px; max-width: 600px; }

QPushButton {
    background-color: #23262b; border: 1px solid #45494f; border-radius: 3px;
    color: #ded9cf; font-weight: 600; padding: 6px 14px; min-height: 20px;
}
QPushButton:hover { background-color: #2c3036; border-color: #777166; color: #f2eee5; }
QPushButton:focus { border-color: #72a9bd; color: #f2eee5; }
QPushButton:pressed { background-color: #34383d; border-color: #8a8377; }
QPushButton:disabled {
    background-color: #1b1d21; border-color: #2d3035; color: #666a70;
}
QPushButton#PrimaryButton {
    background-color: #b47b43; border-color: #c38c55; color: #17191c;
    font-weight: 700; padding: 6px 18px;
}
QPushButton#PrimaryButton:hover {
    background-color: #c88e54; border-color: #d49d65; color: #17191c;
}
QPushButton#PrimaryButton:focus {
    border-color: #f2eee5; background-color: #c0864d; color: #17191c;
}
QPushButton#PrimaryButton:pressed {
    background-color: #9f6a36; border-color: #b47b43; color: #17191c;
}
QPushButton#PrimaryButton:disabled {
    background-color: #2b2723; border-color: #3d3832; color: #756e64;
}

QToolButton#OpenOutputButton {
    background-color: #23262b; border: 1px solid #45494f; border-radius: 3px;
    padding: 5px;
}
QToolButton#OpenOutputButton:hover { background-color: #2c3036; border-color: #777166; }
QToolButton#OpenOutputButton:focus { border-color: #72a9bd; }
QToolButton#OpenOutputButton:pressed { background-color: #34383d; }
QToolButton#OpenOutputButton:disabled {
    background-color: #1b1d21; border-color: #2d3035;
}

QLineEdit, QComboBox {
    background-color: #16181b; border: 1px solid #3a3f45; border-radius: 3px;
    color: #e5e1d8; padding: 6px 10px; min-height: 20px;
    selection-background-color: #4a3a2a; selection-color: #f2eee5;
}
QComboBox { padding-right: 28px; }
QLineEdit:hover, QComboBox:hover { border-color: #777166; background-color: #1a1d21; }
QLineEdit:focus, QComboBox:focus { border-color: #72a9bd; background-color: #16181b; }
QLineEdit:disabled, QComboBox:disabled {
    background-color: #15171a; border-color: #292c30; color: #666a70;
}
QComboBox::drop-down { border: none; width: 24px; background: transparent; }
QComboBox::down-arrow { image: none; width: 0px; height: 0px; }
QComboBox QAbstractItemView, QListView#ComboBoxPopup, QAbstractItemView#ComboBoxPopup {
    background-color: #1e2125; color: #e5e1d8; selection-background-color: #3a3027;
    selection-color: #f2eee5; border: 1px solid #4a4e53; padding: 2px;
}
QComboBox QAbstractItemView::item, QListView#ComboBoxPopup::item,
QAbstractItemView#ComboBoxPopup::item { padding: 6px 10px; border-radius: 2px; }

QListWidget, QPlainTextEdit, QTableWidget, QTreeWidget {
    background-color: #16181b; border: 1px solid #32363b; border-radius: 3px;
    color: #e5e1d8; alternate-background-color: #1a1d21;
    selection-background-color: #3a3027; selection-color: #f2eee5;
}
QListWidget:focus, QPlainTextEdit:focus, QTableWidget:focus, QTreeWidget:focus {
    border-color: #5b8798;
}
QListWidget::item { padding: 7px 10px; border-bottom: 1px solid #26292e; }
QTreeWidget::item { padding: 5px 8px; border-bottom: 1px solid #26292e; }
QListWidget::item:hover, QTreeWidget::item:hover { background-color: #24282d; }
QTreeWidget::item:selected { background-color: #3a3027; color: #f2eee5; }
QTreeWidget:disabled { color: #666a70; background-color: #15171a; }
QTableWidget::item { padding: 6px 10px; border-bottom: 1px solid #26292e; }

QHeaderView::section {
    background-color: #202328; border: 0; border-bottom: 1px solid #383c42;
    border-right: 1px solid #2a2d32;
    color: #b5b1a8; font-size: 11px; font-weight: 600; padding: 6px 10px;
}
QHeaderView::section:last { border-right: 0; }

QTabWidget::pane {
    background-color: #1a1d21; border: 1px solid #32363b; border-radius: 3px; top: -1px;
}
QTabWidget QPlainTextEdit {
    border: none; border-radius: 0px; background-color: #16181b; padding: 10px 12px;
}
QTabBar::tab {
    background-color: #22252a; color: #9e9a91; border: 1px solid #32363b; border-bottom: none;
    border-top-left-radius: 3px; border-top-right-radius: 3px;
    padding: 7px 16px; margin-right: 3px; font-weight: 500;
}
QTabBar::tab:selected {
    background-color: #1a1d21; color: #f2eee5; font-weight: 600;
    border-top: 2px solid #b47b43; border-bottom-color: #1a1d21;
}
QTabBar::tab:hover:!selected { color: #e5e1d8; background-color: #282c31; }
QTabBar::tab:focus { color: #f2eee5; }

QSplitter::handle { background-color: #2b2e33; }
QSplitter::handle:hover { background-color: #777166; }
QSplitter::handle:horizontal { width: 2px; margin: 0 4px; }

QStatusBar {
    background-color: #1b1e22; border-top: 1px solid #2e3237; color: #9e9a91; min-height: 26px;
}
QStatusBar::item { border: none; }

QScrollBar:vertical { border: none; background: transparent; width: 8px; margin: 2px 1px; }
QScrollBar::handle:vertical { background-color: #4a4e54; border-radius: 3px; min-height: 24px; }
QScrollBar::handle:vertical:hover { background-color: #777166; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }

QScrollBar:horizontal { border: none; background: transparent; height: 8px; margin: 1px 2px; }
QScrollBar::handle:horizontal { background-color: #4a4e54; border-radius: 3px; min-width: 24px; }
QScrollBar::handle:horizontal:hover { background-color: #777166; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal { background: transparent; }

QProgressBar {
    background-color: #16181b; border: 1px solid #32363b; border-radius: 3px;
    min-height: 5px; max-height: 5px;
}
QProgressBar::chunk { background-color: #b47b43; border-radius: 2px; }
"""

