from __future__ import annotations

from typing import Any

from src.agents.base import BaseAgent


class TaskDecomposerAgent(BaseAgent):
    name = "TaskDecomposerAgent"

    def run(self, parsed_problem: dict[str, Any]) -> dict[str, Any]:
        tasks = []
        for question in parsed_problem.get("questions", []):
            qid = question.get("id", "Q")
            objective = question.get("objective", "descriptive_modeling")
            tasks.extend(
                [
                    {
                        "id": f"{qid}.1",
                        "question_id": qid,
                        "task_type": "data_preprocessing",
                        "description": "整理输入数据，识别字段类型、缺失值、异常值和可用于建模的核心变量。",
                        "inputs": ["problem_statement", "data_files"],
                        "outputs": ["clean_data_profile", "summary_statistics"],
                    },
                    {
                        "id": f"{qid}.2",
                        "question_id": qid,
                        "task_type": objective,
                        "description": f"围绕 {question.get('text', '')} 建立可解释、可复现的数学模型。",
                        "inputs": ["clean_data_profile", "selected_strategy"],
                        "outputs": ["model_outputs", "figures"],
                    },
                    {
                        "id": f"{qid}.3",
                        "question_id": qid,
                        "task_type": "result_interpretation",
                        "description": "解释模型结果，形成论文中的结论、局限性和可视化支撑。",
                        "inputs": ["model_outputs", "figures"],
                        "outputs": ["result_narrative", "paper_sections"],
                    },
                ]
            )
        return {
            "agent": self.name,
            "llm_trace": self.llm_client.complete_json("task_decomposer", {"question_count": len(parsed_problem.get("questions", []))}),
            "tasks": tasks,
            "dependency_notes": "每个小问按 数据预处理 -> 模型建立与求解 -> 结果解释 串联执行。",
        }

