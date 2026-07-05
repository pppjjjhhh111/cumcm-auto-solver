from pathlib import Path
from uuid import uuid4

from src.tools.report_quality_checker import ReportQualityChecker


def test_report_quality_checker_writes_json_and_summary() -> None:
    root = Path(__file__).resolve().parents[1]
    output_root = root / "outputs" / "test_runs" / f"report_quality_{uuid4().hex}"
    logs_dir = output_root / "logs"
    reports_dir = output_root / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    report_path = reports_dir / "solution_report.md"
    headings = "\n\n".join(
        f"## {section}\n\n内容。"
        for section in ReportQualityChecker.REQUIRED_SECTIONS
    )
    report_path.write_text(
        "# 数学建模论文草稿\n\n"
        f"{headings}\n\n"
        "$$\\hat y = wx + b$$\n\n"
        "Q1 linear_regression total_score data_fit_score interpretability_score outputs/figures/trend.svg 图表\n",
        encoding="utf-8",
    )

    checker = ReportQualityChecker(logs_dir=logs_dir, reports_dir=reports_dir)
    result = checker.check(
        report_path=report_path,
        parsed_problem={"questions": [{"id": "Q1", "text": "预测趋势"}]},
        selected_model={"model_selection_trace": {"task_traces": [{"task_id": "Q1", "selected_model": {"name": "linear_regression"}}]}},
        formulas={"latex_blocks": [{"latex": "\\hat y = wx + b"}]},
        figure_plan={"figure_plan": [{"figure_id": "fig1"}]},
        execution_result={"success": True},
        consistency_check={"consistency_score": 100},
    )

    assert result["final_score"] >= 90
    assert result["quality_level"] in {"excellent_draft", "solid_draft"}
    assert (logs_dir / "report_quality_check.json").exists()
    assert (reports_dir / "report_quality_summary.md").exists()
