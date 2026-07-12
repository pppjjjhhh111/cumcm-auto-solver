from __future__ import annotations

from typing import Any

from src.agents.base import BaseAgent
from src.rag.reference_utils import count_references, reference_summary, select_references
from src.tools.model_zoo import ModelZoo
from src.utils.json_utils import write_json


class StrategyGeneratorAgent(BaseAgent):
    name = "StrategyGeneratorAgent"

    def __init__(self, *args: Any, model_zoo: ModelZoo | None = None, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.model_zoo = model_zoo or ModelZoo()

    def run(
        self,
        decomposed_tasks: dict[str, Any],
        data_profile: dict[str, Any] | None = None,
        retrieved_references: Any = None,
    ) -> dict[str, Any]:
        data_profile = data_profile or {}
        retrieved_references = retrieved_references or []
        strategies = []
        for task in decomposed_tasks.get("tasks", []):
            task_refs = self._references_for_task(task, retrieved_references)
            candidates = self._candidates_for(task, data_profile, task_refs)
            strategies.append(
                {
                    "task_id": task["id"],
                    "task_type": task["task_type"],
                    "task_description": task.get("description", ""),
                    "retrieved_references": task_refs,
                    "candidates": candidates,
                }
            )
        result = {
            "agent": self.name,
            "llm_trace": self.llm_client.complete_json(
                "strategy_generator",
                {
                    "task_count": len(decomposed_tasks.get("tasks", [])),
                    "source": "model_zoo",
                    "has_data_profile": bool(data_profile.get("files")),
                    "retrieved_reference_count": count_references(retrieved_references),
                },
            ),
            "recommendation_source": "config/model_zoo.yaml",
            "retrieved_references": retrieved_references,
            "data_profile_summary": data_profile.get("summary", {}),
            "strategies": strategies,
        }
        if self.logs_dir is not None:
            write_json(self.logs_dir / "model_recommendations.json", result)
        return result

    def _candidates_for(
        self,
        task: dict[str, Any],
        data_profile: dict[str, Any],
        retrieved_references: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        task_type = task.get("task_type", "general_modeling")
        description = task.get("description", "")
        data_type = self._infer_data_type(task, data_profile)
        recommended = self.model_zoo.recommend_models(
            problem_type=task_type,
            data_type=data_type,
            task_description=description,
            limit=3,
        )
        return [self._candidate_from_model(model, task, data_type, retrieved_references) for model in recommended[:3]]

    def _references_for_task(self, task: dict[str, Any], retrieved_references: Any) -> list[dict[str, Any]]:
        question_id = task.get("question_id") or str(task.get("id", "")).split(".")[0]
        return select_references(
            retrieved_references,
            purpose="strategy",
            question_id=str(question_id) if question_id else None,
            limit=5,
        )

    def _candidate_from_model(
        self,
        model: dict[str, Any],
        task: dict[str, Any],
        data_type: str,
        retrieved_references: list[dict[str, Any]],
    ) -> dict[str, Any]:
        advantages = model.get("advantages", [])
        limitations = model.get("limitations", [])
        input_requirements = model.get("input_requirements", [])
        workflow = model.get("typical_workflow", [])
        difficulty = self._implementation_difficulty(model)
        method = "; ".join(workflow[:4]) if workflow else model.get("paper_expression_template", "")
        reference_note = reference_summary(retrieved_references, limit=2)
        base_reason = model.get("fit_reason") or (
            f"{model.get('name')} is suitable for {task.get('task_type')} tasks "
            f"because it supports {', '.join(model.get('suitable_for', [])[:2])}."
        )
        if reference_note:
            base_reason = f"{base_reason} 知识库依据摘要：参考 {reference_note} 的方法提示。"
        return {
            "model_id": model.get("id"),
            "name": model.get("name"),
            "category": model.get("category"),
            "method": method,
            "why_suitable": base_reason,
            "input_data_requirements": input_requirements,
            "expected_output": model.get("output_type"),
            "implementation_difficulty": difficulty,
            "paper_expression_advantage": self._paper_expression_advantage(model, advantages),
            "risks_and_limitations": limitations,
            "python_libraries": model.get("python_libraries", []),
            "paper_expression_template": model.get("paper_expression_template", ""),
            "recommendation_score": model.get("recommendation_score", 0),
            "data_type": data_type,
            "task_id": task.get("id"),
            "task_type": task.get("task_type"),
            "retrieved_references": retrieved_references[:3],
        }

    def _infer_data_type(self, task: dict[str, Any], data_profile: dict[str, Any] | None = None) -> str:
        data_profile = data_profile or {}
        summary = data_profile.get("summary", {})
        if summary.get("time_columns"):
            return "time_series_or_tabular"
        if summary.get("numeric_columns") or summary.get("categorical_columns"):
            return "tabular"
        text = f"{task.get('task_type', '')} {task.get('description', '')}".lower()
        if any(keyword in text for keyword in ["graph", "network", "path", "flow"]):
            return "network"
        if any(keyword in text for keyword in ["time", "forecast", "prediction", "trend"]):
            return "time_series_or_tabular"
        if any(keyword in text for keyword in ["image", "spatial", "grid"]):
            return "spatial_or_grid"
        return "tabular"

    def _implementation_difficulty(self, model: dict[str, Any]) -> str:
        libraries = set(model.get("python_libraries", []))
        model_id = str(model.get("id", ""))
        if libraries <= {"numpy", "pandas"} or model_id in {"linear_regression", "entropy_weight", "topsis", "grey_prediction_GM11"}:
            return "low"
        if model_id in {"random_forest", "random_forest_classifier", "kmeans", "pca", "shortest_path", "max_flow"}:
            return "medium"
        return "high"

    def _paper_expression_advantage(self, model: dict[str, Any], advantages: list[str]) -> str:
        advantage_text = "; ".join(advantages[:2])
        template = model.get("paper_expression_template", "")
        if advantage_text:
            return f"{advantage_text}. Paper expression: {template}"
        return f"Paper expression: {template}"
