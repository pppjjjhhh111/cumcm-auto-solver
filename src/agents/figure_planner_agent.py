from __future__ import annotations

from typing import Any

from src.agents.base import BaseAgent
from src.utils.json_utils import write_json


class FigurePlannerAgent(BaseAgent):
    """Plan figures for data exploration, modeling, results, and validation."""

    name = "FigurePlannerAgent"

    def run(
        self,
        parsed_problem: dict[str, Any],
        data_profile: dict[str, Any],
        selected_strategy: dict[str, Any],
        execution_results: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        execution_results = execution_results or {}
        figures = []
        numeric_columns = data_profile.get("summary", {}).get("numeric_columns", [])
        categorical_columns = data_profile.get("summary", {}).get("categorical_columns", [])
        time_columns = data_profile.get("summary", {}).get("time_columns", [])
        problem_type = parsed_problem.get("problem_type", "general_modeling")

        if numeric_columns:
            figures.append(
                self._figure(
                    "F1",
                    "histogram",
                    numeric_columns[:1],
                    numeric_columns[0],
                    "frequency",
                    None,
                    f"Distribution of {numeric_columns[0]}",
                    f"Distribution of numeric variable {numeric_columns[0]}.",
                    "Show data scale, skewness, and possible outliers before modeling.",
                    1,
                )
            )
        if len(numeric_columns) >= 2:
            figures.append(
                self._figure(
                    "F2",
                    "heatmap",
                    numeric_columns[:6],
                    "numeric variables",
                    "correlation",
                    None,
                    "Correlation heatmap",
                    "Correlation heatmap among main numeric variables.",
                    "Support feature selection and explain relationships.",
                    1,
                )
            )
            figures.append(
                self._figure(
                    "F3",
                    "scatter_plot",
                    numeric_columns[:2],
                    numeric_columns[0],
                    numeric_columns[1],
                    None,
                    f"{numeric_columns[1]} versus {numeric_columns[0]}",
                    f"Scatter relationship between {numeric_columns[0]} and {numeric_columns[1]}.",
                    "Inspect linearity and model fit direction.",
                    2,
                )
            )
        if time_columns and numeric_columns:
            figures.append(
                self._figure(
                    "F4",
                    "line_chart",
                    [time_columns[0], numeric_columns[0]],
                    time_columns[0],
                    numeric_columns[0],
                    None,
                    f"Trend of {numeric_columns[0]}",
                    f"Time trend of {numeric_columns[0]}.",
                    "Support prediction, trend analysis, and temporal explanation.",
                    1,
                )
            )
        if categorical_columns and numeric_columns:
            figures.append(
                self._figure(
                    "F5",
                    "bar_chart",
                    [categorical_columns[0], numeric_columns[0]],
                    categorical_columns[0],
                    numeric_columns[0],
                    None,
                    f"{numeric_columns[0]} by {categorical_columns[0]}",
                    f"Grouped comparison of {numeric_columns[0]} by {categorical_columns[0]}.",
                    "Compare groups and report category-level findings.",
                    2,
                )
            )
        if problem_type in {"prediction", "data_driven_analysis"}:
            figures.append(
                self._figure(
                    "F6",
                    "residual_plot",
                    ["actual", "predicted"],
                    "predicted",
                    "residual",
                    None,
                    "Residual diagnostics",
                    "Residual plot for model error diagnostics.",
                    "Explain model accuracy and identify systematic bias.",
                    3,
                )
            )
        figures.append(
            self._figure(
                "F7",
                "sensitivity_curve",
                ["parameter", "metric"],
                "parameter perturbation",
                "model metric",
                None,
                "Sensitivity analysis curve",
                "Sensitivity curve under parameter perturbation.",
                "Support robustness and sensitivity analysis section.",
                3,
            )
        )

        existing_figures = execution_results.get("figures", [])
        result = {
            "agent": self.name,
            "llm_trace": self.llm_client.complete_json(
                "figure_planner",
                {
                    "problem_type": problem_type,
                    "planned_count": len(figures),
                    "existing_figure_count": len(existing_figures),
                },
            ),
            "figure_plan": figures,
            "existing_figures": existing_figures,
        }
        if self.logs_dir is not None:
            write_json(self.logs_dir / "figure_plan.json", result)
        return result

    def _figure(
        self,
        figure_id: str,
        figure_type: str,
        required_data: list[str],
        x_axis: str,
        y_axis: str,
        grouping: str | None,
        title: str,
        caption: str,
        purpose: str,
        priority: int,
    ) -> dict[str, Any]:
        return {
            "figure_id": figure_id,
            "figure_type": figure_type,
            "required_data": required_data,
            "x_axis": x_axis,
            "y_axis": y_axis,
            "grouping": grouping,
            "title": title,
            "caption": caption,
            "purpose_in_paper": purpose,
            "priority": priority,
        }
