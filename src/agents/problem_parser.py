from __future__ import annotations

import re
from typing import Any

from src.agents.base import BaseAgent


class ProblemParserAgent(BaseAgent):
    name = "ProblemParserAgent"

    KEYWORD_CANDIDATES = [
        "预测",
        "评价",
        "优化",
        "分类",
        "聚类",
        "回归",
        "时间序列",
        "相关性",
        "灵敏度",
        "仿真",
        "规划",
        "数据预处理",
    ]

    def run(self, raw_problem: dict[str, Any], raw_data: list[dict[str, Any]]) -> dict[str, Any]:
        text = raw_problem.get("content", "") or ""
        normalized = re.sub(r"\r\n?", "\n", text).strip()
        paragraphs = [p.strip() for p in re.split(r"\n\s*\n|(?<=。)\s*\n", normalized) if p.strip()]
        questions = self._extract_questions(normalized)
        keywords = [kw for kw in self.KEYWORD_CANDIDATES if kw in normalized]
        data_files = [
            {
                "name": item.get("name"),
                "type": item.get("type"),
                "columns": [table.get("columns", []) for table in item.get("tables", [])],
                "error": item.get("error"),
            }
            for item in raw_data
        ]
        problem_type = self._infer_problem_type(normalized, keywords, raw_data)

        return {
            "agent": self.name,
            "llm_trace": self.llm_client.complete_json(
                "problem_parser",
                {"problem_chars": len(normalized), "data_file_count": len(raw_data)},
            ),
            "background": paragraphs[0] if paragraphs else normalized[:500],
            "data_description": self._describe_data(raw_data),
            "questions": questions,
            "keywords": keywords or ["数据分析", "建模", "可视化"],
            "problem_type": problem_type,
            "data_files": data_files,
            "source_path": raw_problem.get("path"),
        }

    def _extract_questions(self, text: str) -> list[dict[str, Any]]:
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        question_lines = []
        pattern = re.compile(r"^(问题\s*\d+|第\s*\d+\s*问|[\(（]\d+[\)）]|\d+[\.、])")
        for line in lines:
            if pattern.match(line):
                question_lines.append(line)
        if not question_lines:
            question_lines = [line for line in lines if any(token in line for token in ("请", "要求", "建立", "分析", "预测"))]
        if not question_lines and text:
            question_lines = [text[:400]]

        questions = []
        for idx, line in enumerate(question_lines, start=1):
            questions.append(
                {
                    "id": f"Q{idx}",
                    "text": line,
                    "objective": self._infer_objective(line),
                    "expected_outputs": ["数值结果", "图表", "文字解释"],
                }
            )
        return questions

    def _infer_objective(self, text: str) -> str:
        if any(word in text for word in ("预测", "估计", "趋势")):
            return "prediction"
        if any(word in text for word in ("优化", "最优", "规划", "分配")):
            return "optimization"
        if any(word in text for word in ("评价", "排名", "指标", "综合")):
            return "evaluation"
        if any(word in text for word in ("分类", "聚类", "识别")):
            return "classification"
        return "descriptive_modeling"

    def _infer_problem_type(self, text: str, keywords: list[str], raw_data: list[dict[str, Any]]) -> str:
        if "优化" in keywords or "规划" in keywords:
            return "optimization"
        if "预测" in keywords or "时间序列" in keywords:
            return "prediction"
        if "评价" in keywords:
            return "evaluation"
        if any(item.get("tables") for item in raw_data):
            return "data_driven_analysis"
        if "仿真" in text:
            return "simulation"
        return "general_modeling"

    def _describe_data(self, raw_data: list[dict[str, Any]]) -> str:
        if not raw_data:
            return "未提供独立数据文件，主要依据题面文本开展建模。"
        parts = []
        for item in raw_data:
            if item.get("error"):
                parts.append(f"{item.get('name')}: 读取失败，{item.get('error')}")
                continue
            table_desc = []
            for table in item.get("tables", []):
                columns = ", ".join(table.get("columns", []))
                table_desc.append(f"{table.get('name')} 含字段：{columns}")
            parts.append(f"{item.get('name')} ({item.get('type')}): " + "; ".join(table_desc))
        return "\n".join(parts)

