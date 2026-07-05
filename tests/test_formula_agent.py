from src.agents.formula_agent import FormulaAgent
from src.core.llm_client import MockLLMClient


def test_formula_agent_generates_latex_and_checks() -> None:
    agent = FormulaAgent(MockLLMClient())
    result = agent.run(
        selected_strategy={"selected_strategies": [{"selected": {"model_id": "linear_regression"}}]},
        sub_tasks={"tasks": [{"id": "Q1.1"}]},
        parsed_problem={"problem_type": "prediction"},
    )

    assert result["latex_blocks"]
    assert result["variables"]
    assert result["checks"]["variables_defined"] is True
    assert "latex" in result["latex_blocks"][0]
