from src.agents.figure_planner_agent import FigurePlannerAgent
from src.core.llm_client import MockLLMClient


def test_figure_planner_returns_stable_plan() -> None:
    agent = FigurePlannerAgent(MockLLMClient())
    result = agent.run(
        parsed_problem={"problem_type": "prediction"},
        data_profile={"summary": {"numeric_columns": ["x", "y"], "categorical_columns": ["group"], "time_columns": ["date"]}},
        selected_strategy={},
        execution_results={},
    )

    assert result["figure_plan"]
    assert {item["figure_type"] for item in result["figure_plan"]} >= {"histogram", "heatmap", "line_chart"}
    assert all("purpose_in_paper" in item for item in result["figure_plan"])
