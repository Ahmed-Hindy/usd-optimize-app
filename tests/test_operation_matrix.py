from pathlib import Path

from usd_optimize_app.operation_matrix import (
    OperationMatrixStep,
    build_operation_matrix_cases,
    run_operation_matrix,
)


def test_operation_matrix_classifies_special_cases() -> None:
    cases = {
        case.operation_name: case
        for case in build_operation_matrix_cases(
            [
                "generateAtlasUVs",
                "findOverlappingMeshes",
                "merge",
                "splitMeshes",
            ]
        )
    }

    assert cases["merge"].kind == "standard"
    assert cases["merge"].support_tier == "advanced"
    assert cases["generateAtlasUVs"].kind == "parameterized"
    assert cases["findOverlappingMeshes"].kind == "analysis"
    assert cases["findOverlappingMeshes"].support_tier == "supported"
    assert cases["findOverlappingMeshes"].expected == "pass"
    assert cases["splitMeshes"].support_tier == "requires_configuration"


def test_operation_matrix_skips_opt_in_categories_and_writes_manifest(
    monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        "usd_optimize_app.operation_matrix.check_environment",
        lambda: type("Status", (), {"is_usable": True, "errors": ()})(),
    )
    monkeypatch.setattr(
        "usd_optimize_app.operation_matrix.list_available_operations",
        lambda: ["merge", "generateAtlasUVs", "findOccludedMeshes"],
    )

    def fake_run_case(case, input_path, output_dir):
        del input_path, output_dir
        return OperationMatrixStep(
            operation_name=case.operation_name,
            kind=case.kind,
            support_tier=case.support_tier,
            expected=case.expected,
            status="passed",
            output_path=None,
            output_reopened=True,
        )

    monkeypatch.setattr("usd_optimize_app.operation_matrix._run_case", fake_run_case)
    input_path = tmp_path / "input.usda"
    input_path.write_text("#usda 1.0", encoding="utf-8")
    result = run_operation_matrix(input_path, tmp_path / "matrix")

    steps = {step.operation_name: step for step in result.steps}
    assert steps["merge"].status == "passed"
    assert steps["generateAtlasUVs"].status == "skipped"
    assert steps["findOccludedMeshes"].status == "skipped"
    assert result.manifest_path.is_file()
