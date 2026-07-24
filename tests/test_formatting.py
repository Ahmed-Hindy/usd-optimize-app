from usd_optimize_app.formatting import format_file_size


def test_format_file_size_handles_missing_and_scaled_values() -> None:
    assert format_file_size(None) == "missing"
    assert format_file_size(900) == "900 B"
    assert format_file_size(2048) == "2.0 KB"
    assert format_file_size(2 * 1024 * 1024) == "2.0 MB"
