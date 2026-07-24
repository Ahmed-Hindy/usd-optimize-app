"""Reviewed GUI formatting for structured operation results."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

_UNREVIEWED_MESSAGE = "No reviewed formatter exists. See the JSON report for raw results."
_INVALID_OVERLAP_MESSAGE = "Invalid overlap-analysis result. See the JSON report for raw results."


def format_analysis_results(operation_results: list[dict[str, Any]]) -> str:
    """Format reviewed analysis results for the GUI."""
    if not operation_results:
        return "No structured findings."

    sections = [_format_operation_result(result) for result in operation_results]
    return "\n\n".join(sections)


def _format_operation_result(result: Mapping[str, Any]) -> str:
    operation_name = result.get("operation")
    if operation_name == "findOverlappingMeshes":
        return _format_overlapping_meshes(result)

    heading = str(operation_name or "Unknown operation")
    return f"{heading}\n{_UNREVIEWED_MESSAGE}"


def _format_overlapping_meshes(result: Mapping[str, Any]) -> str:
    analysis = _overlap_analysis_payload(result)
    if analysis is None:
        return f"Find overlaps\n{_INVALID_OVERLAP_MESSAGE}"

    mesh_paths = analysis.get("overlappingMeshes", [])
    if not _is_non_string_sequence(mesh_paths):
        return f"Find overlaps\n{_INVALID_OVERLAP_MESSAGE}"

    lines = ["Find overlaps", f"Overlapping Meshes ({len(mesh_paths)})"]
    if mesh_paths:
        lines.extend(f"  • {mesh_path}" for mesh_path in mesh_paths)
    else:
        lines.append("  None")

    if "suppressedOverlaps" in analysis:
        lines.append(f"Suppressed Overlaps: {analysis['suppressedOverlaps']}")
    if "usedGpu" in analysis:
        lines.append(f"Used GPU: {_format_bool(analysis['usedGpu'])}")
    return "\n".join(lines)


def _overlap_analysis_payload(result: Mapping[str, Any]) -> Mapping[str, Any] | None:
    output = result.get("output")
    if not isinstance(output, Mapping):
        return None
    analysis = output.get("analysis")
    return analysis if isinstance(analysis, Mapping) else None


def _is_non_string_sequence(value: object) -> bool:
    return isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray))


def _format_bool(value: object) -> str:
    if isinstance(value, bool):
        return "Yes" if value else "No"
    return str(value)
