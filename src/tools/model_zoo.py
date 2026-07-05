from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class ModelZoo:
    """Load, search, and recommend mathematical modeling methods."""

    def __init__(self, config_path: Path | None = None) -> None:
        self.config_path = config_path or Path(__file__).resolve().parents[2] / "config" / "model_zoo.yaml"
        self._models_by_category: dict[str, list[dict[str, Any]]] = {}
        self._models: list[dict[str, Any]] = []

    def load_models(self) -> list[dict[str, Any]]:
        if not self.config_path.exists():
            raise FileNotFoundError(f"Model zoo config does not exist: {self.config_path}")

        raw_text = self.config_path.read_text(encoding="utf-8")
        try:
            import yaml

            payload = yaml.safe_load(raw_text)
        except ImportError:
            payload = json.loads(raw_text)

        if not isinstance(payload, dict):
            raise ValueError("Model zoo config must be a category-to-model-list mapping.")

        models_by_category: dict[str, list[dict[str, Any]]] = {}
        models: list[dict[str, Any]] = []
        for category, entries in payload.items():
            if not isinstance(entries, list):
                raise ValueError(f"Model zoo category must contain a list: {category}")
            normalized_entries = []
            for entry in entries:
                if not isinstance(entry, dict):
                    raise ValueError(f"Model entry must be a mapping in category: {category}")
                normalized = dict(entry)
                normalized.setdefault("id", self._slugify(str(normalized.get("name", ""))))
                normalized.setdefault("category", category)
                self._validate_model(normalized, category)
                normalized_entries.append(normalized)
                models.append(normalized)
            models_by_category[category] = normalized_entries

        self._models_by_category = models_by_category
        self._models = models
        return list(self._models)

    def list_categories(self) -> list[str]:
        self._ensure_loaded()
        return sorted(self._models_by_category.keys())

    def get_models_by_category(self, category: str) -> list[dict[str, Any]]:
        self._ensure_loaded()
        return [dict(model) for model in self._models_by_category.get(category, [])]

    def search_models(self, query: str) -> list[dict[str, Any]]:
        self._ensure_loaded()
        normalized_query = query.strip().lower()
        if not normalized_query:
            return [dict(model) for model in self._models]
        terms = [term for term in normalized_query.replace("_", " ").split() if term]
        scored = []
        for model in self._models:
            searchable = self._searchable_text(model)
            score = sum(1 for term in terms if term in searchable)
            if normalized_query in searchable:
                score += 3
            if score > 0:
                scored.append((score, model))
        scored.sort(key=lambda item: (-item[0], item[1]["category"], item[1]["id"]))
        return [dict(model) for _, model in scored]

    def recommend_models(
        self,
        problem_type: str,
        data_type: str = "tabular",
        task_description: str = "",
        limit: int = 3,
    ) -> list[dict[str, Any]]:
        self._ensure_loaded()
        problem_type = (problem_type or "general_modeling").lower()
        data_type = (data_type or "tabular").lower()
        task_description = task_description or ""
        target_categories = self._target_categories(problem_type, task_description)

        scored = []
        for model in self._models:
            score = self._recommendation_score(model, target_categories, data_type, task_description)
            scored.append((score, model))
        scored.sort(key=lambda item: (-item[0], item[1]["category"], item[1]["id"]))
        recommendations = []
        for score, model in scored[: max(limit, 3)]:
            enriched = dict(model)
            enriched["recommendation_score"] = score
            enriched["fit_reason"] = self._fit_reason(enriched, problem_type, data_type, task_description)
            recommendations.append(enriched)
        return recommendations

    def _ensure_loaded(self) -> None:
        if not self._models:
            self.load_models()

    def _validate_model(self, model: dict[str, Any], expected_category: str) -> None:
        required_fields = [
            "name",
            "category",
            "suitable_for",
            "input_requirements",
            "output_type",
            "advantages",
            "limitations",
            "typical_workflow",
            "python_libraries",
            "paper_expression_template",
        ]
        missing = [field for field in required_fields if field not in model]
        if missing:
            raise ValueError(f"Model {model.get('id', '<unknown>')} missing fields: {missing}")
        if model["category"] != expected_category:
            raise ValueError(
                f"Model {model.get('id', '<unknown>')} category {model['category']} "
                f"does not match section {expected_category}"
            )

    def _target_categories(self, problem_type: str, task_description: str) -> list[str]:
        text = f"{problem_type} {task_description}".lower()
        category_keywords = {
            "prediction": ["prediction", "forecast", "trend", "regression", "time series"],
            "optimization": ["optimization", "allocation", "schedule", "route", "minimize", "maximize"],
            "evaluation": ["evaluation", "ranking", "score", "indicator", "assessment", "preprocessing", "interpretation"],
            "classification": ["classification", "cluster", "segment", "group", "recognition"],
            "network": ["network", "graph", "path", "flow", "node", "edge"],
            "simulation": ["simulation", "monte carlo", "dynamic", "uncertainty", "scenario"],
        }
        matches = [
            category
            for category, keywords in category_keywords.items()
            if problem_type == category or any(keyword in text for keyword in keywords)
        ]
        if matches:
            return matches
        return ["evaluation", "prediction", "simulation"]

    def _recommendation_score(
        self,
        model: dict[str, Any],
        target_categories: list[str],
        data_type: str,
        task_description: str,
    ) -> int:
        score = 0
        if model["category"] in target_categories:
            score += 50
        searchable = self._searchable_text(model)
        if data_type and data_type in searchable:
            score += 8
        terms = [term for term in task_description.lower().replace("_", " ").split() if len(term) >= 3]
        score += min(sum(2 for term in terms if term in searchable), 20)
        if any(word in searchable for word in ["easy", "simple", "interpretable", "reportable"]):
            score += 3
        return score

    def _fit_reason(self, model: dict[str, Any], problem_type: str, data_type: str, task_description: str) -> str:
        suitable_for = "; ".join(model.get("suitable_for", [])[:2])
        return (
            f"{model['name']} matches {problem_type} tasks with {data_type} data. "
            f"Typical fit: {suitable_for}. Task context: {task_description[:160]}"
        )

    def _searchable_text(self, model: dict[str, Any]) -> str:
        values = [
            str(model.get("id", "")),
            str(model.get("name", "")),
            str(model.get("category", "")),
            self._join(model.get("suitable_for", [])),
            self._join(model.get("input_requirements", [])),
            str(model.get("output_type", "")),
            self._join(model.get("advantages", [])),
            self._join(model.get("limitations", [])),
            self._join(model.get("typical_workflow", [])),
            self._join(model.get("python_libraries", [])),
            str(model.get("paper_expression_template", "")),
        ]
        return " ".join(values).lower()

    def _join(self, value: Any) -> str:
        if isinstance(value, list):
            return " ".join(str(item) for item in value)
        return str(value)

    def _slugify(self, value: str) -> str:
        return "_".join(part for part in value.lower().replace("-", " ").split() if part)
