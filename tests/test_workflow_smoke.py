from pathlib import Path
from uuid import uuid4

from src.core.llm_client import MockLLMClient
from src.core.workflow import WorkflowRunner


def test_sample_workflow_runs() -> None:
    root = Path(__file__).resolve().parents[1]
    output_dir = root / "outputs" / "test_runs" / f"workflow_smoke_{uuid4().hex}"
    runner = WorkflowRunner(
        project_root=root,
        llm_client=MockLLMClient(),
        output_dir=output_dir,
        max_repairs=3,
    )

    state = runner.run(
        root / "examples" / "sample_problem" / "problem.txt",
        root / "examples" / "sample_problem" / "data",
    )

    assert state.execution_result["success"] is True
    assert Path(state.paper["report_path"]).exists()
    assert (output_dir / "code" / "analysis_results.json").exists()
    assert (output_dir / "logs" / "model_recommendations.json").exists()
    assert (output_dir / "logs" / "solution_competition.json").exists()
    assert (output_dir / "logs" / "execution_attempts.json").exists()
    assert (output_dir / "logs" / "paper_pattern_selection.json").exists()
    assert (output_dir / "code_workspace").exists()
    assert state.result_analysis["status"] == "ok"
    assert state.solution_competition["selected_solution"]["solution_name"]
    assert state.selected_model["selected_strategy"]["solution_name"] == state.solution_competition["selected_solution"]["solution_name"]

    report_text = Path(state.paper["report_path"]).read_text(encoding="utf-8")
    assert "## \u5efa\u6a21\u65b9\u6848\u6bd4\u8f83\u4e0e\u9009\u62e9" in report_text
    assert "## \u5404\u5c0f\u95ee\u6a21\u578b\u5efa\u7acb\u4e0e\u6c42\u89e3" in report_text
    assert "## \u6a21\u578b\u8bc4\u4ef7" in report_text
