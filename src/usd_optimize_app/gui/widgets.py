"""Reusable Qt widgets aligned with RenderKit's input-control behavior."""

from __future__ import annotations

from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QComboBox, QListView, QSizePolicy

COMBO_POPUP_OBJECT_NAME = "ComboBoxPopup"


class ComboPopupView(QListView):
    """Highlight a combo-box row whenever the pointer moves over it."""

    def viewportEvent(self, event: QEvent) -> bool:  # noqa: N802
        if event.type() == QEvent.Type.MouseMove:
            self._highlight_index_at_event(event)
        return super().viewportEvent(event)

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        self._highlight_index_at_event(event)
        super().mouseMoveEvent(event)

    def _highlight_index_at_event(self, event) -> None:
        position = event.position().toPoint()
        index = self.indexAt(position)
        if index.isValid():
            self.setCurrentIndex(index)


class NoWheelComboBox(QComboBox):
    """RenderKit-style combo box that ignores accidental wheel changes."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.setView(ComboPopupView(self))
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setMinimumWidth(0)
        self._configure_popup_view()
        self.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.setMinimumContentsLength(12)

    def _configure_popup_view(self) -> None:
        view = self.view()
        view.setObjectName(COMBO_POPUP_OBJECT_NAME)
        view.setMouseTracking(True)
        viewport = view.viewport()
        if viewport is not None:
            viewport.setMouseTracking(True)

    def wheelEvent(self, event) -> None:  # noqa: N802
        """Ignore wheel input unless this control is explicitly focused."""
        if not self.hasFocus():
            event.ignore()
            return
        super().wheelEvent(event)

    def paintEvent(self, event) -> None:  # noqa: N802
        """Render the combo box with an explicit chevron affordance."""
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        if not self.isEnabled():
            chevron_color = QColor("#6f7479")
        elif self.underMouse() or self.hasFocus():
            chevron_color = QColor("#f2eee5")
        else:
            chevron_color = QColor("#9e9a91")
        pen = QPen(chevron_color, 1.6)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)

        center_x = self.width() - 15.0
        center_y = self.height() / 2.0
        chevron = QPainterPath()
        chevron.moveTo(QPointF(center_x - 4.0, center_y - 1.8))
        chevron.lineTo(QPointF(center_x, center_y + 2.2))
        chevron.lineTo(QPointF(center_x + 4.0, center_y - 1.8))
        painter.drawPath(chevron)
        painter.end()

