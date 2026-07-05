from pathlib import Path

from src.core.llm_client import MockLLMClient
from src.evaluation.batch_runner import BatchRunner
from src.evaluation.metrics import compute_metrics


def test_benchmark_batch_runner_runs_minimal_config() -> None:
    root = Path(__file__).resolve().parents[1]
    result = BatchRunner(root, MockLLMClient()).run(root / "benchmark" / "benchmark_config.yaml")

    assert result["task_count"] == 1
    assert Path(result["summary_csv"]).exists()
    assert Path(result["benchmark_report"]).exists()
    assert result["results"][0]["task_id"] == "minimal_problem"


def test_benchmark_quality_config_exists_and_metrics_include_quality_fields() -> None:
    root = Path(__file__).resolve().parents[1]
    quality_config = root / "benchmark" / "quality_config.yaml"
    quality_case = root / "benchmark" / "quality_cases" / "prediction_case" / "problem.txt"

    class DummyState:
        paper = {"report_path": str(quality_case)}
        execution_result = {"success": True}
        result_analysis = {"figures": ["fig.svg"]}
        parsed_problem = {"questions": [{"id": "Q1"}], "problem_type": "prediction"}
        raw_data = [{"path": "data.csv"}]
        execution_attempts = [{"attempt": 0}]
        report_quality = {"final_score": 88.0}
        consistency_check = {"consistency_score": 92.0}
        result_sanity_check = {"sanity_score": 100.0}

    metrics = compute_metrics(DummyState(), runtime_seconds=1.25, expected_problem_type="prediction")

    assert quality_config.exists()
    assert quality_case.exists()
    assert metrics["report_quality_score"] == 88.0
    assert metrics["consistency_score"] == 92.0
    assert metrics["result_sanity_score"] == 100.0
