from __future__ import annotations

from pathlib import Path
from typing import Any


def compute_metrics(state: Any, runtime_seconds: float, expected_problem_type: str | None = None) -> dict[str, Any]:
    report_path = Path(state.paper.get("report_path", "")) if state.paper else Path()
    report_text = report_path.read_text(encoding="utf-8") if report_path.exists() else ""
    required_sections = ["摘要", "问题重述", "模型假设", "各小问模型建立与求解", "结果分析", "模型评价", "附录代码"]
    coverage = _question_coverage(state, report_text)
    model_alignment = 1.0
    if expected_problem_type:
        actual = state.parsed_problem.get("problem_type", "")
        model_alignment = 1.0 if expected_problem_type in actual or actual in expected_problem_type else 0.5
    return {
        "end_to_end_success": bool(state.paper.get("report_path")),
        "code_execution_success": bool(state.execution_result.get("success")),
        "report_completeness_score": sum(1 for section in required_sections if section in report_text) / len(required_sections),
        "question_coverage_score": coverage,
        "data_usage_score": 1.0 if state.raw_data else 0.5,
        "figure_count": len(state.result_analysis.get("figures", [])),
        "model_alignment_score": model_alignment,
        "report_quality_score": state.report_quality.get("final_score", 0),
        "consistency_score": state.consistency_check.get("consistency_score", 0),
        "result_sanity_score": state.result_sanity_check.get("sanity_score", 0),
        "repair_iterations": max(0, len(state.execution_attempts) - 1),
        "runtime_seconds": round(runtime_seconds, 3),
    }


def _question_coverage(state: Any, report_text: str) -> float:
    questions = state.parsed_problem.get("questions", [])
    if not questions:
        return 1.0 if report_text else 0.0
    covered = sum(1 for question in questions if question.get("id", "") in report_text)
    return covered / len(questions)
