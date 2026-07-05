from pathlib import Path

from src.core.llm_client import MockLLMClient
from src.evaluation.batch_runner import BatchRunner


def test_benchmark_batch_runner_runs_minimal_config() -> None:
    root = Path(__file__).resolve().parents[1]
    result = BatchRunner(root, MockLLMClient()).run(root / "benchmark" / "benchmark_config.yaml")

    assert result["task_count"] == 1
    assert Path(result["summary_csv"]).exists()
    assert Path(result["benchmark_report"]).exists()
    assert result["results"][0]["task_id"] == "minimal_problem"
