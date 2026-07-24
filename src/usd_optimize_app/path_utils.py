from pathlib import Path

from usd_optimize_app.constants import DEFAULT_OUTPUT_SUFFIX, SUPPORTED_USD_EXTENSIONS
from usd_optimize_app.errors import OptimizeError


def ensure_supported_usd_path(file_path: Path) -> Path:
    resolved_file_path = file_path.expanduser().resolve()
    if resolved_file_path.suffix.lower() not in SUPPORTED_USD_EXTENSIONS:
        extension_names = ", ".join(sorted(SUPPORTED_USD_EXTENSIONS))
        message = (
            f"Unsupported USD extension: {resolved_file_path.suffix}. Expected {extension_names}."
        )
        raise OptimizeError(message)
    return resolved_file_path


def default_output_path(input_file_path: Path) -> Path:
    return input_file_path.with_name(
        f"{input_file_path.stem}{DEFAULT_OUTPUT_SUFFIX}{input_file_path.suffix}"
    )


def default_report_path(output_file_path: Path) -> Path:
    return output_file_path.with_suffix(f"{output_file_path.suffix}.report.json")


def default_log_path(output_file_path: Path) -> Path:
    return output_file_path.with_suffix(f"{output_file_path.suffix}.log")
