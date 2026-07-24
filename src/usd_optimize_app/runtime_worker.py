"""Subprocess worker for isolated usd-optimize jobs."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from usd_optimize_app.usd_env import configure_environment

_CONTEXT_FLAGS = {
    "analysisMode",
    "debug",
    "singleThreaded",
    "verbose",
    "generateReport",
    "captureStats",
}


def main(argv: list[str] | None = None) -> int:
    """Run an isolated optimization job.

    Args:
        argv: Optional command arguments.

    Returns:
        Process exit code.
    """
    parser = argparse.ArgumentParser(description="Run an isolated usd-optimize job.")
    parser.add_argument("--job", required=True, type=Path, help="Job JSON path.")
    args = parser.parse_args(argv)

    try:
        _run_job(args.job)
    except Exception as error:
        print(f"ERROR: {error}", file=sys.stderr, flush=True)
        return 1
    return 0


def _run_job(job_path: Path) -> None:
    job_data = json.loads(job_path.read_text(encoding="utf-8"))
    runtime_root = Path(job_data["runtime_root"])
    input_path = Path(job_data["input_path"])
    output_path = Path(job_data["output_path"])
    operations = job_data["operations"]
    write_output = bool(job_data.get("write_output", True))

    configure_environment(runtime_root)

    from pxr import Usd
    from usd_optimize.core import ExecutionContext, UsdOptimizeCore

    core = UsdOptimizeCore.getInstance()

    stage = Usd.Stage.Open(str(input_path))
    if stage is None:
        raise RuntimeError(f"Could not open USD stage: {input_path}")

    context = ExecutionContext()
    context.set_stage(stage)
    config = _prepare_operation_config(operations, context)
    results = core.executeConfig(context, config)
    operation_results = _collect_operation_results(results, config)
    _write_operation_results(Path(job_data["result_path"]), operation_results)

    if write_output:
        _export_stage(stage, input_path, output_path)
        print(f"Wrote {output_path}", flush=True)
    else:
        print("Diagnostics completed without writing a USD output.", flush=True)


def _export_stage(stage: object, input_path: Path, output_path: Path) -> None:
    """Export a stage and preserve relative root-layer dependencies.

    Args:
        stage: Open USD stage after optimization.
        input_path: Original root-layer path used to anchor relative assets.
        output_path: Destination root-layer path.

    Raises:
        RuntimeError: If the stage cannot be exported or the output layer saved.
    """
    from pxr import Sdf, UsdUtils

    output_path.parent.mkdir(parents=True, exist_ok=True)
    root_layer = stage.GetRootLayer()
    if not root_layer.Export(str(output_path)):
        raise RuntimeError(f"Could not export USD stage: {output_path}")
    if input_path.parent == output_path.parent:
        return

    output_layer = Sdf.Layer.FindOrOpen(str(output_path))
    if output_layer is None:
        raise RuntimeError(f"Could not reopen exported USD layer: {output_path}")

    def rebase_asset_path(asset_path: str) -> str:
        if _preserve_asset_identifier(asset_path):
            return asset_path
        anchored_path = Sdf.ComputeAssetPathRelativeToLayer(root_layer, asset_path)
        return _path_relative_to_output(anchored_path, output_path.parent, asset_path)

    UsdUtils.ModifyAssetPaths(output_layer, rebase_asset_path)
    if not output_layer.Save():
        raise RuntimeError(f"Could not save rebased USD layer: {output_path}")


def _preserve_asset_identifier(asset_path: str) -> bool:
    """Return whether an asset identifier should not be filesystem-rebased."""
    if not asset_path:
        return True
    if "://" in asset_path or "[" in asset_path or "]" in asset_path:
        return True
    return Path(asset_path).is_absolute()


def _path_relative_to_output(
    anchored_path: str,
    output_dir: Path,
    fallback_path: str,
) -> str:
    """Return an anchored file path relative to the output directory."""
    anchored_file = Path(anchored_path)
    if not anchored_file.is_absolute():
        return fallback_path
    try:
        relative_path = os.path.relpath(anchored_file, output_dir)
    except ValueError:
        return anchored_file.as_posix()
    return Path(relative_path).as_posix()


def _prepare_operation_config(
    operations: list[dict[str, Any]],
    context: object,
) -> list[dict[str, Any]]:
    prepared_operations: list[dict[str, Any]] = []
    for operation_data in operations:
        if operation_data.get("operation") == "executionContext":
            _apply_context_flags(context, operation_data)
            continue
        prepared_operations.append(dict(operation_data))
    return prepared_operations


def _apply_context_flags(context: object, operation_data: dict[str, Any]) -> None:
    for key in _CONTEXT_FLAGS:
        if key in operation_data:
            setattr(context, key, int(bool(operation_data[key])))


def _collect_operation_results(
    results: list[tuple[bool, str | None, dict[str, Any] | None]],
    config: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Validate execution and preserve structured output returned by operations."""
    if len(results) != len(config):
        raise RuntimeError(
            f"usd-optimize returned {len(results)} results for {len(config)} requested operations."
        )
    operation_results: list[dict[str, Any]] = []
    for index, result in enumerate(results):
        success, error_message, output = result
        operation_name = config[index].get("operation", f"operation_{index}")
        if not success:
            raise RuntimeError(f"Operation failed: {operation_name}: {error_message}")
        if output is not None:
            operation_results.append({"operation": operation_name, "output": output})
    return operation_results


def _write_operation_results(result_path: Path, operation_results: list[dict[str, Any]]) -> None:
    """Persist operation output without mixing machine data into the worker log."""
    result_path.write_text(
        json.dumps({"operation_results": operation_results}, indent=2, default=str),
        encoding="utf-8",
    )


if __name__ == "__main__":
    raise SystemExit(main())
