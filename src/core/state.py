from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.utils.json_utils import to_jsonable, write_json


@dataclass
class SolverState:
    """Global structured state passed through the solver workflow."""

    project_root: Path
    problem_path: Path
    data_path: Path | None
    output_dir: Path
    code_dir: Path
    figures_dir: Path
    logs_dir: Path
    reports_dir: Path
    max_repair_attempts: int = 3

    raw_problem: dict[str, Any] = field(default_factory=dict)
    raw_data: list[dict[str, Any]] = field(default_factory=list)
    parsed_problem: dict[str, Any] = field(default_factory=dict)
    decomposed_tasks: dict[str, Any] = field(default_factory=dict)
    data_profile: dict[str, Any] = field(default_factory=dict)
    rag_retrievals: Any = field(default_factory=list)
    candidate_strategies: dict[str, Any] = field(default_factory=dict)
    selected_model: dict[str, Any] = field(default_factory=dict)
    solution_competition: dict[str, Any] = field(default_factory=dict)
    figure_plan: dict[str, Any] = field(default_factory=dict)
    formulas: dict[str, Any] = field(default_factory=dict)
    generated_code: dict[str, Any] = field(default_factory=dict)
    execution_attempts: list[dict[str, Any]] = field(default_factory=list)
    execution_result: dict[str, Any] = field(default_factory=dict)
    result_sanity_check: dict[str, Any] = field(default_factory=dict)
    result_analysis: dict[str, Any] = field(default_factory=dict)
    validation: dict[str, Any] = field(default_factory=dict)
    reflection_report: dict[str, Any] = field(default_factory=dict)
    paper: dict[str, Any] = field(default_factory=dict)
    consistency_check: dict[str, Any] = field(default_factory=dict)
    report_quality: dict[str, Any] = field(default_factory=dict)
    exports: dict[str, Any] = field(default_factory=dict)
    artifacts: dict[str, Any] = field(default_factory=dict)
    errors: list[dict[str, Any]] = field(default_factory=list)

    def to_json_dict(self) -> dict[str, Any]:
        return to_jsonable(self)

    def save_snapshot(self, path: Path) -> None:
        write_json(path, self.to_json_dict())
