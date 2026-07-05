from __future__ import annotations

from pathlib import Path
from typing import Any

from src.agents.base import BaseAgent
from src.utils.json_utils import read_json


class ResultAnalyzerAgent(BaseAgent):
    name = "ResultAnalyzerAgent"

    def run(self, code_dir: Path, execution_result: dict[str, Any]) -> dict[str, Any]:
        result_path = code_dir / "analysis_results.json"
        if not execution_result.get("success"):
            return {
                "agent": self.name,
                "status": "execution_failed",
                "summary": "代码执行失败，无法进行数值结果解释。",
                "stderr": execution_result.get("stderr", ""),
                "figures": [],
                "findings": [],
            }
        if not result_path.exists():
            return {
                "agent": self.name,
                "status": "missing_result_file",
                "summary": "代码执行成功但未找到 analysis_results.json。",
                "figures": [],
                "findings": [],
            }

        results = read_json(result_path)
        findings = []
        for column, stats in results.get("summary", {}).items():
            findings.append(
                f"{column}: 样本数 {stats.get('count')}，均值 {stats.get('mean'):.4g}，"
                f"范围 [{stats.get('min'):.4g}, {stats.get('max'):.4g}]。"
            )
        for corr in results.get("top_correlations", [])[:3]:
            findings.append(
                f"{corr.get('x')} 与 {corr.get('y')} 的 Pearson 相关系数为 {corr.get('pearson'):.4g}，"
                f"样本量 {corr.get('n')}。"
            )
        trend = results.get("trend", {})
        if trend:
            forecast = ", ".join(f"{v:.4g}" for v in trend.get("forecast", []))
            findings.append(
                f"{trend.get('target')} 的线性趋势斜率为 {trend.get('slope'):.4g}，后三期外推值为 {forecast}。"
            )

        return {
            "agent": self.name,
            "llm_trace": self.llm_client.complete_json("result_analyzer", {"success": True}),
            "status": "ok",
            "summary": f"共读取 {results.get('row_count', 0)} 条数据，识别数值字段 {len(results.get('numeric_columns', []))} 个。",
            "findings": findings,
            "figures": results.get("figures", []),
            "raw_result_path": str(result_path),
        }

