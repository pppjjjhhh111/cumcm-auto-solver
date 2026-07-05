from pathlib import Path

from src.tools.model_zoo import ModelZoo


def test_model_zoo_yaml_loads() -> None:
    root = Path(__file__).resolve().parents[1]
    zoo = ModelZoo(root / "config" / "model_zoo.yaml")

    models = zoo.load_models()
    categories = zoo.list_categories()

    assert len(models) >= 28
    assert "prediction" in categories
    assert "optimization" in categories
    assert "evaluation" in categories


def test_model_zoo_get_models_by_category() -> None:
    root = Path(__file__).resolve().parents[1]
    zoo = ModelZoo(root / "config" / "model_zoo.yaml")

    prediction_models = zoo.get_models_by_category("prediction")
    prediction_ids = {model["id"] for model in prediction_models}

    assert "linear_regression" in prediction_ids
    assert "grey_prediction_GM11" in prediction_ids


def test_model_zoo_recommend_models_by_problem_type() -> None:
    root = Path(__file__).resolve().parents[1]
    zoo = ModelZoo(root / "config" / "model_zoo.yaml")

    recommendations = zoo.recommend_models(
        problem_type="prediction",
        data_type="tabular",
        task_description="forecast future demand from historical operation data",
    )

    assert len(recommendations) >= 3
    assert recommendations[0]["category"] == "prediction"
    assert all("fit_reason" in model for model in recommendations)
