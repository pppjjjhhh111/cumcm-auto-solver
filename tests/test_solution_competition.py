from src.agents.solution_competition_agent import SolutionCompetitionAgent
from src.core.llm_client import MockLLMClient


def _sample_sub_tasks() -> dict:
    return {
        "tasks": [
            {"id": "Q1.1", "question_id": "Q1", "task_type": "data_preprocessing"},
            {"id": "Q1.2", "question_id": "Q1", "task_type": "prediction"},
        ]
    }


def _sample_candidate_strategies() -> dict:
    return {
        "strategies": [
            {
                "task_id": "Q1.1",
                "task_type": "data_preprocessing",
                "task_description": "profile fields and clean table data",
                "candidates": [
                    {
                        "model_id": "entropy_weight",
                        "name": "Entropy Weight Method",
                        "category": "evaluation",
                        "expected_output": "weights and scores",
                        "implementation_difficulty": "low",
                        "input_data_requirements": ["indicator matrix"],
                        "risks_and_limitations": ["sensitive to scaling"],
                        "recommendation_score": 55,
                    },
                    {
                        "model_id": "pca",
                        "name": "PCA",
                        "category": "evaluation",
                        "expected_output": "components",
                        "implementation_difficulty": "medium",
                        "input_data_requirements": ["numeric matrix"],
                        "risks_and_limitations": ["component interpretation can be weak"],
                        "recommendation_score": 50,
                    },
                ],
            },
            {
                "task_id": "Q1.2",
                "task_type": "prediction",
                "task_description": "forecast future demand",
                "candidates": [
                    {
                        "model_id": "linear_regression",
                        "name": "Linear Regression",
                        "category": "prediction",
                        "expected_output": "predictions",
                        "implementation_difficulty": "low",
                        "input_data_requirements": ["numeric features", "numeric target"],
                        "risks_and_limitations": ["weak for nonlinear relationships"],
                        "recommendation_score": 60,
                    },
                    {
                        "model_id": "gradient_boosting",
                        "name": "Gradient Boosting Regressor",
                        "category": "prediction",
                        "expected_output": "predictions and feature importance",
                        "implementation_difficulty": "high",
                        "input_data_requirements": ["tabular features", "validation set"],
                        "risks_and_limitations": ["tuning-sensitive"],
                        "recommendation_score": 58,
                    },
                ],
            },
        ]
    }


def test_solution_competition_generates_three_solutions() -> None:
    agent = SolutionCompetitionAgent(MockLLMClient())

    result = agent.run(
        _sample_sub_tasks(),
        _sample_candidate_strategies(),
        {"file_count": 1, "table_count": 1, "row_count_preview": 14},
    )

    names = {solution["solution_name"] for solution in result["candidate_solutions"]}
    assert names == {"conservative_solution", "advanced_solution", "hybrid_solution"}
    assert result["selected_solution"]["solution_name"] in names
    assert all("models_for_each_task" in solution for solution in result["candidate_solutions"])


def test_solution_competition_score_dimensions() -> None:
    agent = SolutionCompetitionAgent(MockLLMClient())

    result = agent.run(
        _sample_sub_tasks(),
        _sample_candidate_strategies(),
        {"file_count": 1, "table_count": 1, "row_count_preview": 14},
    )

    score = result["selected_solution"]["score"]
    assert set(score) == {
        "question_alignment",
        "data_feasibility",
        "implementation_feasibility",
        "interpretability",
        "result_visualization_potential",
        "robustness",
        "paper_writing_quality",
        "total_score",
    }
    assert score["total_score"] == sum(value for key, value in score.items() if key != "total_score")
