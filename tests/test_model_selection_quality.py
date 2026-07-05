from pathlib import Path
from uuid import uuid4

from src.agents.model_selector import ModelSelectorAgent
from src.core.llm_client import MockLLMClient
from src.utils.json_utils import read_json


def test_model_selector_scores_extra_quality_dimensions_and_writes_trace() -> None:
    root = Path(__file__).resolve().parents[1]
    logs_dir = root / "outputs" / "test_runs" / f"model_selection_{uuid4().hex}" / "logs"
    agent = ModelSelectorAgent(MockLLMClient(), logs_dir)

    result = agent.run(
        {
            "strategies": [
                {
                    "task_id": "Q1.1",
                    "task_type": "prediction",
                    "candidates": [
                        {
                            "model_id": "linear_regression",
                            "name": "linear_regression",
                            "category": "prediction",
                            "implementation_difficulty": "low",
                            "why_suitable": "standard coefficient model with equation and forecast output",
                            "expected_output": "forecast and coefficient table",
                            "paper_expression_advantage": "paper expression with coefficients",
                            "risks_and_limitations": ["linear assumption"],
                        },
                        {
                            "model_id": "complex_black_box",
                            "name": "complex_black_box",
                            "category": "prediction",
                            "implementation_difficulty": "high",
                            "why_suitable": "black box prediction",
                            "expected_output": "prediction",
                            "risks_and_limitations": ["overfit", "sensitive"],
                        },
                    ],
                }
            ]
        }
    )

    selected = result["selected_strategies"][0]["selected"]
    assert selected["model_id"] == "linear_regression"
    assert "formula_quality_score" in selected["scores"]
    assert "sensitivity_analysis_potential" in selected["scores"]
    assert result["model_selection_trace"]["task_traces"][0]["selection_reason"]
    trace = read_json(logs_dir / "model_selection_trace.json")
    assert trace["task_traces"][0]["selected_model"]["model_id"] == "linear_regression"
