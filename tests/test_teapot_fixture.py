"""CI validation for the checked-in Intent VFX teapot USD composition fixture."""

from pathlib import Path

TEAPOT_FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "teapot"


def test_teapot_fixture_keeps_its_payload_and_relative_dependency_tree() -> None:
    """Ensure the CI fixture continues to exercise payloads, layers, and references."""
    root_asset = TEAPOT_FIXTURE_ROOT / "teapot.usd"
    payload_asset = TEAPOT_FIXTURE_ROOT / "payload.usd"
    material_asset = TEAPOT_FIXTURE_ROOT / "mtl.usd"
    geometry_asset = TEAPOT_FIXTURE_ROOT / "geo.usd"
    mesh_asset = TEAPOT_FIXTURE_ROOT / "geo" / "UtahTeapot.usd"

    assert all(
        path.is_file()
        for path in (root_asset, payload_asset, material_asset, geometry_asset, mesh_asset)
    )
    assert "prepend payload = @./payload.usd@" in root_asset.read_text(encoding="utf-8")
    assert "subLayers = [" in payload_asset.read_text(encoding="utf-8")
    assert "@./mtl.usd@" in payload_asset.read_text(encoding="utf-8")
    assert "@./geo.usd@" in material_asset.read_text(encoding="utf-8")
    assert "@./geo/UtahTeapot.usd@" in geometry_asset.read_text(encoding="utf-8")
