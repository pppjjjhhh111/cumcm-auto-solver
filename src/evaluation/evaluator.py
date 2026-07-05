from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from src.core.llm_client import MockLLMClient
from src.core.workflow import WorkflowRunner
from src.evaluation.metrics import compute_metrics


class Evaluator:
    def __init__(self, project_root: Path, llm_client: Any | None = None) -> None:
        self.project_root = project_root.resolve()
        self.llm_client = llm_client or MockLLMClient()

    def run_task(self, task: dict[str, Any], output_dir: Path) -> dict[str, Any]:
        start = time.perf_counter()
        runner = WorkflowRunner(
            project_root=self.project_root,
            llm_client=self.llm_client,
            output_dir=output_dir,
            max_repairs=int(task.get("max_repairs", 3)),
            use_rag=bool(task.get("use_rag", False)),
            enable_reflection=bool(task.get("enable_reflection", True)),
        )
        state = runner.run(Path(task["problem_file"]), Path(task["data_dir"]) if task.get("data_dir") else None)
        metrics = compute_metrics(state, time.perf_counter() - start, task.get("expected_problem_type"))
        return {"task_id": task.get("task_id", output_dir.name), **metrics}
