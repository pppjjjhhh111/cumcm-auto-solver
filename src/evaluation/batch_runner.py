from __future__ import annotations

from pathlib import Path
from typing import Any

from src.core.llm_client import MockLLMClient
from src.evaluation.evaluator import Evaluator
from src.evaluation.report_card import write_benchmark_report, write_summary_csv
from src.utils.json_utils import read_json, write_json


class BatchRunner:
    def __init__(self, project_root: Path, llm_client: Any | None = None) -> None:
        self.project_root = project_root.resolve()
        self.llm_client = llm_client or MockLLMClient()

    def run(self, config_path: Path) -> dict[str, Any]:
        config = self._load_config(config_path)
        base_dir = config_path.resolve().parent
        results_dir = (base_dir / config.get("results_dir", "results")).resolve()
        results_dir.mkdir(parents=True, exist_ok=True)
        evaluator = Evaluator(self.project_root, self.llm_client)
        rows = []
        for task in config.get("tasks", []):
            normalized_task = self._normalize_task(task, base_dir)
            task_id = normalized_task.get("task_id", f"task_{len(rows) + 1}")
            task_output_dir = results_dir / task_id
            row = evaluator.run_task(normalized_task, task_output_dir)
            rows.append(row)
            write_json(task_output_dir / "metrics.json", row)
        summary_csv = results_dir / "summary.csv"
        report_md = results_dir / "benchmark_report.md"
        write_summary_csv(summary_csv, rows)
        write_benchmark_report(report_md, rows)
        return {"task_count": len(rows), "summary_csv": str(summary_csv), "benchmark_report": str(report_md), "results": rows}

    def _load_config(self, config_path: Path) -> dict[str, Any]:
        text = config_path.read_text(encoding="utf-8")
        if config_path.suffix.lower() in {".yaml", ".yml"}:
            import yaml

            return yaml.safe_load(text) or {}
        return read_json(config_path)

    def _normalize_task(self, task: dict[str, Any], base_dir: Path) -> dict[str, Any]:
        result = dict(task)
        for key in ("problem_file", "data_dir"):
            if result.get(key):
                path = Path(result[key])
                if not path.is_absolute():
                    candidates = [base_dir / path, self.project_root / path]
                    path = next((candidate for candidate in candidates if candidate.exists()), self.project_root / path)
                result[key] = str(path.resolve())
        return result
