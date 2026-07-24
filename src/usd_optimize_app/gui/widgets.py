"""Reusable Qt widgets aligned with RenderKit's input-control behavior."""

from __future__ import annotations

from PySide6.QtCore import QEvent, Qt
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
