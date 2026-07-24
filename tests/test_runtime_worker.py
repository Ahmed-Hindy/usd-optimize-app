"""Tests for the isolated usd-optimize worker entry point."""

from __future__ import annotations

from pathlib import Path

import pytest

from usd_optimize_app import runtime_worker


def test_main_returns_success_after_a_completed_job(monkeypatch) -> None:
    """Allow Python and the native runtime to shut down normally after a job."""
    monkeypatch.setattr(runtime_worker, "_run_job", lambda _path: None)

    assert runtime_worker.main(["--job", "job.json"]) == 0


def test_main_returns_failure_after_a_job_error(monkeypatch) -> None:
    """Surface a worker failure without force-terminating the interpreter."""

    def raise_job_error(_path: object) -> None:
        raise RuntimeError("worker failed")

    monkeypatch.setattr(runtime_worker, "_run_job", raise_job_error)

    assert runtime_worker.main(["--job", "job.json"]) == 1


def test_collect_operation_results_preserves_analysis_payload() -> None:
    results = [(True, None, {"analysis": {"overlappingMeshes": ["/World/Mesh"]}})]
    config = [{"operation": "findOverlappingMeshes"}]

    assert runtime_worker._collect_operation_results(results, config) == [
        {
            "operation": "findOverlappingMeshes",
            "output": {"analysis": {"overlappingMeshes": ["/World/Mesh"]}},
        }
    ]


def test_relative_asset_path_is_rebased_for_a_new_output_directory(tmp_path: Path) -> None:
    source_dir = tmp_path / "source"
    output_dir = tmp_path / "output"
    source_dir.mkdir()
    output_dir.mkdir()
    asset_path = source_dir / "payload.usd"

    rebased_path = runtime_worker._path_relative_to_output(
        str(asset_path),
        output_dir,
        "./payload.usd",
    )

    assert rebased_path == "../source/payload.usd"


def test_non_file_asset_identifiers_are_preserved() -> None:
    assert runtime_worker._preserve_asset_identifier("omniverse://server/asset.usd") is True
    assert runtime_worker._preserve_asset_identifier("archive.usdz[layer.usd]") is True
    assert runtime_worker._preserve_asset_identifier("C:/assets/asset.usd") is True
    assert runtime_worker._preserve_asset_identifier("./payload.usd") is False


def test_collect_operation_results_rejects_missing_native_results() -> None:
    with pytest.raises(RuntimeError, match="1 results for 2 requested operations"):
        runtime_worker._collect_operation_results(
            [(True, None, None)],
            [{"operation": "first"}, {"operation": "second"}],
        )
