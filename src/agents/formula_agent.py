from __future__ import annotations

from typing import Any

from src.agents.base import BaseAgent
from src.utils.json_utils import write_json


class FormulaAgent(BaseAgent):
    """Generate formula blocks and check basic formula documentation."""

    name = "FormulaAgent"

    def run(
        self,
        selected_strategy: dict[str, Any],
        sub_tasks: dict[str, Any],
        model_zoo_entries: list[dict[str, Any]] | None = None,
        parsed_problem: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        parsed_problem = parsed_problem or {}
        latex_blocks = []
        model_names = self._model_names(selected_strategy)
        problem_type = parsed_problem.get("problem_type", "general_modeling")
        for idx, model_name in enumerate(model_names or ["baseline model"], start=1):
            latex_blocks.append(self._formula_for_model(idx, model_name, problem_type))

        variables = [
            {"symbol": "x_i", "meaning": "index or feature vector of sample i"},
            {"symbol": "y_i", "meaning": "observed target or response of sample i"},
            {"symbol": "\\hat y_i", "meaning": "model prediction or fitted value"},
            {"symbol": "w_j", "meaning": "weight of indicator or feature j"},
            {"symbol": "S_i", "meaning": "comprehensive score of object i"},
        ]
        parameters = [
            {"symbol": "\\theta", "meaning": "model parameter vector"},
            {"symbol": "\\lambda", "meaning": "regularization or sensitivity parameter"},
        ]
        result = {
            "agent": self.name,
            "llm_trace": self.llm_client.complete_json(
                "formula_agent",
                {
                    "model_count": len(model_names),
                    "task_count": len(sub_tasks.get("tasks", [])),
                    "problem_type": problem_type,
                },
            ),
            "variables": variables,
            "parameters": parameters,
            "objective_functions": [
                {
                    "latex": r"\min_{\theta} \sum_{i=1}^{n} L(y_i, f(x_i;\theta))",
                    "explanation": "Fit model parameters by minimizing empirical loss.",
                }
            ],
            "constraints": [
                {
                    "latex": r"g_k(x,\theta) \le 0,\quad k=1,\ldots,m",
                    "explanation": "Represent problem-specific resource, feasibility, or logical constraints.",
                }
            ],
            "model_equations": latex_blocks,
            "loss_functions": [
                {"latex": r"\mathrm{MSE}=\frac{1}{n}\sum_{i=1}^{n}(y_i-\hat y_i)^2", "explanation": "Mean squared error for prediction tasks."}
            ],
            "evaluation_metrics": [
                {"latex": r"R^2=1-\frac{\sum_i (y_i-\hat y_i)^2}{\sum_i(y_i-\bar y)^2}", "explanation": "Goodness-of-fit measure for regression style models."},
                {"latex": r"\Delta S=\frac{S(\theta+\delta)-S(\theta)}{S(\theta)}", "explanation": "Relative change used for sensitivity analysis."},
            ],
            "latex_blocks": latex_blocks,
            "explanation": "Formulas are deterministic templates selected from the chosen model route.",
        }
        result["checks"] = self._checks(result, sub_tasks)
        if self.logs_dir is not None:
            write_json(self.logs_dir / "formulas.json", result)
        return result

    def _model_names(self, selected_strategy: dict[str, Any]) -> list[str]:
        names = []
        for item in selected_strategy.get("selected_strategies", []):
            selected = item.get("selected") or {}
            name = selected.get("model_id") or selected.get("name")
            if name and name not in names:
                names.append(str(name))
        solution = selected_strategy.get("selected_solution", {})
        for item in solution.get("models_for_each_task", []):
            selected = item.get("selected_model") or {}
            name = selected.get("model_id") or selected.get("name")
            if name and name not in names:
                names.append(str(name))
        return names

    def _formula_for_model(self, idx: int, model_name: str, problem_type: str) -> dict[str, str]:
        text = model_name.lower()
        if "linear" in text or "regression" in text:
            latex = r"\hat y_i=\beta_0+\sum_{j=1}^{p}\beta_j x_{ij}"
            explanation = "Linear or regression model maps features to a fitted response."
        elif "topsis" in text:
            latex = r"C_i=\frac{D_i^-}{D_i^+ + D_i^-}"
            explanation = "TOPSIS evaluates alternatives by distance from ideal and negative-ideal solutions."
        elif "entropy" in text:
            latex = r"w_j=\frac{1-e_j}{\sum_{k=1}^{p}(1-e_k)}"
            explanation = "Entropy weight assigns larger weight to indicators with more information variation."
        elif "kmeans" in text or "cluster" in text:
            latex = r"\min_{\mu_1,\ldots,\mu_K}\sum_{i=1}^{n}\min_k \lVert x_i-\mu_k\rVert_2^2"
            explanation = "Clustering minimizes within-cluster squared distances."
        elif "optimization" in problem_type or "programming" in text:
            latex = r"\max_x Z=c^\top x,\quad A x \le b,\quad x\ge 0"
            explanation = "Optimization model maximizes an objective under linearized constraints."
        else:
            latex = r"S_i=\sum_{j=1}^{p} w_j z_{ij}"
            explanation = "Weighted scoring formula summarizes standardized indicators."
        return {"id": f"eq_{idx}", "model": model_name, "latex": latex, "explanation": explanation}

    def _checks(self, result: dict[str, Any], sub_tasks: dict[str, Any]) -> dict[str, Any]:
        variables_defined = all(item.get("symbol") and item.get("meaning") for item in result.get("variables", []))
        formulas_explained = all(item.get("latex") and item.get("explanation") for item in result.get("latex_blocks", []))
        task_count = len(sub_tasks.get("tasks", []))
        return {
            "variables_defined": variables_defined,
            "formulas_explained": formulas_explained,
            "task_count": task_count,
            "formula_count": len(result.get("latex_blocks", [])),
            "each_question_has_expression_if_applicable": len(result.get("latex_blocks", [])) > 0 or task_count == 0,
        }
