"""Severity-aware rendering for the worker log view."""

from __future__ import annotations

from PySide6.QtGui import QColor, QFontDatabase, QTextCharFormat, QTextCursor
from PySide6.QtWidgets import QPlainTextEdit

_LOG_COLOR_BY_KIND = {
    "debug": "#8b949e",
    "info": "#58a6ff",
    "warning": "#d29922",
    "error": "#ff7b72",
    "success": "#4ade80",
    "default": "#e6edf3",
}


def configure_log_view(log_view: QPlainTextEdit) -> None:
    """Configure a readable fixed-width, non-wrapping worker log."""
    log_view.setFont(QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont))
    log_view.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)


def append_log_text(log_view: QPlainTextEdit, text: str) -> None:
    """Append text using a color derived from each line's severity."""
    cursor = log_view.textCursor()
    cursor.movePosition(QTextCursor.MoveOperation.End)
    for segment in text.splitlines(keepends=True):
        text_format = QTextCharFormat()
        text_format.setForeground(QColor(_LOG_COLOR_BY_KIND[_classify_log_line(segment)]))
        cursor.insertText(segment, text_format)
    log_view.setTextCursor(cursor)
    log_view.ensureCursorVisible()


def _classify_log_line(line: str) -> str:
    """Return the presentation kind for one worker-log line."""
    normalized = line.lstrip().upper()
    if normalized.startswith(("[ERROR]", "ERROR:", "FAILED:", "CRITICAL:")):
        return "error"
    if normalized.startswith(("[WARNING]", "WARNING:", "WARN:")):
        return "warning"
    if normalized.startswith(("[DEBUG]", "DEBUG:")):
        return "debug"
    if normalized.startswith(("FINISHED SUCCESSFULLY", "OPTIMIZED:", "WROTE ")):
        return "success"
    if normalized.startswith(
        (
            "[INFO]",
            "INFO:",
            "STARTING ",
            "REPORT:",
            "LOG:",
            "DIAGNOSTICS COMPLETED",
            "WORKER LOG TAIL",
            "WORKER RESULTS:",
            "OPERATION RESULTS:",
        )
    ):
        return "info"
    if normalized.startswith("CANCELLED"):
        return "warning"
    return "default"
