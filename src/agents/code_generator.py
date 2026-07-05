from __future__ import annotations

import json
from pathlib import Path
from textwrap import dedent
from typing import Any

from src.agents.base import BaseAgent


class CodeGeneratorAgent(BaseAgent):
    name = "CodeGeneratorAgent"

    def run(
        self,
        project_root: Path,
        data_path: Path | None,
        figures_dir: Path,
        selected_model: dict[str, Any],
        figure_plan: dict[str, Any] | None = None,
        data_profile: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        code = self._build_code(project_root, data_path, figure_plan or {})
        return {
            "agent": self.name,
            "llm_trace": self.llm_client.complete_json(
                "code_generator",
                {
                    "route": selected_model.get("overall_route"),
                    "has_data_path": data_path is not None,
                    "planned_figures": len((figure_plan or {}).get("figure_plan", [])),
                    "profiled_tables": (data_profile or {}).get("table_count", 0),
                },
            ),
            "filename": "generated_solution.py",
            "language": "python",
            "code": code,
            "notes": "Generated code uses standard library only and reads project-local data through executor environment variables.",
        }

    def _build_code(self, project_root: Path, data_path: Path | None, figure_plan: dict[str, Any]) -> str:
        data_rel = ""
        if data_path is not None:
            try:
                data_rel = data_path.resolve().relative_to(project_root.resolve()).as_posix()
            except ValueError:
                data_rel = ""
        figure_plan_json = json.dumps(
            [
                {
                    "figure_id": item.get("figure_id"),
                    "figure_type": item.get("figure_type"),
                    "title": item.get("title"),
                    "caption": item.get("caption"),
                    "purpose_in_paper": item.get("purpose_in_paper"),
                }
                for item in figure_plan.get("figure_plan", [])[:8]
            ],
            ensure_ascii=False,
        )
        data_rel_literal = json.dumps(data_rel, ensure_ascii=False)
        return dedent(
            f"""
            from __future__ import annotations

            import csv
            import json
            import math
            import os
            import statistics
            from pathlib import Path


            DATA_RELATIVE_PATH = {data_rel_literal}
            FIGURE_PLAN = {figure_plan_json}
            PROJECT_ROOT = Path(os.environ.get("CUMCM_PROJECT_ROOT", ".")).resolve()
            CODE_DIR = Path(os.environ.get("CUMCM_CODE_OUTPUT_DIR", Path(__file__).resolve().parent)).resolve()
            FIGURES_DIR = Path(os.environ.get("CUMCM_FIGURES_DIR", CODE_DIR.parent / "figures")).resolve()
            DATA_PATH = (PROJECT_ROOT / DATA_RELATIVE_PATH).resolve() if DATA_RELATIVE_PATH else None
            CODE_DIR.mkdir(parents=True, exist_ok=True)
            FIGURES_DIR.mkdir(parents=True, exist_ok=True)


            def to_float(value):
                if value is None:
                    return None
                text = str(value).strip().replace(",", "")
                if text == "":
                    return None
                try:
                    return float(text)
                except ValueError:
                    return None


            def discover_csv_files(data_path):
                if data_path is None:
                    return []
                if data_path.is_file() and data_path.suffix.lower() == ".csv":
                    return [data_path]
                if data_path.is_dir():
                    return sorted(data_path.rglob("*.csv"))
                return []


            def read_csv(path):
                with path.open("r", encoding="utf-8-sig", newline="") as handle:
                    reader = csv.DictReader(handle)
                    return list(reader)


            def numeric_columns(rows):
                if not rows:
                    return []
                columns = list(rows[0].keys())
                result = []
                for column in columns:
                    values = [to_float(row.get(column)) for row in rows]
                    valid = [value for value in values if value is not None and math.isfinite(value)]
                    if len(valid) >= max(2, len(rows) // 2):
                        result.append(column)
                return result


            def categorical_columns(rows, numeric):
                if not rows:
                    return []
                numeric_set = set(numeric)
                result = []
                for column in rows[0].keys():
                    if column in numeric_set:
                        continue
                    values = [str(row.get(column, "")).strip() for row in rows if str(row.get(column, "")).strip()]
                    if values and len(set(values)) <= max(20, len(values) * 0.7):
                        result.append(column)
                return result


            def summarize(rows, columns):
                summaries = {{}}
                for column in columns:
                    values = [to_float(row.get(column)) for row in rows]
                    values = [value for value in values if value is not None and math.isfinite(value)]
                    if not values:
                        continue
                    summaries[column] = {{
                        "count": len(values),
                        "min": min(values),
                        "max": max(values),
                        "mean": statistics.fmean(values),
                        "std": statistics.stdev(values) if len(values) > 1 else 0.0,
                    }}
                return summaries


            def pearson(xs, ys):
                if len(xs) != len(ys) or len(xs) < 2:
                    return None
                mean_x = statistics.fmean(xs)
                mean_y = statistics.fmean(ys)
                numerator = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
                denom_x = math.sqrt(sum((x - mean_x) ** 2 for x in xs))
                denom_y = math.sqrt(sum((y - mean_y) ** 2 for y in ys))
                if denom_x == 0 or denom_y == 0:
                    return None
                return numerator / (denom_x * denom_y)


            def correlations(rows, columns):
                result = []
                for index, left in enumerate(columns):
                    for right in columns[index + 1:]:
                        pairs = []
                        for row in rows:
                            x = to_float(row.get(left))
                            y = to_float(row.get(right))
                            if x is not None and y is not None and math.isfinite(x) and math.isfinite(y):
                                pairs.append((x, y))
                        if len(pairs) >= 3:
                            corr = pearson([x for x, _ in pairs], [y for _, y in pairs])
                            if corr is not None:
                                result.append({{"x": left, "y": right, "pearson": corr, "n": len(pairs)}})
                result.sort(key=lambda item: abs(item["pearson"]), reverse=True)
                return result


            def linear_trend(values):
                if len(values) < 2:
                    return {{"slope": 0.0, "intercept": values[0] if values else 0.0, "forecast": []}}
                xs = list(range(len(values)))
                mean_x = statistics.fmean(xs)
                mean_y = statistics.fmean(values)
                denom = sum((x - mean_x) ** 2 for x in xs)
                slope = 0.0 if denom == 0 else sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, values)) / denom
                intercept = mean_y - slope * mean_x
                forecast = [intercept + slope * (len(values) + step) for step in range(1, 4)]
                return {{"slope": slope, "intercept": intercept, "forecast": forecast}}


            def write_summary_csv(path, summaries):
                with path.open("w", encoding="utf-8", newline="") as handle:
                    writer = csv.writer(handle)
                    writer.writerow(["column", "count", "min", "max", "mean", "std"])
                    for column, stats in summaries.items():
                        writer.writerow([
                            column,
                            stats["count"],
                            f"{{stats['min']:.6g}}",
                            f"{{stats['max']:.6g}}",
                            f"{{stats['mean']:.6g}}",
                            f"{{stats['std']:.6g}}",
                        ])


            def write_svg_line_chart(path, values, title):
                width, height = 900, 420
                margin = 56
                if not values:
                    path.write_text("<svg xmlns='http://www.w3.org/2000/svg'></svg>", encoding="utf-8")
                    return
                min_v, max_v = min(values), max(values)
                span = max(max_v - min_v, 1e-9)
                x_span = max(len(values) - 1, 1)
                points = []
                for idx, value in enumerate(values):
                    x = margin + idx * (width - 2 * margin) / x_span
                    y = height - margin - (value - min_v) * (height - 2 * margin) / span
                    points.append((x, y))
                polyline = " ".join(f"{{x:.1f}},{{y:.1f}}" for x, y in points)
                circles = "\\n".join(f"<circle cx='{{x:.1f}}' cy='{{y:.1f}}' r='3' fill='#2563eb'/>" for x, y in points)
                svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{{width}}" height="{{height}}" viewBox="0 0 {{width}} {{height}}">
              <rect width="100%" height="100%" fill="white"/>
              <text x="{{margin}}" y="30" font-size="20" font-family="Arial" fill="#111827">{{title}}</text>
              <line x1="{{margin}}" y1="{{height - margin}}" x2="{{width - margin}}" y2="{{height - margin}}" stroke="#374151"/>
              <line x1="{{margin}}" y1="{{margin}}" x2="{{margin}}" y2="{{height - margin}}" stroke="#374151"/>
              <polyline fill="none" stroke="#2563eb" stroke-width="3" points="{{polyline}}"/>
              {{circles}}
            </svg>'''
                path.write_text(svg, encoding="utf-8")


            def write_svg_bar_chart(path, values, title):
                width = 900
                height = max(260, 90 + 30 * max(len(values), 1))
                max_v = max([value for _, value in values] or [1.0]) or 1.0
                rows = []
                for idx, (label, value) in enumerate(values[:12]):
                    y = 60 + idx * 30
                    bar_width = 620 * value / max_v
                    rows.append(
                        f"<text x='20' y='{{y + 16}}' font-size='12' font-family='Arial'>{{label[:28]}}</text>"
                        f"<rect x='230' y='{{y}}' width='{{bar_width:.1f}}' height='20' fill='#16a34a'/>"
                        f"<text x='{{240 + bar_width:.1f}}' y='{{y + 16}}' font-size='12' font-family='Arial'>{{value:.4g}}</text>"
                    )
                svg = "<svg xmlns='http://www.w3.org/2000/svg' width='%d' height='%d'>" % (width, height)
                svg += "<rect width='100%' height='100%' fill='white'/>"
                svg += f"<text x='20' y='32' font-size='20' font-family='Arial'>{{title}}</text>"
                svg += "".join(rows) + "</svg>"
                path.write_text(svg, encoding="utf-8")


            def write_planned_placeholder(figures_dir, plan):
                files = []
                for item in plan:
                    figure_id = str(item.get("figure_id") or "planned")
                    title = str(item.get("title") or item.get("figure_type") or "Planned figure")
                    path = figures_dir / f"planned_{{figure_id}}.svg"
                    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="900" height="260">
              <rect width="100%" height="100%" fill="white"/>
              <text x="40" y="60" font-size="24" font-family="Arial" fill="#111827">{{title}}</text>
              <text x="40" y="105" font-size="15" font-family="Arial" fill="#374151">Type: {{item.get("figure_type", "")}}</text>
              <text x="40" y="135" font-size="15" font-family="Arial" fill="#374151">Purpose: {{item.get("purpose_in_paper", "")}}</text>
            </svg>'''
                    path.write_text(svg, encoding="utf-8")
                    files.append(str(path))
                return files


            def analyze():
                csv_files = discover_csv_files(DATA_PATH)
                combined = []
                per_file = []
                for csv_file in csv_files:
                    rows = read_csv(csv_file)
                    nums = numeric_columns(rows)
                    cats = categorical_columns(rows, nums)
                    summaries = summarize(rows, nums)
                    per_file.append({{
                        "file": str(csv_file.relative_to(PROJECT_ROOT)) if str(csv_file).startswith(str(PROJECT_ROOT)) else csv_file.name,
                        "row_count": len(rows),
                        "numeric_columns": nums,
                        "categorical_columns": cats,
                        "summaries": summaries,
                        "correlations": correlations(rows, nums),
                    }})
                    combined.extend(rows)

                combined_numeric = numeric_columns(combined)
                combined_categorical = categorical_columns(combined, combined_numeric)
                combined_summary = summarize(combined, combined_numeric)
                combined_correlations = correlations(combined, combined_numeric)
                trend = {{}}
                figure_files = []
                if combined_numeric:
                    target = combined_numeric[0]
                    values = [to_float(row.get(target)) for row in combined]
                    values = [value for value in values if value is not None and math.isfinite(value)]
                    trend = {{"target": target, **linear_trend(values)}}
                    figure_path = FIGURES_DIR / "trend_chart.svg"
                    write_svg_line_chart(figure_path, values, f"Trend of {{target}}")
                    figure_files.append(str(figure_path))
                if combined_categorical:
                    column = combined_categorical[0]
                    counts = {{}}
                    for row in combined:
                        key = str(row.get(column, "")).strip() or "missing"
                        counts[key] = counts.get(key, 0) + 1
                    bar_path = FIGURES_DIR / "category_frequency.svg"
                    write_svg_bar_chart(bar_path, sorted(counts.items(), key=lambda item: item[1], reverse=True), f"Frequency of {{column}}")
                    figure_files.append(str(bar_path))
                figure_files.extend(write_planned_placeholder(FIGURES_DIR, FIGURE_PLAN))

                summary_csv = CODE_DIR / "summary_table.csv"
                write_summary_csv(summary_csv, combined_summary)
                result = {{
                    "csv_files": [str(path.relative_to(PROJECT_ROOT)) if str(path).startswith(str(PROJECT_ROOT)) else path.name for path in csv_files],
                    "row_count": len(combined),
                    "numeric_columns": combined_numeric,
                    "categorical_columns": combined_categorical,
                    "summary": combined_summary,
                    "top_correlations": combined_correlations[:5],
                    "trend": trend,
                    "figures": figure_files,
                    "figure_plan": FIGURE_PLAN,
                    "per_file": per_file,
                    "notes": [
                        "This is a deterministic baseline analysis generated by the Auto-Solver workbench.",
                        "Generated code runs inside outputs/code_workspace and writes artifacts to controlled output directories.",
                    ],
                }}
                output_path = CODE_DIR / "analysis_results.json"
                output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
                print(f"Loaded {{len(csv_files)}} CSV file(s), {{len(combined)}} row(s).")
                print(f"Numeric columns: {{', '.join(combined_numeric) if combined_numeric else 'none'}}")
                print(f"Saved analysis results to {{output_path}}")
                print(f"Saved figures: {{', '.join(figure_files) if figure_files else 'none'}}")


            if __name__ == "__main__":
                analyze()
            """
        ).strip() + "\n"
