"""Preset loading and validation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from usd_optimize_app.constants import BUILTIN_PRESETS_DIR
from usd_optimize_app.errors import PresetError
from usd_optimize_app.models import PresetAudience, PresetDefinition, PresetRisk

VALID_RISKS: set[PresetRisk] = {"safe", "review", "diagnostic", "destructive"}
VALID_AUDIENCES: set[PresetAudience] = {"user", "developer"}


def list_preset_paths(presets_dir: Path = BUILTIN_PRESETS_DIR) -> list[Path]:
    """List available preset JSON files.

    Args:
        presets_dir: Directory containing preset files.

    Returns:
        Sorted preset paths.
    """
    if not presets_dir.exists():
        return []
    return sorted(presets_dir.glob("*.json"))


def load_preset(name_or_path: str, presets_dir: Path = BUILTIN_PRESETS_DIR) -> PresetDefinition:
    """Load a preset by name or file path.

    Args:
        name_or_path: Preset stem, file name, or explicit path.
        presets_dir: Directory containing built-in presets.

    Returns:
        Loaded preset definition.

    Raises:
        PresetError: If the preset is missing or invalid.
    """
    preset_path = _resolve_preset_path(name_or_path, presets_dir)
    try:
        raw_data = json.loads(preset_path.read_text(encoding="utf-8"))
    except OSError as error:
        raise PresetError(f"Could not read preset: {preset_path}") from error
    except json.JSONDecodeError as error:
        raise PresetError(f"Invalid preset JSON: {preset_path}: {error}") from error
    return _parse_preset(raw_data, preset_path)


def load_all_presets(
    presets_dir: Path = BUILTIN_PRESETS_DIR,
    *,
    include_developer: bool = False,
) -> list[PresetDefinition]:
    """Load user presets, optionally including developer-only configurations.

    Args:
        presets_dir: Directory containing preset files.
        include_developer: Whether to include advanced validation presets.

    Returns:
        Loaded preset definitions.
    """
    presets = [load_preset(str(path), presets_dir) for path in list_preset_paths(presets_dir)]
    if include_developer:
        return presets
    return [preset for preset in presets if preset.audience == "user"]


def operations_to_json(preset: PresetDefinition) -> str:
    """Serialize preset operations for usd-optimize.

    Args:
        preset: Preset to serialize.

    Returns:
        JSON string containing the operation list.
    """
    return json.dumps(preset.operations, indent=2)


def operation_names(preset: PresetDefinition) -> list[str]:
    """Return operation names from a preset.

    Args:
        preset: Preset to inspect.

    Returns:
        Operation names in execution order.
    """
    names: list[str] = []
    for operation_data in preset.operations:
        operation_name = operation_data.get("operation")
        if isinstance(operation_name, str):
            names.append(operation_name)
    return names


def _resolve_preset_path(name_or_path: str, presets_dir: Path) -> Path:
    candidate_path = Path(name_or_path).expanduser()
    if candidate_path.exists():
        return candidate_path.resolve()

    normalized_name = name_or_path[:-5] if name_or_path.endswith(".json") else name_or_path
    preset_path = presets_dir / f"{normalized_name}.json"
    if preset_path.exists():
        return preset_path.resolve()
    raise PresetError(f"Preset not found: {name_or_path}")


def _parse_preset(raw_data: dict[str, Any], preset_path: Path) -> PresetDefinition:
    if not isinstance(raw_data, dict):
        raise PresetError(f"Preset root must be an object: {preset_path}")

    name = _require_string(raw_data, "name", preset_path)
    display_name = _require_string(raw_data, "display_name", preset_path)
    risk = _require_string(raw_data, "risk", preset_path)
    audience = _require_string(raw_data, "audience", preset_path)
    description = _require_string(raw_data, "description", preset_path)
    operations = raw_data.get("operations")

    if risk not in VALID_RISKS:
        raise PresetError(f"Invalid preset risk '{risk}' in {preset_path}")
    if audience not in VALID_AUDIENCES:
        raise PresetError(f"Invalid preset audience '{audience}' in {preset_path}")
    if not isinstance(operations, list) or not operations:
        raise PresetError(f"Preset operations must be a non-empty list: {preset_path}")
    for operation_data in operations:
        operation_name = (
            operation_data.get("operation") if isinstance(operation_data, dict) else None
        )
        if not isinstance(operation_name, str):
            raise PresetError(f"Invalid preset operation entry: {preset_path}")

    return PresetDefinition(
        name=name,
        display_name=display_name,
        risk=risk,
        audience=audience,
        description=description,
        operations=operations,
        path=preset_path,
    )


def _require_string(raw_data: dict[str, Any], key: str, preset_path: Path) -> str:
    value = raw_data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise PresetError(f"Preset field '{key}' must be a non-empty string: {preset_path}")
    return value
