from __future__ import annotations

from typing import Any

from src.agents.base import BaseAgent
from src.utils.json_utils import write_json


class ModelSelectorAgent(BaseAgent):
    name = "ModelSelectorAgent"

    def run(self, candidate_strategies: dict[str, Any]) -> dict[str, Any]:
        selected = []
        for item in candidate_strategies.get("strategies", []):
            scored = []
            for candidate in item.get("candidates", []):
                scores = self._score(candidate, item.get("task_type", ""))
                scored.append({**candidate, "scores": scores, "total_score": scores["total_score"]})
            scored.sort(key=lambda x: x["total_score"], reverse=True)
            selected.append(
                {
                    "task_id": item.get("task_id"),
                    "task_type": item.get("task_type"),
                    "selected": scored[0] if scored else None,
                    "ranked_candidates": scored,
                }
            )
        result = {
            "agent": self.name,
            "llm_trace": self.llm_client.complete_json(
                "model_selector",
                {"strategy_groups": len(candidate_strategies.get("strategies", []))},
            ),
            "criteria": [
                "data_fit_score",
                "implementation_score",
                "interpretability_score",
                "stability_score",
                "reportability_score",
                "formula_quality_score",
                "sensitivity_analysis_potential",
                "total_score",
            ],
            "selected_strategies": selected,
            "overall_route": self._overall_route(selected),
            "model_selection_trace": self._selection_trace(selected),
        }
        if self.logs_dir is not None:
            write_json(self.logs_dir / "model_selection_trace.json", result["model_selection_trace"])
        return result

    def _score(self, candidate: dict[str, Any], task_type: str) -> dict[str, int]:
        data_fit = self._data_fit_score(candidate, task_type)
        implementation = self._implementation_score(candidate)
        interpretability = self._interpretability_score(candidate)
        stability = self._stability_score(candidate)
        reportability = self._reportability_score(candidate)
        formula_quality = self._formula_quality_score(candidate)
        sensitivity_potential = self._sensitivity_analysis_potential(candidate)
        total = data_fit + implementation + interpretability + stability + reportability + formula_quality + sensitivity_potential
        return {
            "data_fit_score": data_fit,
            "implementation_score": implementation,
            "interpretability_score": interpretability,
            "stability_score": stability,
            "reportability_score": reportability,
            "formula_quality_score": formula_quality,
            "sensitivity_analysis_potential": sensitivity_potential,
            "total_score": total,
        }

    def _data_fit_score(self, candidate: dict[str, Any], task_type: str) -> int:
        category = candidate.get("category", "")
        task_type = task_type or candidate.get("task_type", "")
        if category == task_type:
            return 5
        if task_type in {"data_preprocessing", "result_interpretation", "descriptive_modeling"} and category == "evaluation":
            return 4
        if task_type == "prediction" and category in {"prediction", "evaluation"}:
            return 4
        if candidate.get("recommendation_score", 0) >= 50:
            return 4
        return 3

    def _implementation_score(self, candidate: dict[str, Any]) -> int:
        difficulty = candidate.get("implementation_difficulty", "medium")
        if difficulty == "low":
            return 5
        if difficulty == "medium":
            return 4
        return 3

    def _interpretability_score(self, candidate: dict[str, Any]) -> int:
        text = self._candidate_text(candidate)
        if any(term in text for term in ["linear", "entropy", "topsis", "ahp", "grey", "coefficient", "ideal"]):
            return 5
        if any(term in text for term in ["feature importance", "cluster center", "principal component"]):
            return 4
        return 3

    def _stability_score(self, candidate: dict[str, Any]) -> int:
        text = self._candidate_text(candidate)
        if any(term in text for term in ["sensitive", "stochastic", "overfit", "local optima", "subjective"]):
            return 3
        if any(term in text for term in ["robust", "mature", "standard"]):
            return 5
        return 4

    def _reportability_score(self, candidate: dict[str, Any]) -> int:
        text = self._candidate_text(candidate)
        if any(term in text for term in ["paper expression", "rank", "coefficient", "objective", "ideal", "hierarchy"]):
            return 5
        if candidate.get("paper_expression_template"):
            return 4
        return 3

    def _formula_quality_score(self, candidate: dict[str, Any]) -> int:
        text = self._candidate_text(candidate)
        if any(term in text for term in ["objective", "constraint", "loss", "equation", "coefficient", "weight", "distance", "rank"]):
            return 5
        if candidate.get("paper_expression_template"):
            return 4
        return 3

    def _sensitivity_analysis_potential(self, candidate: dict[str, Any]) -> int:
        text = self._candidate_text(candidate)
        if any(term in text for term in ["parameter", "weight", "threshold", "constraint", "scenario", "forecast", "simulation"]):
            return 5
        if any(term in text for term in ["random", "forest", "boosting", "cluster", "optimization"]):
            return 4
        return 3

    def _candidate_text(self, candidate: dict[str, Any]) -> str:
        values = [
            candidate.get("model_id", ""),
            candidate.get("name", ""),
            candidate.get("category", ""),
            candidate.get("method", ""),
            candidate.get("why_suitable", ""),
            " ".join(candidate.get("input_data_requirements", [])),
            str(candidate.get("expected_output", "")),
            str(candidate.get("paper_expression_advantage", "")),
            " ".join(candidate.get("risks_and_limitations", [])),
            str(candidate.get("paper_expression_template", "")),
        ]
        return " ".join(str(value) for value in values).lower()

    def _overall_route(self, selected: list[dict[str, Any]]) -> str:
        model_names = []
        for item in selected:
            selected_model = item.get("selected")
            if selected_model:
                model_names.append(selected_model.get("name", ""))
        unique_names = []
        for name in model_names:
            if name and name not in unique_names:
                unique_names.append(name)
        if not unique_names:
            return "No model route selected."
        preview = ", ".join(unique_names[:5])
        return f"Model Zoo guided route prioritizing: {preview}."

    def _selection_trace(self, selected: list[dict[str, Any]]) -> dict[str, Any]:
        traces = []
        for item in selected:
            chosen = item.get("selected") or {}
            rejected = []
            for candidate in item.get("ranked_candidates", [])[1:]:
                rejected.append(
                    {
                        "model_id": candidate.get("model_id"),
                        "name": candidate.get("name"),
                        "total_score": candidate.get("total_score"),
                        "why_not_selected": self._why_not_selected(chosen, candidate),
                        "risk_points": candidate.get("risks_and_limitations", []),
                    }
                )
            traces.append(
                {
                    "task_id": item.get("task_id"),
                    "task_type": item.get("task_type"),
                    "selected_model": {
                        "model_id": chosen.get("model_id"),
                        "name": chosen.get("name"),
                        "total_score": chosen.get("total_score"),
                        "scores": chosen.get("scores", {}),
                    },
                    "selection_reason": self._selection_reason(chosen),
                    "data_match": chosen.get("why_suitable", ""),
                    "output_match": chosen.get("expected_output", ""),
                    "current_model_risks": chosen.get("risks_and_limitations", []),
                    "rejected_candidates": rejected,
                }
            )
        return {
            "criteria": [
                "data_fit_score",
                "implementation_score",
                "interpretability_score",
                "stability_score",
                "reportability_score",
                "formula_quality_score",
                "sensitivity_analysis_potential",
                "total_score",
            ],
            "task_traces": traces,
        }

    def _selection_reason(self, candidate: dict[str, Any]) -> str:
        if not candidate:
            return "No candidate model was available."
        scores = candidate.get("scores", {})
        strongest = sorted(
            ((key, value) for key, value in scores.items() if key != "total_score"),
            key=lambda item: item[1],
            reverse=True,
        )[:3]
        score_text = ", ".join(f"{key}={value}" for key, value in strongest)
        return (
            f"Selected {candidate.get('name', candidate.get('model_id'))} because it has the highest total score "
            f"under the current data, implementation, interpretability, stability, reportability, formula, and sensitivity criteria. "
            f"Strongest dimensions: {score_text}."
        )

    def _why_not_selected(self, selected: dict[str, Any], candidate: dict[str, Any]) -> str:
        selected_score = selected.get("total_score", 0) if selected else 0
        candidate_score = candidate.get("total_score", 0)
        if candidate_score < selected_score:
            return f"Lower total score than the selected model ({candidate_score} < {selected_score})."
        return "Kept as backup because the selected model is more balanced for report expression and implementation."
