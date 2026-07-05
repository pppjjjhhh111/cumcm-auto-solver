from pathlib import Path
from uuid import uuid4

from src.tools.consistency_checker import ConsistencyChecker


def test_consistency_checker_detects_complete_artifacts() -> None:
    root = Path(__file__).resolve().parents[1]
    logs_dir = root / "outputs" / "test_runs" / f"consistency_{uuid4().hex}" / "logs"
    checker = ConsistencyChecker(logs_dir=logs_dir)

    result = checker.check(
        parsed_problem={"questions": [{"id": "Q1", "text": "预测"}]},
        decomposed_tasks={"tasks": [{"id": "Q1.1", "question_id": "Q1"}]},
        selected_model={
            "selected_solution": {"solution_name": "conservative_solution"},
            "selected_strategies": [
                {"task_id": "Q1.1", "selected": {"name": "linear_regression", "model_id": "linear_regression"}}
            ],
        },
        formulas={"latex_blocks": [{"latex": "y=x"}]},
        figure_plan={"figure_plan": [{"figure_id": "fig1"}]},
        execution_result={"success": True},
        result_analysis={"status": "ok"},
        paper={"markdown": "## Q1\n\nlinear_regression\n"},
    )

    assert result["status"] == "pass"
    assert result["consistency_score"] >= 90
    assert (logs_dir / "consistency_check.json").exists()


def test_consistency_checker_flags_missing_model_and_report_coverage() -> None:
    checker = ConsistencyChecker()

    result = checker.check(
        parsed_problem={"questions": [{"id": "Q1", "text": "预测"}]},
        decomposed_tasks={"tasks": [{"id": "Q1.1", "question_id": "Q1"}]},
        selected_model={"selected_strategies": [{"task_id": "Q1.1", "selected": None}]},
        formulas={},
        figure_plan={},
        execution_result={"success": False},
        result_analysis={"status": "execution_failed"},
        paper={"markdown": "空报告"},
    )

    assert result["status"] == "needs_review"
    assert result["failures"]
    assert result["suggested_fixes"]
