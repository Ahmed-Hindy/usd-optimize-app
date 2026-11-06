"""Application icon for the USD Optimize GUI."""

from pathlib import Path

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap

ICON_PATH = Path(__file__).resolve().parents[1] / "resources" / "usdview-blue.svg"


def create_app_icon() -> QIcon:
    """Load the bundled OpenUSD icon.

    Returns:
        Application icon loaded from the packaged SVG asset.
    """
    return QIcon(str(ICON_PATH))


def create_folder_icon() -> QIcon:
    """Create a monochrome stroke folder icon tailored to the dark workbench theme."""
    icon = QIcon()
    for size in (16, 20, 24, 32):
        icon.addPixmap(_render_folder_pixmap(size, QColor("#d8d3c9")), QIcon.Mode.Normal)
        icon.addPixmap(_render_folder_pixmap(size, QColor("#f2eee5")), QIcon.Mode.Active)
        icon.addPixmap(_render_folder_pixmap(size, QColor("#6f7479")), QIcon.Mode.Disabled)
    return icon


def _render_folder_pixmap(size: int, color: QColor) -> QPixmap:
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

    scale = size / 16.0
    pen = QPen(color, max(1.35 * scale, 1.2))
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)

    path = QPainterPath()
    path.moveTo(QPointF(2.0 * scale, 4.2 * scale))
    path.lineTo(QPointF(6.0 * scale, 4.2 * scale))
    path.lineTo(QPointF(7.4 * scale, 5.8 * scale))
    path.lineTo(QPointF(14.0 * scale, 5.8 * scale))
    path.lineTo(QPointF(14.0 * scale, 12.4 * scale))
    path.lineTo(QPointF(2.0 * scale, 12.4 * scale))
    path.closeSubpath()
    painter.drawPath(path)

    flap_rect = QRectF(2.0 * scale, 7.2 * scale, 12.0 * scale, 5.2 * scale)
    painter.drawLine(flap_rect.topLeft(), flap_rect.topRight())
    painter.end()
    return pixmap

