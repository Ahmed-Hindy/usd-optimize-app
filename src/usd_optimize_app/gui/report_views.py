"""Qt rendering helpers for structured diagnostic results."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import QTableWidget, QTableWidgetItem

from usd_optimize_app.diagnostics import StageStat


def populate_diagnostics_table(table: QTableWidget, stats: list[StageStat]) -> None:
    """Populate a diagnostics table from parsed stage statistics."""
    table.setRowCount(len(stats))
    for row_index, stat in enumerate(stats):
        is_total = stat.prim_type.strip().lower() == "total"
        values = (stat.prim_type, stat.count, stat.inactive, stat.invisible)
        for column_index, value in enumerate(values):
            display_value = f"{int(value):,}" if column_index > 0 and value.isdigit() else value
            item = QTableWidgetItem(display_value)
            if column_index == 0:
                item.setTextAlignment(
                    Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
                )
            else:
                item.setTextAlignment(
                    Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
                )
            if is_total:
                font = QFont(item.font())
                font.setBold(True)
                item.setFont(font)
                item.setForeground(QColor("#f2eee5"))
            table.setItem(row_index, column_index, item)
    table.resizeColumnsToContents()

