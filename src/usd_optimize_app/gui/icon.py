"""Application icon for the USD Optimize GUI."""

from pathlib import Path

from PySide6.QtGui import QIcon

ICON_PATH = Path(__file__).resolve().parents[1] / "resources" / "usdview-blue.svg"


def create_app_icon() -> QIcon:
    """Load the bundled OpenUSD icon.

    Returns:
        Application icon loaded from the packaged SVG asset.
    """
    return QIcon(str(ICON_PATH))
