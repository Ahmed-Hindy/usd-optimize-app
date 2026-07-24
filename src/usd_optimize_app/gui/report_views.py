"""Qt rendering helpers for structured diagnostic results."""

from __future__ import annotations

from PySide6.QtWidgets import QTableWidget, QTableWidgetItem

from usd_optimize_app.diagnostics import StageStat


def populate_diagnostics_table(table: QTableWidget, stats: list[StageStat]) -> None:
    """Populate a diagnostics table from parsed stage statistics."""
    table.setRowCount(len(stats))
    for row_index, stat in enumerate(stats):
        values = (stat.prim_type, stat.count, stat.inactive, stat.invisible)
        for column_index, value in enumerate(values):
            table.setItem(row_index, column_index, QTableWidgetItem(value))
    table.resizeColumnsToContents()
