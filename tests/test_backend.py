from __future__ import annotations

from pathlib import Path

import pytest

from usd_optimize_app import backend as backend_module
from usd_optimize_app.backend import (
    OptimizeJobSettings,
    build_optimize_request,
    get_gui_workflows,
    get_preset_views,
    preset_to_view,
    run_batch_jobs,
)
from usd_optimize_app.errors import PresetError
from usd_optimize_app.presets import load_preset


class _FakePrim:
    def __init__(
        self,
        name: str,
        type_name: str,
        children: tuple[_FakePrim, ...] = (),
        *,
        has_payload: bool = False,
        has_references: bool = False,
    ) -> None:
        self._name = name
        self._type_name = type_name
        self._children = children
        self._has_payload = has_payload
        self._has_references = has_references

    def GetAllChildren(self):  # noqa: N802
        return self._children

    def GetName(self):  # noqa: N802
        return self._name

    def GetPath(self):  # noqa: N802
        return f"/{self._name}"

    def GetTypeName(self):  # noqa: N802
        return self._type_name

    def HasAuthoredPayloads(self):  # noqa: N802
        return self._has_payload

    def HasAuthoredReferences(self):  # noqa: N802
        return self._has_references

    def IsInstance(self):  # noqa: N802
        return False

    def IsActive(self):  # noqa: N802
        return True

    def IsLoaded(self):  # noqa: N802
        return True


class _FakeStage:
    def __init__(self, roots: tuple[_FakePrim, ...]) -> None:
        self._pseudo_root = _FakePrim("", "", roots)

    def GetPseudoRoot(self):  # noqa: N802
        return self._pseudo_root


def test_scene_graph_builder_preserves_hierarchy_and_composition_flags() -> None:
    mesh = _FakePrim("Mesh", "Mesh", has_references=True)
    world = _FakePrim("World", "Xform", (mesh,), has_payload=True)

    roots, prim_count, truncated = backend_module._build_scene_graph(_FakeStage((world,)))

    assert prim_count == 2
    assert truncated is False
    assert roots[0].name == "World"
    assert roots[0].has_payload is True
    assert roots[0].children[0].name == "Mesh"
    assert roots[0].children[0].has_references is True


def test_scene_graph_builder_marks_truncated_output(monkeypatch) -> None:
    child = _FakePrim("Child", "Xform")
    world = _FakePrim("World", "Xform", (child,))
    monkeypatch.setattr(backend_module, "SCENE_GRAPH_MAX_PRIMS", 1)

    roots, prim_count, truncated = backend_module._build_scene_graph(_FakeStage((world,)))

    assert prim_count == 1
    assert truncated is True
    assert roots[0].children == ()


def test_scene_graph_builder_keeps_all_roots_when_one_root_is_deep(monkeypatch) -> None:
    monkeypatch.setattr(backend_module, "SCENE_GRAPH_MAX_PRIMS", 5)
    players = _FakePrim(
        "players",
        "Xform",
        tuple(_FakePrim(f"player_{index}", "Xform") for index in range(10)),
    )
    cameras = _FakePrim("cameras", "Scope")
    world = _FakePrim("world", "Xform")

    roots, prim_count, truncated = backend_module._build_scene_graph(
        _FakeStage((players, cameras, world))
    )

    assert [root.name for root in roots] == ["players", "cameras", "world"]
    assert prim_count == 4
    assert truncated is True
    assert len(roots[0].children) == 1


def test_preset_to_view_exposes_display_data() -> None:
    preset = load_preset("diagnostics")

    view = preset_to_view(preset)

    assert view.name == "diagnostics"
    assert view.display_name == "Inspect Stage"
    assert view.risk == "diagnostic"
    assert view.operations == ("printStats",)


def test_get_gui_workflows_returns_only_explicit_actions_in_ui_order() -> None:
    views = get_gui_workflows()

    assert [view.name for view in views] == [
        "safe_publish",
        "geometry_optimization",
        "find_overlaps",
    ]


def test_get_preset_views_preserves_previous_user_preset_contract() -> None:
    views = get_preset_views()

    assert {view.name for view in views} == {
        "safe_publish",
        "diagnostics",
        "find_overlaps",
        "geometry_optimization",
    }


def test_build_optimize_request_uses_shared_validation(tmp_path: Path) -> None:
    input_path = tmp_path / "asset.usda"
    output_path = tmp_path / "asset.optimized.usda"
    input_path.write_text("#usda 1.0\n", encoding="utf-8")

    request = build_optimize_request(
        OptimizeJobSettings(
            input_path=input_path,
            output_path=output_path,
            preset_name="diagnostics",
            force=True,
            dry_run=True,
            prim_paths=("/World/Asset/Mesh", "/World/Asset"),
        )
    )

    assert request.input_path == input_path.resolve()
    assert request.output_path == output_path.resolve()
    assert request.preset.name == "diagnostics"
    assert request.force is True
    assert request.dry_run is True
    assert request.prim_paths == ("/World/Asset",)


def test_batch_jobs_use_one_explicit_output_directory(monkeypatch, tmp_path: Path) -> None:
    inputs = (tmp_path / "first.usda", tmp_path / "second.usda")
    for input_path in inputs:
        input_path.write_text("#usda 1.0\n", encoding="utf-8")
    captured_settings = []
    monkeypatch.setattr(
        "usd_optimize_app.backend.run_optimize_job",
        lambda settings: captured_settings.append(settings),
    )

    run_batch_jobs(inputs, tmp_path / "output", "safe_publish")

    assert [settings.output_path for settings in captured_settings] == [
        tmp_path / "output" / "first.optimized.usda",
        tmp_path / "output" / "second.optimized.usda",
    ]


def test_batch_jobs_reject_duplicate_output_names_before_running(tmp_path: Path) -> None:
    first_input = tmp_path / "a" / "asset.usda"
    second_input = tmp_path / "b" / "asset.usda"
    first_input.parent.mkdir()
    second_input.parent.mkdir()
    first_input.write_text("#usda 1.0\n", encoding="utf-8")
    second_input.write_text("#usda 1.0\n", encoding="utf-8")

    with pytest.raises(PresetError, match="duplicate output paths"):
        run_batch_jobs((first_input, second_input), tmp_path / "output", "safe_publish")


def test_batch_jobs_reject_outputs_that_are_another_batch_input(tmp_path: Path) -> None:
    first_input = tmp_path / "asset.usda"
    second_input = tmp_path / "asset.optimized.usda"
    first_input.write_text("#usda 1.0\n", encoding="utf-8")
    second_input.write_text("#usda 1.0\n", encoding="utf-8")

    with pytest.raises(PresetError, match="overwrite input USD files"):
        run_batch_jobs((first_input, second_input), tmp_path, "safe_publish", force=True)


def test_diagnostic_batch_ignores_output_collisions(monkeypatch, tmp_path: Path) -> None:
    input_path = tmp_path / "asset.usda"
    input_path.write_text("#usda 1.0\n", encoding="utf-8")
    (tmp_path / "asset.optimized.usda").write_text("existing", encoding="utf-8")
    captured_settings = []
    monkeypatch.setattr(
        "usd_optimize_app.backend.run_optimize_job",
        lambda settings: captured_settings.append(settings),
    )

    run_batch_jobs((input_path,), None, "diagnostics")

    assert captured_settings[0].write_output is False
