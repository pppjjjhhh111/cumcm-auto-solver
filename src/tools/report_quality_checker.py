from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from src.utils.json_utils import write_json


class ReportQualityChecker:
    """Score generated Markdown reports against modeling-paper requirements."""

    REQUIRED_SECTIONS = [
        "摘要",
        "关键词",
        "问题重述",
        "问题分析",
        "建模方案比较与选择",
        "模型选择理由",
        "模型假设",
        "符号说明",
        "数据预处理与探索性分析",
        "各小问模型建立与求解",
        "结果分析",
        "灵敏度分析",
        "模型反思与改进说明",
        "模型评价",
        "参考文献",
        "附录代码",
    ]

    def __init__(self, logs_dir: Path | None = None, reports_dir: Path | None = None) -> None:
        self.logs_dir = logs_dir
        self.reports_dir = reports_dir

    def check(
        self,
        report_path: Path,
        parsed_problem: dict[str, Any],
        selected_model: dict[str, Any],
        formulas: dict[str, Any],
        figure_plan: dict[str, Any],
        execution_result: dict[str, Any],
        consistency_check: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        markdown = report_path.read_text(encoding="utf-8") if report_path.exists() else ""
        section_score, section_details = self._section_score(markdown)
        question_score, question_details = self._question_coverage_score(markdown, parsed_problem)
        formula_score = self._formula_score(markdown, formulas)
        figure_score = self._figure_score(markdown, figure_plan)
        model_score = self._model_reasoning_score(markdown, selected_model)
        execution_score = 100 if execution_result.get("success") else 35
        consistency_score = (consistency_check or {}).get("consistency_score", 0)
        final_score = round(
            section_score * 0.22
            + question_score * 0.16
            + formula_score * 0.14
            + figure_score * 0.12
            + model_score * 0.14
            + execution_score * 0.10
            + consistency_score * 0.12,
            2,
        )
        result = {
            "checker": "ReportQualityChecker",
            "report_path": str(report_path),
            "final_score": final_score,
            "quality_level": self._quality_level(final_score),
            "scores": {
                "section_completeness": section_score,
                "question_coverage": question_score,
                "formula_presence": formula_score,
                "figure_integration": figure_score,
                "model_selection_reasoning": model_score,
                "execution_reliability": execution_score,
                "artifact_consistency": consistency_score,
            },
            "section_details": section_details,
            "question_details": question_details,
            "issues": self._issues(section_details, question_details, formula_score, figure_score, model_score, execution_result),
            "suggested_fixes": self._suggestions(section_details, question_details, formula_score, figure_score, model_score, execution_result),
        }
        if self.logs_dir is not None:
            write_json(self.logs_dir / "report_quality_check.json", result)
        if self.reports_dir is not None:
            self.write_summary(self.reports_dir / "report_quality_summary.md", result)
        return result

    def write_summary(self, path: Path, result: dict[str, Any]) -> Path:
        scores = result.get("scores", {})
        lines = [
            "# Report Quality Summary",
            "",
            f"- Final score: {result.get('final_score')}",
            f"- Quality level: {result.get('quality_level')}",
            "",
            "## Scores",
            "",
        ]
        for key, value in scores.items():
            lines.append(f"- {key}: {value}")
        lines.extend(["", "## Issues", ""])
        for issue in result.get("issues", []):
            lines.append(f"- {issue}")
        lines.extend(["", "## Suggested Fixes", ""])
        for suggestion in result.get("suggested_fixes", []):
            lines.append(f"- {suggestion}")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return path

    def _section_score(self, markdown: str) -> tuple[float, list[dict[str, Any]]]:
        details = []
        for section in self.REQUIRED_SECTIONS:
            present = section in markdown
            details.append({"section": section, "present": present})
        score = round(100 * sum(1 for item in details if item["present"]) / max(len(details), 1), 2)
        return score, details

    def _question_coverage_score(self, markdown: str, parsed_problem: dict[str, Any]) -> tuple[float, list[dict[str, Any]]]:
        questions = parsed_problem.get("questions", [])
        if not questions:
            return 70.0, [{"question_id": None, "covered": False, "note": "No parsed questions were available."}]
        details = []
        for question in questions:
            qid = str(question.get("id", ""))
            text = str(question.get("text", ""))
            covered = bool(qid and qid in markdown) or bool(text[:16] and text[:16] in markdown)
            details.append({"question_id": qid, "covered": covered})
        score = round(100 * sum(1 for item in details if item["covered"]) / len(details), 2)
        return score, details

    def _formula_score(self, markdown: str, formulas: dict[str, Any]) -> float:
        latex_blocks = formulas.get("latex_blocks", [])
        markdown_math_blocks = len(re.findall(r"\$\$[\s\S]+?\$\$", markdown))
        if latex_blocks and markdown_math_blocks >= len(latex_blocks):
            return 100.0
        if latex_blocks or markdown_math_blocks:
            return 75.0
        return 35.0

    def _figure_score(self, markdown: str, figure_plan: dict[str, Any]) -> float:
        planned = figure_plan.get("figure_plan", [])
        figure_mentions = markdown.count("outputs/figures") + markdown.count("图表") + markdown.count("figure")
        if planned and figure_mentions >= min(len(planned), 3):
            return 100.0
        if planned or figure_mentions:
            return 70.0
        return 35.0

    def _model_reasoning_score(self, markdown: str, selected_model: dict[str, Any]) -> float:
        trace = selected_model.get("model_selection_trace", {})
        has_trace = bool(trace.get("task_traces"))
        reasoning_terms = ["total_score", "data_fit_score", "interpretability_score", "reportability_score", "选择理由", "得分"]
        matches = sum(1 for term in reasoning_terms if term in markdown)
        if has_trace and matches >= 3:
            return 100.0
        if has_trace or matches >= 2:
            return 75.0
        return 40.0

    def _issues(
        self,
        section_details: list[dict[str, Any]],
        question_details: list[dict[str, Any]],
        formula_score: float,
        figure_score: float,
        model_score: float,
        execution_result: dict[str, Any],
    ) -> list[str]:
        issues = []
        missing_sections = [item["section"] for item in section_details if not item["present"]]
        missing_questions = [item["question_id"] for item in question_details if not item["covered"]]
        if missing_sections:
            issues.append("Missing sections: " + ", ".join(missing_sections))
        if missing_questions:
            issues.append("Questions not clearly covered: " + ", ".join(str(item) for item in missing_questions))
        if formula_score < 80:
            issues.append("Formula integration is weak or absent.")
        if figure_score < 80:
            issues.append("Figure plan is weakly reflected in the report.")
        if model_score < 80:
            issues.append("Model selection reasoning needs more explicit score/rationale discussion.")
        if not execution_result.get("success"):
            issues.append("Code execution did not succeed; report results require manual review.")
        return issues or ["No blocking report quality issue detected."]

    def _suggestions(
        self,
        section_details: list[dict[str, Any]],
        question_details: list[dict[str, Any]],
        formula_score: float,
        figure_score: float,
        model_score: float,
        execution_result: dict[str, Any],
    ) -> list[str]:
        suggestions = []
        if any(not item["present"] for item in section_details):
            suggestions.append("Regenerate or revise the Markdown report to include all required CUMCM-style sections.")
        if any(not item["covered"] for item in question_details):
            suggestions.append("Add a dedicated subsection for every parsed question id and objective.")
        if formula_score < 80:
            suggestions.append("Insert LaTeX formula blocks and define all variables in the symbol table.")
        if figure_score < 80:
            suggestions.append("Reference planned/generated figures in result analysis with titles and captions.")
        if model_score < 80:
            suggestions.append("Add a model selection rationale table using model_selection_trace.json.")
        if not execution_result.get("success"):
            suggestions.append("Fix generated code, rerun execution, and regenerate result analysis before final submission.")
        return suggestions or ["Report is structurally acceptable for a draft; continue with expert polishing."]

    def _quality_level(self, score: float) -> str:
        if score >= 90:
            return "excellent_draft"
        if score >= 80:
            return "solid_draft"
        if score >= 65:
            return "needs_polish"
        return "needs_revision"
