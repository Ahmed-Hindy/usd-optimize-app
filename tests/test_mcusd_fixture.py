"""CI validation for the checked-in McUsd diagnostic fixture."""

import re
from pathlib import Path

MCUSD_FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "mcusd"


def test_mcusd_fixture_preserves_scene_variety_for_diagnostics() -> None:
    """Keep the camera, lighting, geometry, material, and shader coverage intact."""
    asset_path = MCUSD_FIXTURE_ROOT / "McUsd.usda"
    attribution_path = MCUSD_FIXTURE_ROOT / "README.md"

    assert asset_path.is_file()
    assert attribution_path.is_file()
    asset_text = asset_path.read_text(encoding="utf-8")

    assert 'def Xform "McUsd"' in asset_text
    assert 'def Camera "Camera"' in asset_text
    assert 'def DistantLight "Sun"' in asset_text
    assert 'def DomeLight "DomeLight"' in asset_text
    assert len(re.findall(r"^\s*def Mesh ", asset_text, flags=re.MULTILINE)) == 23
    assert len(re.findall(r"^\s*def Material ", asset_text, flags=re.MULTILINE)) == 23
    assert len(re.findall(r"^\s*def Shader ", asset_text, flags=re.MULTILINE)) == 121

    texture_references = re.findall(r"@(?:\./)?([^@]+\.png)@", asset_text)
    assert len(texture_references) == 76
    assert all((MCUSD_FIXTURE_ROOT / texture_path).is_file() for texture_path in texture_references)
