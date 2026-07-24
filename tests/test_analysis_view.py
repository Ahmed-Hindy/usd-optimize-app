"""Tests for human-readable analysis formatting."""

from usd_optimize_app.gui.analysis_view import format_analysis_results


def test_format_analysis_results_uses_headings_counts_and_bullets() -> None:
    """Convert nested native analysis output into readable text."""
    formatted = format_analysis_results(
        [
            {
                "operation": "findOverlappingMeshes",
                "output": {
                    "analysis": {
                        "overlappingMeshes": ["/World/First", "/World/Second"],
                        "suppressedOverlaps": 0,
                        "usedGpu": False,
                    }
                },
            }
        ]
    )

    assert formatted == (
        "Find overlaps\n"
        "Overlapping Meshes (2)\n"
        "  • /World/First\n"
        "  • /World/Second\n"
        "Suppressed Overlaps: 0\n"
        "Used GPU: No"
    )


def test_format_analysis_results_handles_empty_findings() -> None:
    formatted = format_analysis_results(
        [
            {
                "operation": "findOverlappingMeshes",
                "output": {"analysis": {"overlappingMeshes": []}},
            }
        ]
    )

    assert formatted == "Find overlaps\nOverlapping Meshes (0)\n  None"


def test_format_analysis_results_rejects_unreviewed_operations() -> None:
    formatted = format_analysis_results(
        [{"operation": "futureAnalysis", "output": {"analysis": {"value": 1}}}]
    )

    assert formatted == (
        "futureAnalysis\nNo reviewed formatter exists. See the JSON report for raw results."
    )


def test_format_analysis_results_rejects_malformed_overlap_results() -> None:
    formatted = format_analysis_results(
        [
            {
                "operation": "findOverlappingMeshes",
                "output": {"analysis": {"overlappingMeshes": "not-a-list"}},
            }
        ]
    )

    assert formatted == (
        "Find overlaps\nInvalid overlap-analysis result. See the JSON report for raw results."
    )
