from __future__ import annotations

from pathlib import Path
from typing import Any

from src.agents.base import BaseAgent
from src.rag.reference_utils import reference_summary, select_references
from src.tools.paper_pattern_library import PaperPatternLibrary
from src.utils.json_utils import write_json


class PaperWriterAgent(BaseAgent):
    name = "PaperWriterAgent"

    REQUIRED_SECTIONS = [
        "摘要",
        "关键词",
        "问题重述",
        "问题分析",
        "建模方案比较与选择",
        "模型选择理由",
        "模型假设",
        "符号说明",
        "数据预处理与探索性分析",
        "各小问模型建立与求解",
        "结果分析",
        "灵敏度分析",
        "模型反思与改进说明",
        "模型评价",
        "参考文献",
        "附录代码",
    ]

    def __init__(self, *args: Any, pattern_library: PaperPatternLibrary | None = None, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.pattern_library = pattern_library or PaperPatternLibrary()

    def run(
        self,
        parsed_problem: dict[str, Any],
        decomposed_tasks: dict[str, Any],
        selected_model: dict[str, Any],
        result_analysis: dict[str, Any],
        validation: dict[str, Any],
        generated_code: dict[str, Any],
        reports_dir: Path,
        data_profile: dict[str, Any] | None = None,
        figure_plan: dict[str, Any] | None = None,
        formulas: dict[str, Any] | None = None,
        reflection_report: dict[str, Any] | None = None,
        retrieved_references: Any = None,
    ) -> dict[str, Any]:
        reports_dir.mkdir(parents=True, exist_ok=True)
        report_path = reports_dir / "solution_report.md"
        data_profile = data_profile or {}
        figure_plan = figure_plan or {}
        formulas = formulas or {}
        reflection_report = reflection_report or {}
        paper_references = select_references(retrieved_references, purpose="paper", limit=5)
        pattern_selection = self.pattern_library.recommend_pattern(parsed_problem)
        if self.logs_dir is not None:
            write_json(self.logs_dir / "paper_pattern_selection.json", pattern_selection)

        markdown = self._build_markdown(
            parsed_problem=parsed_problem,
            decomposed_tasks=decomposed_tasks,
            selected_model=selected_model,
            result_analysis=result_analysis,
            validation=validation,
            code=generated_code.get("code", ""),
            pattern_selection=pattern_selection,
            data_profile=data_profile,
            figure_plan=figure_plan,
            formulas=formulas,
            reflection_report=reflection_report,
            paper_references=paper_references,
        )
        report_path.write_text(markdown, encoding="utf-8")
        return {
            "agent": self.name,
            "llm_trace": self.llm_client.complete_json(
                "paper_writer",
                {
                    "section_count": len(self.REQUIRED_SECTIONS),
                    "primary_pattern": pattern_selection.get("primary_pattern", {}).get("id"),
                    "has_data_profile": bool(data_profile.get("files")),
                    "formula_count": len(formulas.get("latex_blocks", [])),
                    "retrieved_reference_count": len(paper_references),
                },
            ),
            "report_path": str(report_path),
            "sections": self.REQUIRED_SECTIONS,
            "pattern_selection": pattern_selection,
            "retrieved_references": paper_references,
            "knowledge_guidance": reference_summary(paper_references),
            "markdown": markdown,
        }

    def _build_markdown(
        self,
        parsed_problem: dict[str, Any],
        decomposed_tasks: dict[str, Any],
        selected_model: dict[str, Any],
        result_analysis: dict[str, Any],
        validation: dict[str, Any],
        code: str,
        pattern_selection: dict[str, Any],
        data_profile: dict[str, Any],
        figure_plan: dict[str, Any],
        formulas: dict[str, Any],
        reflection_report: dict[str, Any],
        paper_references: list[dict[str, Any]],
    ) -> str:
        questions = parsed_problem.get("questions", [])
        question_lines = "\n".join(f"- {q.get('id')}: {q.get('text')}" for q in questions) or "- 未识别到明确小问。"
        keywords = "；".join(parsed_problem.get("keywords", [])) or "数学建模；自动求解；数据分析"
        pattern_summary = self._pattern_detail_lines(pattern_selection)
        paper_guidance = self._paper_guidance_section(paper_references)
        assumptions = self._combined_list(pattern_selection, "common_assumptions")
        solution_competition = self._solution_competition_section(selected_model)
        model_selection_reason = self._model_selection_reason_section(selected_model)
        symbol_table = self._symbol_table(formulas)
        formula_blocks = self._formula_blocks(formulas)
        data_profile_section = self._data_profile_section(data_profile)
        question_sections = self._question_sections(questions, decomposed_tasks, selected_model, result_analysis, pattern_selection, formulas)
        result_section = self._result_section(result_analysis, figure_plan)
        validation_section = self._validation_section(validation, pattern_selection)
        reflection_section = self._reflection_section(reflection_report)
        execution_failure_section = self._execution_failure_section(result_analysis)

        return f"""# 数学建模论文草稿

## 摘要

本文面向给定数学建模题，构建了从题面解析、数据画像、模型推荐、多方案竞争、公式组织、代码执行、结果解释到报告生成的自动化求解流程。系统识别的题型为 `{parsed_problem.get('problem_type', 'general_modeling')}`，并结合 Model Zoo 与 Paper Pattern Library 生成可复现的建模路线。本文输出为教学研究和往年题复现实验草稿，仍需要人工结合题目背景进行最终润色。

## 关键词

{keywords}；Auto-Solver；模型库；数据画像；反思迭代

## 问题重述

{parsed_problem.get('background', '')}

小问列表：

{question_lines}

数据说明：

{parsed_problem.get('data_description', '')}

## 问题分析

系统解析得到的整体题型为 `{parsed_problem.get('problem_type', 'general_modeling')}`。论文结构根据题型动态组合，主要写作套路如下：

{pattern_summary}

{paper_guidance}

## 建模方案比较与选择

{solution_competition}

## 模型选择理由

{model_selection_reason}

## 模型假设

{self._bullet_lines(assumptions)}

## 符号说明

{symbol_table}

## 数据预处理与探索性分析

{data_profile_section}

## 各小问模型建立与求解

{formula_blocks}

{question_sections}

## 结果分析

{result_section}

{execution_failure_section}

## 灵敏度分析

{validation_section}

## 模型反思与改进说明

{reflection_section}

## 模型评价

优点：

1. 采用数据画像、模型库推荐和多方案竞争，路线选择更可解释。
2. 自动生成代码在 `outputs/code_workspace` 中执行，并保存执行、修复和安全检查日志。
3. 报告结构根据题型模板组织，覆盖竞赛论文常见章节。

不足：

1. 当前报告仍是论文草稿，复杂题目的专业推导和背景解释需要人工复核。
2. MockLLM 模式下的建模路线偏保守，真实 LLM 可增强题意理解和文本质量。
3. 第一版 RAG 使用关键词检索，适合本地方法启发，但不等同于严格语义检索。

## 参考文献

[1] 全国大学生数学建模竞赛历年赛题与优秀论文资料。

[2] Montgomery, D. C., Peck, E. A., & Vining, G. G. Introduction to Linear Regression Analysis.

[3] Han, J., Kamber, M., & Pei, J. Data Mining: Concepts and Techniques.

## 附录代码

```python
{code}
```
"""

    def _solution_competition_section(self, selected_model: dict[str, Any]) -> str:
        competition = selected_model.get("solution_competition", {})
        candidates = competition.get("candidate_solutions", [])
        selected = competition.get("selected_solution") or selected_model.get("selected_solution", {})
        if not candidates:
            return "暂无多方案竞争结果，采用模型选择器输出的默认路线。"
        rows = ["| 方案 | 总分 | 难度 | 总体思路 |", "| --- | ---: | --- | --- |"]
        for solution in candidates:
            rows.append(
                f"| {solution.get('solution_name', '')} | "
                f"{(solution.get('score') or {}).get('total_score', '')} | "
                f"{solution.get('implementation_difficulty', '')} | "
                f"{solution.get('overall_idea', '')} |"
            )
        risks = self._bullet_lines(selected.get("risk_points", []))
        return "\n".join(rows) + (
            f"\n\n最终选择 `{selected.get('solution_name', '')}`，"
            f"总分 {(selected.get('score') or {}).get('total_score', '')}。\n\n"
            f"选择理由：{selected.get('paper_narrative', selected.get('overall_idea', ''))}\n\n"
            f"风险提示：\n\n{risks}"
        )

    def _paper_guidance_section(self, paper_references: list[dict[str, Any]]) -> str:
        if not paper_references:
            return "本地知识库未提供可用论文模板参考，报告按内置 Paper Pattern Library 组织。"
        return (
            "本地知识库写作参考：系统仅使用以下条目的结构启发，不复制原文。"
            f"{reference_summary(paper_references)}。"
        )

    def _model_selection_reason_section(self, selected_model: dict[str, Any]) -> str:
        trace = selected_model.get("model_selection_trace", {})
        task_traces = trace.get("task_traces", [])
        if not task_traces:
            return "暂无模型选择追踪日志，请查看 `outputs/logs/model_selection_trace.json`。"
        lines = [
            "| 任务 | 选中模型 | 总分 | 主要理由 | 主要风险 |",
            "| --- | --- | ---: | --- | --- |",
        ]
        for item in task_traces:
            selected = item.get("selected_model", {})
            scores = selected.get("scores", {})
            risks = item.get("current_model_risks", [])
            lines.append(
                f"| {item.get('task_id', '')} | "
                f"{selected.get('name', selected.get('model_id', ''))} | "
                f"{scores.get('total_score', selected.get('total_score', ''))} | "
                f"{item.get('selection_reason', '')} | "
                f"{'; '.join(str(risk) for risk in risks[:3]) or '-'} |"
            )
        rejected_lines = []
        for item in task_traces:
            rejected = item.get("rejected_candidates", [])
            if not rejected:
                continue
            for candidate in rejected[:2]:
                rejected_lines.append(
                    f"- 任务 {item.get('task_id')} 的备选 `{candidate.get('name')}` 未入选："
                    f"{candidate.get('why_not_selected')}"
                )
        sections = ["\n".join(lines)]
        if rejected_lines:
            sections.append("备选模型取舍说明：\n\n" + "\n".join(rejected_lines))
        sections.append("详细评分日志保存于 `outputs/logs/model_selection_trace.json`。")
        return "\n\n".join(sections)

    def _symbol_table(self, formulas: dict[str, Any]) -> str:
        variables = formulas.get("variables") or [
            {"symbol": "x_i", "meaning": "第 i 个样本或对象"},
            {"symbol": "y_i", "meaning": "观测值或目标变量"},
            {"symbol": "\\hat y_i", "meaning": "预测值或估计值"},
            {"symbol": "w_j", "meaning": "第 j 个指标权重"},
            {"symbol": "S_i", "meaning": "综合得分"},
        ]
        rows = ["| 符号 | 含义 |", "| --- | --- |"]
        for item in variables:
            rows.append(f"| ${item.get('symbol')}$ | {item.get('meaning')} |")
        return "\n".join(rows)

    def _formula_blocks(self, formulas: dict[str, Any]) -> str:
        blocks = []
        for item in formulas.get("latex_blocks", []):
            blocks.append(
                f"模型 `{item.get('model', '')}` 的核心表达为：\n\n"
                f"$$\n{item.get('latex', '')}\n$$\n\n"
                f"{item.get('explanation', '')}"
            )
        return "\n\n".join(blocks) if blocks else "本题采用描述统计与基线模型，核心公式将在人工复核时进一步细化。"

    def _data_profile_section(self, data_profile: dict[str, Any]) -> str:
        if not data_profile.get("files"):
            warnings = self._bullet_lines(data_profile.get("warnings", ["未提供结构化数据文件，跳过数据画像。"]))
            return f"数据画像未执行或无可用数据文件。\n\n{warnings}"
        lines = [
            f"系统共识别 `{data_profile.get('file_count', 0)}` 个数据文件、`{data_profile.get('table_count', 0)}` 个表。"
        ]
        summary = data_profile.get("summary", {})
        lines.append(f"- 数值字段：{', '.join(summary.get('numeric_columns', [])[:12]) or '无'}")
        lines.append(f"- 类别字段：{', '.join(summary.get('categorical_columns', [])[:12]) or '无'}")
        lines.append(f"- 时间字段：{', '.join(summary.get('time_columns', [])[:8]) or '无'}")
        lines.append("")
        lines.append("建议预处理步骤：")
        lines.append(self._bullet_lines(summary.get("recommended_preprocessing_steps", [])))
        figure_lines = []
        for item in summary.get("recommended_figures", [])[:10]:
            figure_lines.append(f"- {item.get('figure_type')}: {item.get('caption')} (`{item.get('path')}`)")
        if figure_lines:
            lines.append("\n自动生成的数据画像图：")
            lines.extend(figure_lines)
        return "\n".join(lines)

    def _question_sections(
        self,
        questions: list[dict[str, Any]],
        decomposed_tasks: dict[str, Any],
        selected_model: dict[str, Any],
        result_analysis: dict[str, Any],
        pattern_selection: dict[str, Any],
        formulas: dict[str, Any],
    ) -> str:
        if not questions:
            return "### 综合建模任务\n\n未识别到明确小问，系统按综合数据分析任务组织建模。"
        tasks_by_question = self._group_tasks_by_question(decomposed_tasks)
        selected_by_question = self._group_selected_by_question(selected_model)
        sections = []
        for question in questions:
            qid = question.get("id", "Q")
            tasks = self._bullet_lines(
                [
                    f"{task.get('id')} ({task.get('task_type')}): {task.get('description')}"
                    for task in tasks_by_question.get(qid, [])
                ]
            )
            selected_lines = self._selected_model_lines(selected_by_question.get(qid, []))
            sections.append(
                f"""### {qid} {question.get('text', '')}

#### 问题分析

该小问目标被识别为 `{question.get('objective', 'unknown')}`。系统将其拆分为数据整理、模型建立与结果解释三个环节。

任务拆解：

{tasks}

#### 模型建立

{selected_lines}

#### 模型求解

自动生成的 Python 代码写入 `outputs/code`，并在 `outputs/code_workspace` 中运行。核心数值结果写入 `analysis_results.json` 和 `summary_table.csv`，图表写入 `outputs/figures`。

#### 结果分析

结合自动执行结果，本小问应重点解释模型输出、图表趋势、异常点和结论适用范围。当前执行摘要：{result_analysis.get('summary', '')}
"""
            )
        return "\n\n".join(sections)

    def _result_section(self, result_analysis: dict[str, Any], figure_plan: dict[str, Any]) -> str:
        findings = self._bullet_lines(result_analysis.get("findings", []))
        generated_figures = self._bullet_lines(result_analysis.get("figures", []))
        planned = []
        for item in figure_plan.get("figure_plan", []):
            planned.append(
                f"{item.get('figure_id')} {item.get('title')}：{item.get('caption')} 用途：{item.get('purpose_in_paper')}"
            )
        return (
            f"执行状态：`{result_analysis.get('status', 'unknown')}`。\n\n"
            f"主要发现：\n\n{findings}\n\n"
            f"生成图表：\n\n{generated_figures}\n\n"
            f"论文图表规划与图注：\n\n{self._bullet_lines(planned)}"
        )

    def _validation_section(self, validation: dict[str, Any], pattern_selection: dict[str, Any]) -> str:
        methods = self._combined_list(pattern_selection, "common_validation_methods")
        return (
            f"推荐验证方法：\n\n{self._bullet_lines(methods)}\n\n"
            f"误差分析：\n\n{self._bullet_lines(validation.get('error_analysis', []))}\n\n"
            f"灵敏度分析：\n\n{self._bullet_lines(validation.get('sensitivity_analysis', []))}\n\n"
            f"鲁棒性分析：\n\n{self._bullet_lines(validation.get('robustness_analysis', []))}"
        )

    def _reflection_section(self, reflection_report: dict[str, Any]) -> str:
        if not reflection_report:
            return "初稿生成后将由 ReflectionAgent 进行完整性、数据使用、图表、公式和执行状态检查。"
        lines = [
            f"- 完整性得分：{reflection_report.get('completeness_score')}",
            f"- 题意匹配得分：{reflection_report.get('question_alignment_score')}",
            f"- 数据使用得分：{reflection_report.get('data_usage_score')}",
            f"- 是否需要修订：{reflection_report.get('need_revision')}",
            "",
            "发现的问题：",
            self._bullet_lines(reflection_report.get("detected_problems", [])),
            "",
            "改进建议：",
            self._bullet_lines(reflection_report.get("suggested_fixes", [])),
        ]
        return "\n".join(lines)

    def _execution_failure_section(self, result_analysis: dict[str, Any]) -> str:
        if result_analysis.get("status") != "execution_failed":
            return ""
        stderr = result_analysis.get("stderr", "")
        return f"""### 代码执行失败说明

自动修复后代码仍未成功执行。错误摘要如下：

```text
{stderr[-3000:]}
```

人工修改建议：

- 检查 `outputs/logs/execution_attempts.json` 中每次执行和修复记录。
- 检查 `outputs/logs/code_safety.json` 中是否存在安全拦截。
- 手动修改 `outputs/code/attempt_*.py` 后在受控目录中复现运行。
"""

    def _pattern_detail_lines(self, pattern_selection: dict[str, Any]) -> str:
        lines = []
        for pattern in pattern_selection.get("patterns", []):
            lines.append(f"- {pattern.get('name', pattern.get('id'))}: {' -> '.join(pattern.get('section_order', []))}")
        return "\n".join(lines) or "- 通用建模结构：数据预处理 -> 模型建立 -> 求解 -> 分析验证"

    def _combined_list(self, pattern_selection: dict[str, Any], key: str) -> list[str]:
        values = []
        for pattern in pattern_selection.get("patterns", []):
            for item in pattern.get(key, []):
                if item not in values:
                    values.append(item)
        return values or ["根据题目和数据情况补充。"]

    def _group_tasks_by_question(self, decomposed_tasks: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
        grouped: dict[str, list[dict[str, Any]]] = {}
        for task in decomposed_tasks.get("tasks", []):
            question_id = task.get("question_id") or str(task.get("id", "")).split(".")[0]
            grouped.setdefault(question_id, []).append(task)
        return grouped

    def _group_selected_by_question(self, selected_model: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
        grouped: dict[str, list[dict[str, Any]]] = {}
        for item in selected_model.get("selected_strategies", []):
            task_id = str(item.get("task_id", ""))
            question_id = task_id.split(".")[0] if task_id else "Q"
            grouped.setdefault(question_id, []).append(item)
        return grouped

    def _selected_model_lines(self, selected_items: list[dict[str, Any]]) -> str:
        lines = []
        for item in selected_items:
            selected = item.get("selected") or {}
            scores = selected.get("scores", {})
            score_text = f"，综合得分 {scores.get('total_score')}" if scores else ""
            lines.append(
                f"- {item.get('task_id')}: {selected.get('name', '未选择模型')}。"
                f"{selected.get('why_suitable') or selected.get('method', '')}{score_text}"
            )
        return "\n".join(lines) or "- 暂无模型选择结果。"

    def _bullet_lines(self, items: list[Any]) -> str:
        return "\n".join(f"- {item}" for item in items) if items else "- 根据题目和数据情况补充。"
