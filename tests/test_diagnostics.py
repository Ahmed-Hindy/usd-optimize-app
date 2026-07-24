from usd_optimize_app.diagnostics import parse_stage_metrics, parse_stage_stats


def test_parse_stage_stats_reads_worker_table() -> None:
    output = """
| Prim Type  Count  Inactive  Invisible |
| Sphere     1      0         0         |
| Xform      1      1         0         |
| Total      2      1         0         |
"""

    stats = parse_stage_stats(output)

    assert [(stat.prim_type, stat.count, stat.inactive, stat.invisible) for stat in stats] == [
        ("Sphere", "1", "0", "0"),
        ("Xform", "1", "1", "0"),
        ("Total", "2", "1", "0"),
    ]


def test_parse_stage_stats_retains_annotated_counts_and_metrics() -> None:
    output = """
| Faces: 1,236 |
| Vertices: 1,286 |
| Renderable Geometries: 1 |
| Material    1 (1 unique)              0         --        |
| Mesh        1 (4 disjoint, 1 unique)  0         0         |
"""

    stats = parse_stage_stats(output)
    metrics = parse_stage_metrics(output)

    assert [(stat.prim_type, stat.count) for stat in stats] == [
        ("Material", "1 (1 unique)"),
        ("Mesh", "1 (4 disjoint, 1 unique)"),
    ]
    assert metrics.faces == 1236
    assert metrics.vertices == 1286
    assert metrics.renderable_geometries == 1
