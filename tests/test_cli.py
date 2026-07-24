from pathlib import Path
from types import SimpleNamespace

from usd_optimize_app.cli import main
from usd_optimize_app.models import OptimizeResult


def test_list_presets_shows_only_supported_workflows_by_default(capsys) -> None:
    exit_code = main(["list-presets"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "safe_publish" in captured.out
    assert "diagnostics" in captured.out
    assert "find_overlaps" in captured.out
    assert "review_light" not in captured.out


def test_list_presets_all_includes_developer_presets(capsys) -> None:
    exit_code = main(["list-presets", "--all"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "review_light" in captured.out
    assert "developer" in captured.out


def test_list_ops_includes_support_classification(monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        "usd_optimize_app.cli.list_available_operations",
        lambda: ["computeExtents", "merge"],
    )

    exit_code = main(["list-ops"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "computeExtents" in captured.out
    assert "supported" in captured.out
    assert "merge" in captured.out
    assert "advanced" in captured.out


def test_show_preset_command_succeeds(capsys) -> None:
    exit_code = main(["show-preset", "diagnostics"])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Inspect Stage" in captured.out
    assert '"audience": "user"' in captured.out


def test_optimize_command_uses_shared_backend(monkeypatch, capsys) -> None:
    backend_result = OptimizeResult(
        input_path=Path("input.usda"),
        output_path=Path("out.usda"),
        preset_name="diagnostics",
        success=True,
        duration_seconds=0.0,
        operations=["printStats"],
        report_path=Path("out.report.json"),
    )

    def fake_run_optimize_job(settings):
        assert settings.input_path == Path("input.usda")
        assert settings.output_path == Path("out.usda")
        assert settings.preset_name == "diagnostics"
        assert settings.force is True
        assert settings.dry_run is True
        assert settings.write_output is False
        return backend_result

    monkeypatch.setattr("usd_optimize_app.cli.run_optimize_job", fake_run_optimize_job)

    exit_code = main(
        [
            "optimize",
            "--input",
            "input.usda",
            "--output",
            "out.usda",
            "--preset",
            "diagnostics",
            "--force",
            "--dry-run",
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Dry run: input.usda" in captured.out
    assert "Optimized:" not in captured.out
    assert "Log:" not in captured.out


def test_smoke_test_command_prints_summary(monkeypatch, capsys) -> None:
    step = SimpleNamespace(
        asset_name="input",
        preset_name="diagnostics",
        result=SimpleNamespace(
            output_path=Path("out.usda"),
            report_path=Path("out.report.json"),
            log_path=None,
            worker_output="diagnostics",
        ),
    )
    smoke_result = SimpleNamespace(
        runtime_root=Path("runtime"),
        operation_count=44,
        input_path=Path("input.usda"),
        output_dir=Path("reports"),
        steps=[step],
    )

    def fake_run_smoke_test(settings):
        assert settings.input_path == Path("input.usda")
        assert settings.output_dir == Path("reports")
        assert settings.preset_names == ("diagnostics",)
        assert settings.external_assets is False
        assert settings.external_asset_manifest is None
        assert settings.external_assets_dir is None
        return smoke_result

    monkeypatch.setattr("usd_optimize_app.cli.run_smoke_test", fake_run_smoke_test)

    exit_code = main(
        [
            "smoke-test",
            "--input",
            "input.usda",
            "--output-dir",
            "reports",
            "--preset",
            "diagnostics",
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Smoke test passed." in captured.out
    assert "Operation count: 44" in captured.out
    assert "Output: none (analysis only)" in captured.out


def test_report_summary_command_prints_text(monkeypatch, capsys) -> None:
    summary_collection = SimpleNamespace(reports_dir=Path("reports"))

    def fake_load_report_summaries(reports_dir):
        assert reports_dir == Path("reports")
        return summary_collection

    monkeypatch.setattr("usd_optimize_app.cli.load_report_summaries", fake_load_report_summaries)
    monkeypatch.setattr(
        "usd_optimize_app.cli.format_report_summary", lambda collection: "summary text"
    )

    exit_code = main(["report-summary", "--reports-dir", "reports"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "summary text" in captured.out


def test_smoke_test_external_assets_options(monkeypatch, capsys) -> None:
    smoke_result = SimpleNamespace(
        runtime_root=Path("runtime"),
        operation_count=44,
        input_path=None,
        output_dir=Path("reports"),
        steps=[
            SimpleNamespace(
                asset_name="asset_a",
                preset_name="diagnostics",
                result=SimpleNamespace(
                    output_path=Path("out.usda"),
                    report_path=None,
                    log_path=None,
                    worker_output="diagnostics",
                ),
            )
        ],
    )

    def fake_run_smoke_test(settings):
        assert settings.input_path is None
        assert settings.output_dir is None
        assert settings.preset_names == ("diagnostics",)
        assert settings.external_assets is True
        assert settings.external_asset_manifest == Path("manifest.json")
        assert settings.external_assets_dir == Path("asset-cache")
        return smoke_result

    monkeypatch.setattr("usd_optimize_app.cli.run_smoke_test", fake_run_smoke_test)

    exit_code = main(
        [
            "smoke-test",
            "--external-assets",
            "--asset-manifest",
            "manifest.json",
            "--assets-dir",
            "asset-cache",
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Assets: 1" in captured.out
    assert "asset_a / diagnostics: OK" in captured.out


def test_batch_command_forwards_explicit_inputs_and_output_dir(monkeypatch, tmp_path: Path) -> None:
    """The batch CLI accepts only explicit input paths and one destination."""
    captured: dict[str, object] = {}

    def fake_run_batch_jobs(inputs, output_dir, preset_name, *, force):
        captured.update(inputs=inputs, output_dir=output_dir, preset_name=preset_name, force=force)
        return [
            OptimizeResult(
                input_path=inputs[0],
                output_path=output_dir / "asset.optimized.usda",
                preset_name=preset_name,
                success=True,
                duration_seconds=0.0,
                operations=[],
            )
        ]

    monkeypatch.setattr("usd_optimize_app.cli.run_batch_jobs", fake_run_batch_jobs)
    first_input = tmp_path / "first.usda"
    second_input = tmp_path / "second.usda"
    output_dir = tmp_path / "optimized"
    assert (
        main(
            [
                "batch",
                "--input",
                str(first_input),
                "--input",
                str(second_input),
                "--output-dir",
                str(output_dir),
                "--preset",
                "safe_publish",
                "--force",
            ]
        )
        == 0
    )
    assert captured == {
        "inputs": (first_input, second_input),
        "output_dir": output_dir,
        "preset_name": "safe_publish",
        "force": True,
    }


def test_diagnostic_batch_prints_worker_output(monkeypatch, capsys, tmp_path: Path) -> None:
    """CLI diagnostics prints its only result channel rather than GUI wording."""

    def fake_run_batch_jobs(inputs, output_dir, preset_name, *, force):
        return [
            OptimizeResult(
                input_path=inputs[0],
                output_path=output_dir / "asset.optimized.usda",
                preset_name=preset_name,
                success=True,
                duration_seconds=0.0,
                operations=[],
                worker_output="| Sphere 1 0 0 |\n",
            )
        ]

    monkeypatch.setattr("usd_optimize_app.cli.run_batch_jobs", fake_run_batch_jobs)
    assert (
        main(
            [
                "batch",
                "--input",
                str(tmp_path / "asset.usda"),
                "--output-dir",
                str(tmp_path / "output"),
                "--preset",
                "diagnostics",
            ]
        )
        == 0
    )

    captured = capsys.readouterr()
    assert "Diagnostics:" in captured.out
    assert "| Sphere 1 0 0 |" in captured.out
    assert "side-panel" not in captured.out
