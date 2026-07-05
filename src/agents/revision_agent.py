from __future__ import annotations

from typing import Any

from src.agents.base import BaseAgent


class RevisionAgent(BaseAgent):
    """Apply one conservative revision pass based on reflection output."""

    name = "RevisionAgent"

    def run(
        self,
        reflection_report: dict[str, Any],
        selected_strategy: dict[str, Any],
        generated_code: dict[str, Any],
        validation_results: dict[str, Any],
        draft_report: dict[str, Any],
    ) -> dict[str, Any]:
        revised_validation = dict(validation_results)
        revised_report = dict(draft_report)
        markdown = revised_report.get("markdown", "")
        if reflection_report.get("need_revision"):
            appendix = self._revision_appendix(reflection_report)
            if appendix not in markdown:
                markdown = markdown.rstrip() + "\n\n" + appendix + "\n"
            revised_report["markdown"] = markdown
            report_path = revised_report.get("report_path")
            if report_path:
                from pathlib import Path

                Path(report_path).write_text(markdown, encoding="utf-8")
            revised_validation.setdefault("revision_notes", reflection_report.get("suggested_fixes", []))
        return {
            "agent": self.name,
            "llm_trace": self.llm_client.complete_json(
                "revision",
                {"need_revision": reflection_report.get("need_revision", False)},
            ),
            "selected_strategy": selected_strategy,
            "generated_code": generated_code,
            "validation_results": revised_validation,
            "draft_report": revised_report,
            "revision_applied": bool(reflection_report.get("need_revision")),
        }

    def _revision_appendix(self, reflection_report: dict[str, Any]) -> str:
        fixes = "\n".join(f"- {item}" for item in reflection_report.get("suggested_fixes", [])) or "- No revision needed."
        return f"""## 模型反思与改进说明

系统完成初稿后进行了质量反思检查。主要建议如下：

{fixes}
"""
