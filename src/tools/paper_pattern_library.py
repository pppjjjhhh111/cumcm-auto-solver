from __future__ import annotations

from pathlib import Path
from typing import Any


class PaperPatternLibrary:
    """Load and recommend mathematical modeling paper writing patterns."""

    def __init__(self, config_path: Path | None = None) -> None:
        self.config_path = config_path or Path(__file__).resolve().parents[2] / "config" / "paper_patterns.yaml"
        self._patterns: dict[str, dict[str, Any]] = {}

    def load_patterns(self) -> dict[str, dict[str, Any]]:
        if not self.config_path.exists():
            raise FileNotFoundError(f"Paper pattern config does not exist: {self.config_path}")
        try:
            import yaml
        except ImportError as exc:
            raise ImportError("PyYAML is required to load paper_patterns.yaml.") from exc

        payload = yaml.safe_load(self.config_path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("Paper pattern config must be a mapping.")

        patterns: dict[str, dict[str, Any]] = {}
        for pattern_id, pattern in payload.items():
            if not isinstance(pattern, dict):
                raise ValueError(f"Paper pattern must be a mapping: {pattern_id}")
            normalized = dict(pattern)
            normalized["id"] = pattern_id
            self._validate_pattern(pattern_id, normalized)
            patterns[pattern_id] = normalized
        self._patterns = patterns
        return dict(self._patterns)

    def get_pattern(self, problem_type: str) -> dict[str, Any]:
        self._ensure_loaded()
        pattern_id = self._normalize_problem_type(problem_type)
        return dict(self._patterns.get(pattern_id, self._patterns["evaluation_problem"]))

    def recommend_pattern(self, parsed_problem: dict[str, Any]) -> dict[str, Any]:
        self._ensure_loaded()
        problem_type = parsed_problem.get("problem_type", "evaluation")
        primary_pattern = self.get_pattern(problem_type)

        question_patterns = []
        seen_pattern_ids = [primary_pattern["id"]]
        for question in parsed_problem.get("questions", []):
            objective = question.get("objective") or problem_type
            pattern = self.get_pattern(objective)
            if pattern["id"] not in seen_pattern_ids:
                seen_pattern_ids.append(pattern["id"])
            question_patterns.append(
                {
                    "question_id": question.get("id"),
                    "question_text": question.get("text"),
                    "objective": objective,
                    "pattern_id": pattern["id"],
                    "pattern_name": pattern.get("name", pattern["id"]),
                    "section_order": pattern.get("section_order", []),
                }
            )

        combined_patterns = [self._patterns[pattern_id] for pattern_id in seen_pattern_ids]
        return {
            "primary_problem_type": problem_type,
            "primary_pattern": primary_pattern,
            "patterns": combined_patterns,
            "question_patterns": question_patterns,
        }

    def _ensure_loaded(self) -> None:
        if not self._patterns:
            self.load_patterns()

    def _validate_pattern(self, pattern_id: str, pattern: dict[str, Any]) -> None:
        required_fields = [
            "section_order",
            "key_formulas",
            "recommended_figures",
            "recommended_tables",
            "common_assumptions",
            "common_validation_methods",
            "writing_style_tips",
        ]
        missing = [field for field in required_fields if field not in pattern]
        if missing:
            raise ValueError(f"Paper pattern {pattern_id} missing fields: {missing}")
        for field in required_fields:
            if not isinstance(pattern[field], list):
                raise ValueError(f"Paper pattern {pattern_id}.{field} must be a list.")

    def _normalize_problem_type(self, problem_type: str) -> str:
        self._ensure_loaded()
        normalized = (problem_type or "").strip().lower()
        if not normalized:
            return "evaluation_problem"
        if normalized.endswith("_problem") and normalized in self._patterns:
            return normalized

        for pattern_id, pattern in self._patterns.items():
            aliases = [pattern_id.replace("_problem", ""), *pattern.get("problem_aliases", [])]
            if normalized in {str(alias).lower() for alias in aliases}:
                return pattern_id

        keyword_map = {
            "prediction_problem": ["predict", "forecast", "trend", "time"],
            "optimization_problem": ["optim", "allocation", "schedule", "min", "max"],
            "classification_problem": ["class", "cluster", "segment"],
            "simulation_problem": ["simulat", "monte", "dynamic"],
            "network_problem": ["network", "graph", "path", "flow"],
            "evaluation_problem": ["evaluat", "rank", "score", "indicator", "data"],
        }
        for pattern_id, keywords in keyword_map.items():
            if any(keyword in normalized for keyword in keywords):
                return pattern_id
        return "evaluation_problem"
