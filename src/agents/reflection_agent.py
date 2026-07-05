from __future__ import annotations

from typing import Any

from src.agents.base import BaseAgent
from src.utils.json_utils import write_json


class ReflectionAgent(BaseAgent):
    """Check draft solution quality and decide whether one revision is needed."""

    name = "ReflectionAgent"

    def run(
        self,
        parsed_problem: dict[str, Any],
        sub_tasks: dict[str, Any],
        selected_strategy: dict[str, Any],
        generated_code: dict[str, Any],
        execution_results: dict[str, Any],
        figures: list[str] | dict[str, Any],
        validation_results: dict[str, Any],
        draft_report: dict[str, Any],
    ) -> dict[str, Any]:
        markdown = draft_report.get("markdown", "")
        detected = []
        question_count = len(parsed_problem.get("questions", []))
        task_count = len(sub_tasks.get("tasks", []))
        figure_count = self._figure_count(figures, execution_results)
        if not execution_results.get("success"):
            detected.append("Generated code did not execute successfully.")
        if question_count == 0:
            detected.append("No explicit sub-questions were detected.")
        if "模型假设" not in markdown:
            detected.append("Report lacks a model assumptions section.")
        if "$" not in markdown and "\\[" not in markdown:
            detected.append("Report lacks mathematical expressions.")
        if figure_count == 0:
            detected.append("No generated figures were found.")
        if not validation_results.get("sensitivity_analysis"):
            detected.append("Sensitivity analysis suggestions are missing.")

        scores = {
            "completeness_score": self._score(100 - 8 * len(detected)),
            "question_alignment_score": self._score(90 if question_count and task_count else 65),
            "data_usage_score": self._score(90 if generated_code.get("code") else 65),
            "modeling_depth_score": self._score(85 if selected_strategy.get("selected_solution") else 70),
            "report_quality_score": self._score(88 if len(markdown) > 1000 else 65),
        }
        need_revision = bool(detected) and scores["completeness_score"] < 85
        result = {
            "agent": self.name,
            "llm_trace": self.llm_client.complete_json(
                "reflection",
                {"detected_problem_count": len(detected), "execution_success": execution_results.get("success")},
            ),
            **scores,
            "detected_problems": detected,
            "suggested_fixes": self._suggested_fixes(detected),
            "need_revision": need_revision,
            "revision_plan": self._revision_plan(detected) if need_revision else [],
        }
        if self.logs_dir is not None:
            write_json(self.logs_dir / "reflection_report.json", result)
        return result

    def _figure_count(self, figures: list[str] | dict[str, Any], execution_results: dict[str, Any]) -> int:
        if isinstance(figures, dict):
            planned = len(figures.get("figure_plan", []))
        else:
            planned = len(figures or [])
        generated = len(execution_results.get("generated_files", []))
        return max(planned, generated)

    def _score(self, value: int) -> int:
        return max(0, min(100, value))

    def _suggested_fixes(self, detected: list[str]) -> list[str]:
        mapping = {
            "Generated code did not execute successfully.": "Inspect execution_attempts.json and simplify generated code.",
            "No explicit sub-questions were detected.": "Add fallback sub-question coverage in the report.",
            "Report lacks a model assumptions section.": "Insert standard modeling assumptions.",
            "Report lacks mathematical expressions.": "Insert FormulaAgent latex blocks.",
            "No generated figures were found.": "Generate baseline EDA or result charts.",
            "Sensitivity analysis suggestions are missing.": "Add perturbation and robustness checks.",
        }
        return [mapping.get(item, item) for item in detected]

    def _revision_plan(self, detected: list[str]) -> list[dict[str, str]]:
        return [{"issue": item, "action": fix} for item, fix in zip(detected, self._suggested_fixes(detected))]
