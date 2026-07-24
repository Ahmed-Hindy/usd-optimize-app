"""Persistent GUI preferences for the last used USD paths."""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QSettings

LAST_INPUT_KEY = "paths/last_input"
LAST_OUTPUT_KEY = "paths/last_output"


@dataclass(frozen=True)
class SavedPaths:
    """Last input and output paths restored by the GUI."""

    input_path: str
    output_path: str


class GuiPreferences:
    """Read and write the minimal durable GUI state."""

    def __init__(self, settings: QSettings | None = None) -> None:
        """Initialize the preference store.

        Args:
            settings: Optional settings backend, primarily for tests.
        """
        self._settings = settings or QSettings("usd-optimize-app", "USD Optimize")

    def load_paths(self) -> SavedPaths:
        """Return the last saved input and output paths."""
        return SavedPaths(
            input_path=_coerce_string(self._settings.value(LAST_INPUT_KEY, "")),
            output_path=_coerce_string(self._settings.value(LAST_OUTPUT_KEY, "")),
        )

    def save_input_path(self, input_path: str) -> None:
        """Save the committed input path."""
        self._settings.setValue(LAST_INPUT_KEY, input_path.strip())
        self._settings.sync()

    def save_output_path(self, output_path: str) -> None:
        """Save the output path currently shown in the GUI."""
        self._settings.setValue(LAST_OUTPUT_KEY, output_path.strip())
        self._settings.sync()


def _coerce_string(value: object) -> str:
    """Return a settings value as a stripped string."""
    return value.strip() if isinstance(value, str) else ""
