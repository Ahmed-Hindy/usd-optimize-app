"""Shared human-readable formatting helpers."""

from __future__ import annotations

_BYTES_PER_KIBIBYTE = 1024
_BYTES_PER_MEBIBYTE = _BYTES_PER_KIBIBYTE * _BYTES_PER_KIBIBYTE


def format_file_size(size_bytes: int | None) -> str:
    """Format a byte count for compact UI and report output.

    Args:
        size_bytes: File size in bytes, or ``None`` when the file is unavailable.

    Returns:
        A compact byte, KB, or MB string.
    """
    if size_bytes is None:
        return "missing"
    if size_bytes < _BYTES_PER_KIBIBYTE:
        return f"{size_bytes} B"
    if size_bytes < _BYTES_PER_MEBIBYTE:
        return f"{size_bytes / _BYTES_PER_KIBIBYTE:.1f} KB"
    return f"{size_bytes / _BYTES_PER_MEBIBYTE:.1f} MB"
