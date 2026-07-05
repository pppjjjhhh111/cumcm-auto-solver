from pathlib import Path

from src.tools.paper_pattern_library import PaperPatternLibrary


def test_paper_patterns_yaml_loads() -> None:
    root = Path(__file__).resolve().parents[1]
    library = PaperPatternLibrary(root / "config" / "paper_patterns.yaml")

    patterns = library.load_patterns()

    assert "evaluation_problem" in patterns
    assert "prediction_problem" in patterns
    assert "optimization_problem" in patterns
    assert patterns["prediction_problem"]["section_order"][0] == "数据预处理"


def test_get_pattern_by_problem_type() -> None:
    root = Path(__file__).resolve().parents[1]
    library = PaperPatternLibrary(root / "config" / "paper_patterns.yaml")

    pattern = library.get_pattern("optimization")

    assert pattern["id"] == "optimization_problem"
    assert "决策变量定义" in pattern["section_order"]


def test_recommend_pattern_supports_multiple_question_types() -> None:
    root = Path(__file__).resolve().parents[1]
    library = PaperPatternLibrary(root / "config" / "paper_patterns.yaml")
    parsed_problem = {
        "problem_type": "prediction",
        "questions": [
            {"id": "Q1", "text": "预测未来需求", "objective": "prediction"},
            {"id": "Q2", "text": "制定最优调度方案", "objective": "optimization"},
        ],
    }

    recommendation = library.recommend_pattern(parsed_problem)
    pattern_ids = {pattern["id"] for pattern in recommendation["patterns"]}
    question_pattern_ids = {item["pattern_id"] for item in recommendation["question_patterns"]}

    assert recommendation["primary_pattern"]["id"] == "prediction_problem"
    assert "prediction_problem" in pattern_ids
    assert "optimization_problem" in pattern_ids
    assert question_pattern_ids == {"prediction_problem", "optimization_problem"}
