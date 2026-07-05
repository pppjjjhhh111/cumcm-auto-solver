from __future__ import annotations

import csv
from pathlib import Path
from typing import Any


def write_summary_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = sorted({key for row in rows for key in row.keys()})
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_benchmark_report(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["# Benchmark Report", ""]
    if not rows:
        lines.append("No benchmark tasks were executed.")
    else:
        success = sum(1 for row in rows if row.get("end_to_end_success"))
        lines.append(f"- Tasks: {len(rows)}")
        lines.append(f"- End-to-end success: {success}/{len(rows)}")
        lines.append("")
        lines.append("| task_id | e2e | code | completeness | coverage | figures | repairs | runtime_seconds |")
        lines.append("| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |")
        for row in rows:
            lines.append(
                f"| {row.get('task_id')} | {row.get('end_to_end_success')} | "
                f"{row.get('code_execution_success')} | {row.get('report_completeness_score')} | "
                f"{row.get('question_coverage_score')} | {row.get('figure_count')} | "
                f"{row.get('repair_iterations')} | {row.get('runtime_seconds')} |"
            )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
