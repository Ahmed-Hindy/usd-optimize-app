"""Severity-aware worker-log rendering tests."""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtGui import QTextBlock
from PySide6.QtWidgets import QApplication, QPlainTextEdit

from usd_optimize_app.gui.log_view import append_log_text, configure_log_view


def _block_color_name(block: QTextBlock) -> str:
    fragment_iterator = block.begin()
    fragment = fragment_iterator.fragment()
    return fragment.charFormat().foreground().color().name()


def test_log_view_colors_lines_by_severity() -> None:
    application = QApplication.instance() or QApplication([])
    del application
    log_view = QPlainTextEdit()
    configure_log_view(log_view)

    append_log_text(
        log_view,
        "[DEBUG] details\n[INFO] running\n[WARNING] review\n[ERROR] failed\n"
        "Finished successfully.\n",
    )

    document = log_view.document()
    color_names = []
    block = document.firstBlock()
    while block.isValid() and block.text():
        color_names.append(_block_color_name(block))
        block = block.next()

    assert log_view.lineWrapMode() == QPlainTextEdit.LineWrapMode.NoWrap
    assert color_names == ["#8b949e", "#58a6ff", "#d29922", "#ff7b72", "#4ade80"]
