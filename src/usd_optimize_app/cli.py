"""Command line interface for USD Optimize App."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from usd_optimize_app.backend import OptimizeJobSettings, run_batch_jobs, run_optimize_job
from usd_optimize_app.errors import UsdOptimizeAppError
from usd_optimize_app.operation_matrix import run_operation_matrix
from usd_optimize_app.operation_support import get_operation_support
from usd_optimize_app.presets import load_all_presets, load_preset
from usd_optimize_app.report_summary import (
    format_report_summary,
    load_report_summaries,
    summaries_to_json_data,
)
from usd_optimize_app.smoke_tests import (
    DEFAULT_EXTERNAL_SMOKE_PRESETS,
    DEFAULT_SMOKE_PRESETS,
    SmokeTestSettings,
    run_smoke_test,
)
from usd_optimize_app.usd_env import check_environment, list_available_operations


def main(argv: list[str] | None = None) -> int:
    """Run the command line interface.

    Args:
        argv: Optional command arguments. Uses process arguments when omitted.

    Returns:
        Process exit code.
    """
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        return args.func(args)
    except UsdOptimizeAppError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("Cancelled.", file=sys.stderr)
        return 130


def build_parser() -> argparse.ArgumentParser:
    """Build the top-level CLI parser.

    Returns:
        Configured argument parser.
    """
    parser = argparse.ArgumentParser(
        prog="usdopt",
        description="CLI wrapper for NVIDIA usd-optimize.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    doctor_parser = subparsers.add_parser("doctor", help="Check the usd-optimize environment.")
    doctor_parser.set_defaults(func=_run_doctor)

    list_ops_parser = subparsers.add_parser("list-ops", help="List usd-optimize operations.")
    list_ops_parser.set_defaults(func=_run_list_ops)

    list_presets_parser = subparsers.add_parser("list-presets", help="List bundled presets.")
    list_presets_parser.add_argument(
        "--all",
        action="store_true",
        help="Include developer-only validation presets.",
    )
    list_presets_parser.set_defaults(func=_run_list_presets)

    show_preset_parser = subparsers.add_parser("show-preset", help="Show preset JSON operations.")
    show_preset_parser.add_argument("preset", help="Preset name or path.")
    show_preset_parser.set_defaults(func=_run_show_preset)

    optimize_parser = subparsers.add_parser("optimize", help="Optimize a USD file.")
    optimize_parser.add_argument("--input", required=True, type=Path, help="Input USD file.")
    optimize_parser.add_argument("--output", type=Path, help="Output USD file.")
    optimize_parser.add_argument(
        "--preset",
        default="safe_publish",
        help="Preset name or JSON path.",
    )
    optimize_parser.add_argument(
        "--force",
        action="store_true",
        help="Replace an existing output file.",
    )
    optimize_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate request without writing USD.",
    )
    optimize_parser.set_defaults(func=_run_optimize)

    batch_parser = subparsers.add_parser(
        "batch", help="Optimize explicit USD inputs into one directory."
    )
    batch_parser.add_argument(
        "--input", action="append", required=True, type=Path, help="Input USD file."
    )
    batch_parser.add_argument(
        "--output-dir",
        type=Path,
        help="Output directory. Not needed for the diagnostics preset.",
    )
    batch_parser.add_argument("--preset", default="safe_publish", help="Bundled preset name.")
    batch_parser.add_argument(
        "--force", action="store_true", help="Replace existing batch outputs."
    )
    batch_parser.set_defaults(func=_run_batch)

    smoke_parser = subparsers.add_parser("smoke-test", help="Run operational smoke tests.")
    smoke_parser.add_argument(
        "--input",
        type=Path,
        help="USD fixture to test. Defaults to the sibling usd-optimize OpenUSD fixture.",
    )
    smoke_parser.add_argument(
        "--output-dir",
        type=Path,
        help="Directory for generated smoke-test outputs.",
    )
    smoke_parser.add_argument(
        "--preset",
        action="append",
        dest="presets",
        help="Preset to run. Can be supplied more than once.",
    )
    smoke_parser.add_argument(
        "--external-assets",
        action="store_true",
        help="Use the sibling usd-optimize CI external asset manifest/cache.",
    )
    smoke_parser.add_argument(
        "--asset-manifest",
        type=Path,
        help="External asset manifest path. Used with --external-assets.",
    )
    smoke_parser.add_argument(
        "--assets-dir",
        type=Path,
        help="Downloaded external asset cache. Used with --external-assets.",
    )
    smoke_parser.set_defaults(func=_run_smoke_test)

    matrix_parser = subparsers.add_parser(
        "operation-matrix",
        help="Run selected operation DLLs independently and save a result manifest.",
    )
    matrix_parser.add_argument("--input", required=True, type=Path, help="USD fixture to test.")
    matrix_parser.add_argument(
        "--output-dir",
        type=Path,
        help="Directory for per-operation outputs, logs, and operation-matrix.json.",
    )
    matrix_parser.add_argument(
        "--include-parameterized",
        action="store_true",
        help="Also try DLLs whose defaults need asset-specific settings.",
    )
    matrix_parser.add_argument(
        "--include-gpu",
        action="store_true",
        help="Also try potentially GPU-bound DLLs.",
    )
    matrix_parser.add_argument(
        "--include-special",
        action="store_true",
        help="Also try helper or explicitly destructive DLLs.",
    )
    matrix_parser.add_argument(
        "--all",
        action="store_true",
        help="Enable parameterized, GPU, and special DLL categories.",
    )
    matrix_parser.add_argument(
        "--strict",
        action="store_true",
        help="Return a non-zero exit code when a DLL expected to pass fails.",
    )
    matrix_parser.set_defaults(func=_run_operation_matrix)

    summary_parser = subparsers.add_parser(
        "report-summary",
        help="Summarize optimization report JSON files.",
    )
    summary_parser.add_argument(
        "--reports-dir",
        type=Path,
        default=Path("reports"),
        help="Directory to scan recursively for *.report.json files.",
    )
    summary_parser.add_argument(
        "--json",
        action="store_true",
        help="Write machine-readable JSON instead of a text table.",
    )
    summary_parser.set_defaults(func=_run_report_summary)

    gui_parser = subparsers.add_parser("gui", help="Open the PySide6 GUI.")
    gui_parser.set_defaults(func=_run_gui)

    return parser


def _run_doctor(_args: argparse.Namespace) -> int:
    status = check_environment()
    print("USD Optimize environment")
    print(f"  Runtime root: {status.runtime_root or 'not found'}")
    print(f"  Required Python: {status.required_python or 'unknown'}")
    print(f"  Current Python: {status.current_python}")
    print(f"  python dir: {_format_bool(status.has_python_dir)}")
    print(f"  usdpy dir: {_format_bool(status.has_usdpy_dir)}")
    print(f"  lib dir: {_format_bool(status.has_lib_dir)}")
    print(f"  extraLibs dir: {_format_bool(status.has_extra_libs_dir)}")
    print(f"  pxr import: {_format_bool(status.pxr_import_ok)}")
    print(f"  usd_optimize import: {_format_bool(status.usd_optimize_import_ok)}")
    if status.operation_count is not None:
        print(f"  operation count: {status.operation_count}")
    if status.errors:
        print("\nProblems:")
        for error in status.errors:
            print(f"  - {error}")
        return 1
    print("\nEnvironment looks usable.")
    return 0


def _run_list_ops(_args: argparse.Namespace) -> int:
    for operation_name in list_available_operations():
        support = get_operation_support(operation_name)
        print(f"{operation_name:28} {support.tier:23} {support.behavior:8} {support.reason}")
    return 0


def _run_list_presets(args: argparse.Namespace) -> int:
    presets = load_all_presets(include_developer=args.all)
    if not presets:
        print("No presets found.")
        return 1
    for preset in presets:
        print(f"{preset.name:20} {preset.risk:12} {preset.audience:10} {preset.display_name}")
    return 0


def _run_show_preset(args: argparse.Namespace) -> int:
    preset = load_preset(args.preset)
    preset_data = {
        "name": preset.name,
        "display_name": preset.display_name,
        "risk": preset.risk,
        "audience": preset.audience,
        "description": preset.description,
        "operations": preset.operations,
    }
    print(json.dumps(preset_data, indent=2))
    return 0


def _run_optimize(args: argparse.Namespace) -> int:
    preset = load_preset(args.preset)
    result = run_optimize_job(
        OptimizeJobSettings(
            input_path=args.input,
            output_path=args.output,
            preset_name=args.preset,
            force=args.force,
            dry_run=args.dry_run,
            write_output=preset.risk != "diagnostic",
        )
    )
    worker_output = result.worker_output
    operation_results = result.operation_results
    if args.dry_run:
        print(f"Dry run: {result.input_path}")
    elif worker_output:
        print(f"Diagnostics: {result.input_path}")
    else:
        print(f"Optimized: {result.output_path}")
    if result.report_path:
        print(f"Report: {result.report_path}")
    if result.log_path:
        print(f"Log: {result.log_path}")
    if worker_output:
        print(worker_output.rstrip())
    if result.warnings:
        print("Warnings:")
        for warning in result.warnings:
            print(f"  - {warning}")
    _print_operation_results(operation_results)
    return 0


def _run_batch(args: argparse.Namespace) -> int:
    """Run one bundled preset across the explicit batch input list."""
    results = run_batch_jobs(tuple(args.input), args.output_dir, args.preset, force=args.force)
    for result in results:
        if result.worker_output:
            print(f"Diagnostics: {result.input_path}")
            if result.report_path:
                print(f"Report: {result.report_path}")
            print(result.worker_output.rstrip())
            _print_operation_results(result.operation_results)
        else:
            print(f"Completed: {result.input_path} -> {result.output_path}")
    return 0


def _run_smoke_test(args: argparse.Namespace) -> int:
    default_presets = (
        DEFAULT_EXTERNAL_SMOKE_PRESETS if args.external_assets else DEFAULT_SMOKE_PRESETS
    )
    preset_names = tuple(args.presets) if args.presets else default_presets
    result = run_smoke_test(
        SmokeTestSettings(
            input_path=args.input,
            output_dir=args.output_dir,
            preset_names=preset_names,
            external_assets=args.external_assets,
            external_asset_manifest=args.asset_manifest,
            external_assets_dir=args.assets_dir,
        )
    )
    print("USD Optimize smoke test")
    print(f"  Runtime root: {result.runtime_root}")
    if result.input_path:
        print(f"  Input: {result.input_path}")
    else:
        asset_names = sorted({step.asset_name for step in result.steps})
        print(f"  Assets: {len(asset_names)}")
    print(f"  Output dir: {result.output_dir}")
    print(f"  Operation count: {result.operation_count}")
    print("\nPreset runs:")
    for step in result.steps:
        print(f"  - {step.asset_name} / {step.preset_name}: OK")
        if step.result.worker_output:
            print("    Output: none (analysis only)")
        else:
            print(f"    Output: {step.result.output_path}")
        if step.result.report_path:
            print(f"    Report: {step.result.report_path}")
        if step.result.log_path:
            print(f"    Log: {step.result.log_path}")
    print("\nSmoke test passed.")
    return 0


def _run_operation_matrix(args: argparse.Namespace) -> int:
    """Run isolated operation checks and print a concise outcome table."""
    result = run_operation_matrix(
        input_path=args.input,
        output_dir=args.output_dir,
        include_parameterized=args.include_parameterized or args.all,
        include_gpu=args.include_gpu or args.all,
        include_special=args.include_special or args.all,
    )
    print("USD Optimize operation matrix")
    print(f"  Input: {result.input_path}")
    print(f"  Output dir: {result.output_dir}")
    print(f"  Manifest: {result.manifest_path}")
    print("\nOperation runs:")
    for step in result.steps:
        status = step.status.upper()
        details = step.support_tier
        if step.kind == "analysis":
            details += ", analysis"
        if step.status == "failed" and step.expected == "allow_failure":
            details += ", allowed failure"
        print(f"  - {step.operation_name}: {status} ({details})")
        if step.error:
            print(f"    {step.error.splitlines()[0]}")
    print(f"\nUnexpected failures: {len(result.unexpected_failures)}")
    return 1 if args.strict and result.unexpected_failures else 0


def _run_report_summary(args: argparse.Namespace) -> int:
    summaries = load_report_summaries(args.reports_dir)
    if args.json:
        print(json.dumps(summaries_to_json_data(summaries), indent=2))
    else:
        print(format_report_summary(summaries))
    return 0


def _print_operation_results(operation_results: list[dict[str, object]]) -> None:
    """Print structured analysis data returned by an operation when available."""
    if not operation_results:
        return
    print("Operation results:")
    print(json.dumps(operation_results, indent=2))


def _run_gui(_args: argparse.Namespace) -> int:
    from usd_optimize_app.gui.app import main as gui_main

    return gui_main()


def _format_bool(value: bool) -> str:
    return "OK" if value else "MISSING"


if __name__ == "__main__":
    raise SystemExit(main())
