from pathlib import Path
from uuid import uuid4

from src.tools.data_profiler import DataProfiler


def test_data_profiler_profiles_minimal_csv_and_writes_outputs() -> None:
    root = Path(__file__).resolve().parents[1]
    output_dir = root / "outputs" / "test_runs" / f"data_profiler_{uuid4().hex}"
    profiler = DataProfiler(figures_dir=output_dir / "figures", logs_dir=output_dir / "logs")

    result = profiler.run(root / "tests" / "fixtures" / "minimal_problem" / "data")

    assert result["status"] == "ok"
    assert result["file_count"] >= 1
    assert result["files"][0]["columns"]
    assert "missing_values" in result["files"][0]
    assert (output_dir / "logs" / "data_profile.json").exists()
    assert (output_dir / "figures" / "data_profile").exists()
