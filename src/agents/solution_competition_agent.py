from __future__ import annotations

from typing import Any

from src.agents.base import BaseAgent
from src.utils.json_utils import write_json


class SolutionCompetitionAgent(BaseAgent):
    """Generate and score complete competing modeling solutions."""

    name = "SolutionCompetitionAgent"

    SOLUTION_NAMES = ["conservative_solution", "advanced_solution", "hybrid_solution"]

    def run(
        self,
        sub_tasks: dict[str, Any],
        candidate_strategies: dict[str, Any],
        data_profile: dict[str, Any],
    ) -> dict[str, Any]:
        strategy_groups = candidate_strategies.get("strategies", [])
        solutions = [
            self._build_solution("conservative_solution", strategy_groups, data_profile),
            self._build_solution("advanced_solution", strategy_groups, data_profile),
            self._build_solution("hybrid_solution", strategy_groups, data_profile),
        ]
        solutions.sort(key=lambda solution: solution["score"]["total_score"], reverse=True)
        result = {
            "agent": self.name,
            "llm_trace": self.llm_client.complete_json(
                "solution_competition",
                {
                    "task_count": len(sub_tasks.get("tasks", [])),
                    "strategy_group_count": len(strategy_groups),
                    "data_profile": data_profile,
                },
            ),
            "input_summary": {
                "task_count": len(sub_tasks.get("tasks", [])),
                "strategy_group_count": len(strategy_groups),
                "data_profile": data_profile,
            },
            "score_dimensions": [
                "question_alignment",
                "data_feasibility",
                "implementation_feasibility",
                "interpretability",
                "result_visualization_potential",
                "robustness",
                "paper_writing_quality",
                "total_score",
            ],
            "candidate_solutions": solutions,
            "selected_solution": solutions[0] if solutions else {},
        }
        if self.logs_dir is not None:
            write_json(self.logs_dir / "solution_competition.json", result)
        return result

    def _build_solution(
        self,
        solution_name: str,
        strategy_groups: list[dict[str, Any]],
        data_profile: dict[str, Any],
    ) -> dict[str, Any]:
        models_for_each_task = []
        for group in strategy_groups:
            model = self._choose_model(solution_name, group.get("candidates", []))
            models_for_each_task.append(
                {
                    "task_id": group.get("task_id"),
                    "task_type": group.get("task_type"),
                    "task_description": group.get("task_description", ""),
                    "selected_model": model,
                    "selection_reason": self._selection_reason(solution_name, model),
                }
            )

        score = self._score_solution(solution_name, models_for_each_task, data_profile)
        return {
            "solution_name": solution_name,
            "overall_idea": self._overall_idea(solution_name),
            "models_for_each_task": models_for_each_task,
            "required_data": self._required_data(models_for_each_task, data_profile),
            "expected_outputs": self._expected_outputs(models_for_each_task),
            "expected_figures": self._expected_figures(solution_name, models_for_each_task),
            "implementation_difficulty": self._solution_difficulty(solution_name, models_for_each_task),
            "risk_points": self._risk_points(solution_name, models_for_each_task, data_profile),
            "paper_narrative": self._paper_narrative(solution_name),
            "score": score,
        }

    def _choose_model(self, solution_name: str, candidates: list[dict[str, Any]]) -> dict[str, Any]:
        if not candidates:
            return {}
        if solution_name == "conservative_solution":
            return sorted(candidates, key=self._conservative_sort_key)[0]
        if solution_name == "advanced_solution":
            return sorted(candidates, key=self._advanced_sort_key)[0]
        return sorted(candidates, key=self._hybrid_sort_key)[0]

    def _conservative_sort_key(self, candidate: dict[str, Any]) -> tuple[int, int, str]:
        difficulty_rank = {"low": 0, "medium": 1, "high": 2}
        text = self._candidate_text(candidate)
        interpretability_bonus = -1 if any(term in text for term in ["linear", "entropy", "topsis", "grey"]) else 0
        return (
            difficulty_rank.get(candidate.get("implementation_difficulty", "medium"), 1),
            interpretability_bonus,
            str(candidate.get("model_id", "")),
        )

    def _advanced_sort_key(self, candidate: dict[str, Any]) -> tuple[int, int, str]:
        difficulty_rank = {"high": 0, "medium": 1, "low": 2}
        text = self._candidate_text(candidate)
        advanced_bonus = -1 if any(term in text for term in ["forest", "boosting", "genetic", "annealing", "svm"]) else 0
        return (
            advanced_bonus,
            difficulty_rank.get(candidate.get("implementation_difficulty", "medium"), 1),
            str(candidate.get("model_id", "")),
        )

    def _hybrid_sort_key(self, candidate: dict[str, Any]) -> tuple[int, int, str]:
        difficulty = candidate.get("implementation_difficulty", "medium")
        difficulty_rank = 0 if difficulty == "medium" else 1 if difficulty == "low" else 2
        return (
            difficulty_rank,
            -int(candidate.get("recommendation_score", 0)),
            str(candidate.get("model_id", "")),
        )

    def _score_solution(
        self,
        solution_name: str,
        models_for_each_task: list[dict[str, Any]],
        data_profile: dict[str, Any],
    ) -> dict[str, int]:
        difficulty = self._solution_difficulty(solution_name, models_for_each_task)
        has_data = data_profile.get("file_count", 0) > 0 or data_profile.get("table_count", 0) > 0
        model_text = self._models_text(models_for_each_task)

        question_alignment = 5 if models_for_each_task else 2
        data_feasibility = 5 if has_data and difficulty != "high" else 4 if has_data else 3
        implementation_feasibility = {"low": 5, "medium": 4, "high": 3}.get(difficulty, 4)
        interpretability = 5 if solution_name == "conservative_solution" else 4 if solution_name == "hybrid_solution" else 3
        visualization = 5 if any(term in model_text for term in ["prediction", "ranking", "cluster", "flow", "simulation"]) else 4
        robustness = 5 if solution_name == "conservative_solution" else 4 if solution_name == "hybrid_solution" else 3
        paper_quality = 5 if solution_name in {"conservative_solution", "hybrid_solution"} else 4

        if solution_name == "hybrid_solution":
            question_alignment += 1
            visualization += 1
        scores = {
            "question_alignment": self._clamp(question_alignment),
            "data_feasibility": self._clamp(data_feasibility),
            "implementation_feasibility": self._clamp(implementation_feasibility),
            "interpretability": self._clamp(interpretability),
            "result_visualization_potential": self._clamp(visualization),
            "robustness": self._clamp(robustness),
            "paper_writing_quality": self._clamp(paper_quality),
        }
        scores["total_score"] = sum(scores.values())
        return scores

    def _overall_idea(self, solution_name: str) -> str:
        ideas = {
            "conservative_solution": (
                "Use simple, interpretable, low-dependency models for each task, prioritizing stable execution "
                "and clear paper explanation."
            ),
            "advanced_solution": (
                "Use higher-capacity machine learning, optimization, or nonlinear models when candidate models "
                "support stronger fitting or search ability."
            ),
            "hybrid_solution": (
                "Combine interpretable baseline models with stronger candidate models where useful, balancing "
                "reliability, effect quality, and paper expressiveness."
            ),
        }
        return ideas[solution_name]

    def _required_data(self, models_for_each_task: list[dict[str, Any]], data_profile: dict[str, Any]) -> list[str]:
        requirements = [
            f"Input data files: {data_profile.get('file_count', 0)}",
            f"Detected tables: {data_profile.get('table_count', 0)}",
        ]
        for item in models_for_each_task:
            model = item.get("selected_model") or {}
            for requirement in model.get("input_data_requirements", []):
                if requirement not in requirements:
                    requirements.append(requirement)
        return requirements

    def _expected_outputs(self, models_for_each_task: list[dict[str, Any]]) -> list[str]:
        outputs = []
        for item in models_for_each_task:
            output = (item.get("selected_model") or {}).get("expected_output")
            if output and output not in outputs:
                outputs.append(output)
        return outputs or ["model results", "tables", "figures", "paper narrative"]

    def _expected_figures(self, solution_name: str, models_for_each_task: list[dict[str, Any]]) -> list[str]:
        figures = ["data profile chart", "main result chart"]
        model_text = self._models_text(models_for_each_task)
        if "prediction" in model_text or "regression" in model_text:
            figures.append("actual vs predicted comparison chart")
        if "ranking" in model_text or "topsis" in model_text or "entropy" in model_text:
            figures.append("score ranking bar chart")
        if solution_name in {"advanced_solution", "hybrid_solution"}:
            figures.append("model comparison chart")
        return figures

    def _solution_difficulty(self, solution_name: str, models_for_each_task: list[dict[str, Any]]) -> str:
        if solution_name == "advanced_solution":
            return "high"
        difficulties = [
            (item.get("selected_model") or {}).get("implementation_difficulty", "medium")
            for item in models_for_each_task
        ]
        if "high" in difficulties:
            return "high" if solution_name != "hybrid_solution" else "medium"
        if "medium" in difficulties:
            return "medium"
        return "low"

    def _risk_points(
        self,
        solution_name: str,
        models_for_each_task: list[dict[str, Any]],
        data_profile: dict[str, Any],
    ) -> list[str]:
        risks = []
        if data_profile.get("table_count", 0) == 0:
            risks.append("No structured table was detected; model implementation may rely on text-only assumptions.")
        if solution_name == "advanced_solution":
            risks.append("Advanced models may require more data, tuning, and third-party libraries.")
        if solution_name == "conservative_solution":
            risks.append("Conservative models may underfit nonlinear relationships.")
        if solution_name == "hybrid_solution":
            risks.append("Hybrid solution needs careful paper explanation to connect baseline and enhanced models.")
        for item in models_for_each_task:
            model = item.get("selected_model") or {}
            for risk in model.get("risks_and_limitations", [])[:1]:
                if risk not in risks:
                    risks.append(risk)
        return risks

    def _paper_narrative(self, solution_name: str) -> str:
        narratives = {
            "conservative_solution": (
                "The paper can emphasize transparent assumptions, reproducible steps, and clear interpretation."
            ),
            "advanced_solution": (
                "The paper can emphasize stronger modeling capacity and compare gains against simpler baselines."
            ),
            "hybrid_solution": (
                "The paper can present an interpretable baseline first, then introduce enhanced models for tasks "
                "where better fit or optimization quality is needed."
            ),
        }
        return narratives[solution_name]

    def _selection_reason(self, solution_name: str, model: dict[str, Any]) -> str:
        if not model:
            return "No candidate model was available for this task."
        if solution_name == "conservative_solution":
            return "Chosen for low implementation difficulty and paper interpretability."
        if solution_name == "advanced_solution":
            return "Chosen for stronger modeling capacity among available candidates."
        return "Chosen as a balance between feasibility, recommendation score, and expressiveness."

    def _models_text(self, models_for_each_task: list[dict[str, Any]]) -> str:
        return " ".join(
            self._candidate_text(item.get("selected_model") or {})
            for item in models_for_each_task
        )

    def _candidate_text(self, candidate: dict[str, Any]) -> str:
        values = [
            candidate.get("model_id", ""),
            candidate.get("name", ""),
            candidate.get("category", ""),
            candidate.get("expected_output", ""),
            candidate.get("paper_expression_advantage", ""),
            " ".join(candidate.get("risks_and_limitations", [])),
        ]
        return " ".join(str(value) for value in values).lower()

    def _clamp(self, score: int) -> int:
        return max(1, min(score, 5))
