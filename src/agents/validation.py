from __future__ import annotations

from typing import Any

from src.agents.base import BaseAgent


class ValidationAgent(BaseAgent):
    name = "ValidationAgent"

    def run(self, result_analysis: dict[str, Any], selected_model: dict[str, Any]) -> dict[str, Any]:
        return {
            "agent": self.name,
            "llm_trace": self.llm_client.complete_json("validation", {"finding_count": len(result_analysis.get("findings", []))}),
            "error_analysis": [
                "检查输入数据是否存在缺失值、异常值和量纲差异，必要时保留原始数据与处理后数据的对照。",
                "对趋势预测结果报告残差或历史拟合误差，避免仅给出点估计。",
                "若样本量较小，应在论文中说明统计结论的置信度有限。",
            ],
            "sensitivity_analysis": [
                "对主要权重、阈值或窗口长度做上下 10% 扰动，观察排名、预测值或关键结论是否变化。",
                "若核心变量选择发生变化，比较不同变量组合下的结论一致性。",
            ],
            "robustness_analysis": [
                "采用描述统计基线与简化模型交叉验证方向性结论。",
                "对异常点进行保留和剔除两组计算，比较均值、斜率和相关系数的变化。",
            ],
            "selected_route": selected_model.get("overall_route", ""),
        }

