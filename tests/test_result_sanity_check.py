from pathlib import Path
from uuid import uuid4

from src.core.llm_client import MockLLMClient
from src.core.state import SolverState
from src.core.workflow import WorkflowRunner


def test_workflow_result_sanity_check_scores_expected_outputs() -> None:
    root = Path(__file__).resolve().parents[1]
    output_root = root / "outputs" / "test_runs" / f"result_sanity_{uuid4().hex}"
    code_dir = output_root / "code"
    figures_dir = output_root / "figures"
    logs_dir = output_root / "logs"
    reports_dir = output_root / "reports"
    for path in (code_dir, figures_dir, logs_dir, reports_dir):
        path.mkdir(parents=True, exist_ok=True)
    (code_dir / "analysis_results.json").write_text('{"row_count": 5}', encoding="utf-8")
    (code_dir / "summary_table.csv").write_text("column,count\nx,5\n", encoding="utf-8")
    (figures_dir / "trend_chart.svg").write_text("<svg></svg>", encoding="utf-8")

    state = SolverState(
        project_root=root,
        problem_path=root / "problem.txt",
        data_path=None,
        output_dir=output_root,
        code_dir=code_dir,
        figures_dir=figures_dir,
        logs_dir=logs_dir,
        reports_dir=reports_dir,
    )
    state.execution_result = {"success": True, "returncode": 0, "stderr": ""}
    state.execution_attempts = [{"attempt": 0, "success": True}]
    runner = WorkflowRunner(project_root=root, llm_client=MockLLMClient(), output_dir=output_root)

    result = runner._build_result_sanity_check(state)

    assert result["status"] == "pass"
    assert result["sanity_score"] == 100
    assert result["repair_iterations"] == 0
