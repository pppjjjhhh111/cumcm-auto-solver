from __future__ import annotations

from pathlib import Path
from typing import Any

from src.utils.json_utils import write_json


class ConsistencyChecker:
    """Check cross-artifact consistency after a workflow run."""

    def __init__(self, logs_dir: Path | None = None) -> None:
        self.logs_dir = logs_dir

    def check(
        self,
        parsed_problem: dict[str, Any],
        decomposed_tasks: dict[str, Any],
        selected_model: dict[str, Any],
        formulas: dict[str, Any],
        figure_plan: dict[str, Any],
        execution_result: dict[str, Any],
        result_analysis: dict[str, Any],
        paper: dict[str, Any],
    ) -> dict[str, Any]:
        questions = parsed_problem.get("questions", [])
        tasks = decomposed_tasks.get("tasks", [])
        selected_items = selected_model.get("selected_strategies", [])
        latex_blocks = formulas.get("latex_blocks", [])
        figures = figure_plan.get("figure_plan", [])
        markdown = paper.get("markdown", "")

        checks = [
            self._check_count("questions_have_tasks", len(questions), self._question_task_count(questions, tasks)),
            self._check_count("tasks_have_selected_models", len(tasks), len([item for item in selected_items if item.get("selected")])),
            self._check_presence("selected_solution_exists", bool(selected_model.get("selected_solution"))),
            self._check_presence("formula_blocks_exist", bool(latex_blocks)),
            self._check_presence("figure_plan_exists", bool(figures)),
            self._check_presence("execution_succeeded", bool(execution_result.get("success"))),
            self._check_presence("result_analysis_ok", result_analysis.get("status") == "ok"),
            self._check_report_mentions_questions(questions, markdown),
            self._check_report_mentions_models(selected_items, markdown),
        ]
        passed = sum(1 for item in checks if item["status"] == "pass")
        warnings = [item for item in checks if item["status"] == "warning"]
        failures = [item for item in checks if item["status"] == "fail"]
        result = {
            "checker": "ConsistencyChecker",
            "passed_checks": passed,
            "total_checks": len(checks),
            "consistency_score": round(100 * passed / max(len(checks), 1), 2),
            "status": "pass" if not failures else "needs_review",
            "checks": checks,
            "warnings": warnings,
            "failures": failures,
            "suggested_fixes": self._suggest_fixes(failures, warnings),
        }
        if self.logs_dir is not None:
            write_json(self.logs_dir / "consistency_check.json", result)
        return result

    def _question_task_count(self, questions: list[dict[str, Any]], tasks: list[dict[str, Any]]) -> int:
        question_ids = {str(question.get("id")) for question in questions}
        covered = set()
        for task in tasks:
            question_id = str(task.get("question_id") or str(task.get("id", "")).split(".")[0])
            if question_id in question_ids:
                covered.add(question_id)
        return len(covered)

    def _check_count(self, name: str, expected: int, actual: int) -> dict[str, Any]:
        if expected == 0:
            return {"name": name, "status": "warning", "expected": expected, "actual": actual, "message": "No source items were detected."}
        if actual >= expected:
            return {"name": name, "status": "pass", "expected": expected, "actual": actual, "message": "Coverage is complete."}
        return {"name": name, "status": "fail", "expected": expected, "actual": actual, "message": "Coverage is incomplete."}

    def _check_presence(self, name: str, present: bool) -> dict[str, Any]:
        return {
            "name": name,
            "status": "pass" if present else "fail",
            "expected": True,
            "actual": present,
            "message": "Required artifact exists." if present else "Required artifact is missing or failed.",
        }

    def _check_report_mentions_questions(self, questions: list[dict[str, Any]], markdown: str) -> dict[str, Any]:
        missing = [str(question.get("id")) for question in questions if question.get("id") and str(question.get("id")) not in markdown]
        status = "pass" if not missing else "fail"
        return {
            "name": "report_mentions_questions",
            "status": status,
            "expected": [question.get("id") for question in questions],
            "actual_missing": missing,
            "message": "Report references every parsed question." if not missing else "Report misses one or more question ids.",
        }

    def _check_report_mentions_models(self, selected_items: list[dict[str, Any]], markdown: str) -> dict[str, Any]:
        model_names = []
        for item in selected_items:
            selected = item.get("selected") or {}
            name = selected.get("name") or selected.get("model_id")
            if name and name not in model_names:
                model_names.append(name)
        missing = [name for name in model_names if name not in markdown]
        status = "pass" if not missing else "warning"
        return {
            "name": "report_mentions_selected_models",
            "status": status,
            "expected": model_names,
            "actual_missing": missing,
            "message": "Report mentions selected model names." if not missing else "Some selected model names are not explicitly mentioned.",
        }

    def _suggest_fixes(self, failures: list[dict[str, Any]], warnings: list[dict[str, Any]]) -> list[str]:
        suggestions = []
        names = {item.get("name") for item in failures + warnings}
        if "questions_have_tasks" in names:
            suggestions.append("Re-run task decomposition or manually add missing sub-tasks for uncovered questions.")
        if "tasks_have_selected_models" in names:
            suggestions.append("Inspect model_recommendations.json and model_selection_trace.json for tasks without selected models.")
        if "formula_blocks_exist" in names:
            suggestions.append("Add at least one formula block per core modeling task when the task is mathematical.")
        if "figure_plan_exists" in names:
            suggestions.append("Add figure planning entries for exploratory analysis, results, and sensitivity analysis.")
        if "execution_succeeded" in names or "result_analysis_ok" in names:
            suggestions.append("Inspect execution_attempts.json and repair the generated analysis code before trusting results.")
        if "report_mentions_questions" in names or "report_mentions_selected_models" in names:
            suggestions.append("Regenerate or revise the report so selected models and every question are explicitly discussed.")
        return suggestions or ["No major consistency fixes are required."]
