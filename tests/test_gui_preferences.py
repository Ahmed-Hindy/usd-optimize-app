from PySide6.QtCore import QSettings

from usd_optimize_app.gui.preferences import GuiPreferences, SavedPaths


def test_preferences_store_only_last_paths(tmp_path) -> None:
    settings = QSettings(str(tmp_path / "preferences.ini"), QSettings.Format.IniFormat)
    preferences = GuiPreferences(settings)

    preferences.save_input_path("  C:/assets/scene.usda  ")
    preferences.save_output_path("  C:/assets/scene.optimized.usda  ")

    assert preferences.load_paths() == SavedPaths(
        input_path="C:/assets/scene.usda",
        output_path="C:/assets/scene.optimized.usda",
    )


def test_preferences_ignore_non_string_values(tmp_path) -> None:
    settings = QSettings(str(tmp_path / "preferences.ini"), QSettings.Format.IniFormat)
    settings.setValue("paths/last_input", 42)
    settings.setValue("paths/last_output", ["not", "a", "path"])

    assert GuiPreferences(settings).load_paths() == SavedPaths(input_path="", output_path="")
