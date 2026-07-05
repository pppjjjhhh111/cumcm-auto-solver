from pathlib import Path
from uuid import uuid4

from src.agents.code_repair_agent import CodeRepairAgent
from src.core.llm_client import MockLLMClient
from src.tools.python_executor import PythonExecutor
from src.utils.json_utils import write_json


def test_code_repair_loop_captures_and_repairs_error() -> None:
    root = Path(__file__).resolve().parents[1]
    output_root = root / "outputs" / "test_runs" / f"code_repair_{uuid4().hex}"
    code_dir = output_root / "code"
    workspace_dir = output_root / "code_workspace"
    logs_dir = output_root / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    executor = PythonExecutor(root, code_dir, workspace_dir=workspace_dir, timeout_seconds=120)
    repair_agent = CodeRepairAgent(MockLLMClient(), logs_dir)
    bad_code = "prnt('repair loop ok')\n"

    initial_file = executor.write_code("generated_solution.py", bad_code)
    first_result = executor.execute(initial_file)

    assert first_result["success"] is False
    assert "NameError" in first_result["stderr"]
    assert first_result["execution_cwd"] == str(workspace_dir.resolve())

    repair = repair_agent.run(
        original_code=bad_code,
        stderr=first_result["stderr"],
        stdout=first_result["stdout"],
        execution_context={"attempt": 1},
        available_data_files=[],
        previous_repair_attempts=[],
    )

    assert repair["changed"] is True
    assert repair["repaired_code"] == "print('repair loop ok')\n"
    assert repair["confidence_score"] > 0.5

    repaired_file = executor.write_code("attempt_1.py", repair["repaired_code"])
    second_result = executor.execute(repaired_file)
    second_result["repair"] = {k: v for k, v in repair.items() if k != "repaired_code"}
    attempts = [first_result, second_result]
    write_json(logs_dir / "execution_attempts.json", attempts)

    assert second_result["success"] is True
    assert "repair loop ok" in second_result["stdout"]
    assert (code_dir / "attempt_1.py").exists()
    assert (logs_dir / "execution_attempts.json").exists()


def test_python_executor_blocks_project_external_absolute_path() -> None:
    root = Path(__file__).resolve().parents[1]
    output_root = root / "outputs" / "test_runs" / f"executor_safety_{uuid4().hex}"
    executor = PythonExecutor(root, output_root / "code", workspace_dir=output_root / "code_workspace")
    unsafe_code = "from pathlib import Path\nprint(Path('C:/Windows/System32'))\n"

    code_file = executor.write_code("generated_solution.py", unsafe_code)
    result = executor.execute(code_file)

    assert result["success"] is False
    assert "Absolute paths outside project_root" in result["stderr"]
