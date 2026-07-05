# ReportQualityChecker 评审与 Rubric 建议

## 审查范围

本次审查聚焦 `PaperWriterAgent` 与最终报告链路：

- `src/agents/paper_writer.py`：固定生成 `solution_report.md`，覆盖摘要、问题重述、建模方案比较、模型假设、符号说明、数据分析、各小问求解、结果分析、灵敏度分析、反思、评价、参考文献、附录代码等章节。
- `src/core/workflow.py`：先生成初稿，再运行 `ReflectionAgent`，必要时运行 `RevisionAgent`，随后再次调用 `PaperWriterAgent` 生成最终报告，最后由 `ReportExporter` 导出。
- `src/agents/reflection_agent.py`：已有轻量质量信号，但只返回若干分数、`detected_problems`、`suggested_fixes` 和 `need_revision`，缺少最终报告级别的结构化缺陷清单。
- `src/tools/report_exporter.py`：只负责 Markdown 到 docx/pdf 的格式导出，不判断报告质量。
- `src/evaluation/metrics.py`：benchmark 使用粗粒度完整性、覆盖率、执行成功等指标，但不是最终报告质量 gate。

结论：当前系统能生成结构完整的论文草稿，但“章节存在”不等于“高质量论文”。建议新增轻量、非 LLM、非 Agent Team 的 `ReportQualityChecker`，在最终 `PaperWriterAgent` 之后、`ReportExporter` 之前运行，输出结构化 JSON 和可读 Markdown 摘要。

## 不建议做的事

- 不新增运行时 Agent Team。
- 不新增 `src/team` 或 `src/team_agents`。
- 不把质量检查做成另一个会改写正文的 agent。
- 不把质量摘要直接塞进 `solution_report.md` 主体，避免污染参赛论文样式；应独立输出 `report_quality_summary.md`。

## 建议落点

后续实现可放在工具层，例如 `src/tools/report_quality_checker.py`，作为确定性检查器被 workflow 调用：

1. `PaperWriterAgent` 生成最终 `solution_report.md`。
2. `ReportQualityChecker` 读取最终报告和已有 state artifacts。
3. 写出 `outputs/logs/report_quality_check.json`。
4. 写出 `outputs/reports/report_quality_summary.md`。
5. 再执行 `ReportExporter`，让导出链路可以携带质量警告。

## Rubric 评分维度

总分建议 100 分，维度保持轻量、可用正则和已有 state 判断：

| 维度 | 权重 | 检查重点 |
| --- | ---: | --- |
| 章节完整性 | 15 | `PaperWriterAgent.REQUIRED_SECTIONS` 是否全部出现；标题下是否有有效正文；是否只有占位句 |
| 题意与小问覆盖 | 15 | 每个 `parsed_problem.questions[].id` 是否在正文中有对应小节、模型、结果解释 |
| 建模严谨性 | 15 | 是否有变量、目标/指标、公式、约束或算法说明；公式是否来自 `FormulaAgent` 且能对应任务 |
| 数据与结果证据 | 15 | 是否引用数据画像、执行状态、`analysis_results.json`、`summary_table.csv`、主要发现和数值结果 |
| 验证与敏感性 | 10 | 是否包含误差分析、灵敏度、鲁棒性、局限性，且不是空泛模板 |
| 图表与表格 | 10 | 是否列出生成图、图注、用途；关键结果是否有表格或图支撑；路径是否存在 |
| 可复现性 | 10 | 是否说明代码路径、执行状态、修复记录、安全检查、依赖输出；执行失败是否明确披露 |
| 语言格式与导出就绪 | 10 | 中文表达、英文混杂、乱码风险、Markdown 表格、代码块、参考文献、docx/pdf 可导出性 |

评分建议：每个维度给 `score`、`max_score`、`status`、`evidence` 和 `penalties`，避免只给总分。

## 质量等级说明

建议输出四级质量等级：

| 等级 | 分数 | Gate | 说明 |
| --- | ---: | --- | --- |
| A / `high_quality` | 90-100 | pass | 结构完整、结果有证据、无 major flaw，可进入人工润色 |
| B / `usable_draft` | 75-89 | pass | 可用草稿，有少量 minor flaws 或 1 个非阻塞 major flaw |
| C / `needs_revision` | 60-74 | fail | 结构基本存在，但缺少关键推导、验证或结果证据 |
| D / `blocked` | 0-59 | fail | 执行失败、核心章节缺失、题意严重不匹配，不能作为最终报告 |

额外 gate 规则：

- 任一 blocker 直接降为 `blocked`。
- 存在 2 个及以上 major flaws 时，即使总分较高，也最多为 `needs_revision`。
- 报告章节完整但缺少数值结果、公式或小问覆盖时，不应评为 A。

## 缺失章节规则

`missing_sections` 不应只检查标题缺失，还要检查“有标题但内容无效”：

- `missing_heading`：必需章节标题不存在。
- `empty_section`：标题存在，但到下一个标题之间有效正文少于阈值，例如少于 80 个中文字符或只含空列表。
- `placeholder_only`：包含“根据题目和数据情况补充”“暂无”“人工复核时进一步细化”等占位语。
- `pattern_gap`：题型模板要求的关键内容缺失，例如优化题缺目标函数/约束，预测题缺误差指标，仿真题缺状态变量和实验设计。
- `question_gap`：某个 Q 编号没有独立模型、求解或结果解释。

建议必查章节：

`摘要`、`关键词`、`问题重述`、`问题分析`、`建模方案比较与选择`、`模型假设`、`符号说明`、`数据预处理与探索性分析`、`各小问模型建立与求解`、`结果分析`、`灵敏度分析`、`模型反思与改进说明`、`模型评价`、`参考文献`、`附录代码`。

## Major Flaws

建议把以下问题归为 major flaws：

- 代码执行失败，但报告没有显式说明失败和修复建议。
- 任一必需章节缺失或只有占位内容。
- 小问覆盖不足，例如 `Q1-Q5` 中有小问没有模型、求解或结果解释。
- 模型路线与题意明显不匹配，例如优化/动力学问题只写成泛化综合评价。
- 公式、变量、约束和目标函数不能对应实际任务。
- 结果分析没有任何数值结果、表格、图或执行产物证据。
- 灵敏度/鲁棒性/误差分析为空或只有泛化方法名。
- 图表路径不存在，或报告声称生成图表但 artifacts 中没有对应文件。
- `RevisionAgent` 的修订结果被最终 `PaperWriterAgent` 重写后没有保留可验证改动。

## Minor Flaws

建议把以下问题归为 minor flaws：

- 英文模型说明和中文正文混杂，影响论文风格一致性。
- 参考文献过于泛化，未对应实际模型或数据来源。
- 代码附录过长，影响导出可读性。
- Markdown 表格在 docx/pdf 中只是普通段落，导出效果有限。
- 章节顺序正确但图表未在正文中交叉引用。
- 摘要偏流程描述，缺少问题、方法、结果、结论四要素。
- “模型评价”只写系统优缺点，没有评价模型本身的适用性和局限性。

## `report_quality_check.json` 建议格式

建议 JSON 面向机器消费，保留可追踪证据：

```json
{
  "checker": "ReportQualityChecker",
  "version": "0.1",
  "report_path": "outputs/reports/solution_report.md",
  "summary_path": "outputs/reports/report_quality_summary.md",
  "overall_score": 78,
  "quality_level": "usable_draft",
  "gate_passed": true,
  "dimension_scores": [
    {
      "id": "section_completeness",
      "label": "章节完整性",
      "score": 13,
      "max_score": 15,
      "status": "warn",
      "evidence": ["15/15 required headings found"],
      "penalties": ["模型评价章节偏模板化"]
    }
  ],
  "missing_sections": [
    {
      "section": "目标函数与约束",
      "type": "pattern_gap",
      "severity": "major",
      "reason": "优化类问题未给出明确目标函数或约束条件",
      "suggested_fix": "在各小问模型建立中补充变量、目标函数、约束和求解算法"
    }
  ],
  "major_flaws": [
    {
      "id": "major_001",
      "category": "modeling_rigor",
      "section": "各小问模型建立与求解",
      "evidence": "报告列出公式，但未说明公式如何映射到 Q2 的决策变量",
      "impact": "读者无法复现建模逻辑",
      "suggested_fix": "按小问补充变量定义、目标函数、约束和参数含义"
    }
  ],
  "minor_flaws": [
    {
      "id": "minor_001",
      "category": "style",
      "section": "建模方案比较与选择",
      "evidence": "存在英文 paper_narrative",
      "suggested_fix": "将模型路线说明统一翻译为中文论文表达"
    }
  ],
  "suggested_fixes": [
    {
      "priority": "P1",
      "target": "结果分析",
      "action": "引用 analysis_results.json 中的关键数值并解释含义",
      "auto_fixable": false
    }
  ],
  "artifacts_checked": {
    "report_markdown": true,
    "execution_success": true,
    "formula_count": 4,
    "generated_figure_count": 3,
    "question_count": 5
  }
}
```

## `report_quality_summary.md` 建议格式

Markdown 摘要面向用户和 UI 展示，建议结构固定：

```markdown
# 报告质量检查摘要

## 总体结论

- 质量等级：B / usable_draft
- 总分：78/100
- Gate：pass
- 主要原因：章节完整，但结果证据和建模严谨性仍需增强。

## 维度评分

| 维度 | 得分 | 状态 | 主要扣分原因 |
| --- | ---: | --- | --- |
| 章节完整性 | 13/15 | warn | 模型评价偏模板化 |

## 缺失章节或弱章节

| 章节 | 类型 | 严重性 | 建议 |
| --- | --- | --- | --- |
| 目标函数与约束 | pattern_gap | major | 补充变量、目标函数和约束 |

## Major Flaws

1. `modeling_rigor`：公式未映射到小问决策变量。

## Minor Flaws

1. `style`：部分方案说明仍为英文。

## Suggested Fixes

1. P1：在结果分析中引用关键数值和图表。
2. P2：统一中文论文表达。

## 检查依据

- 报告：`outputs/reports/solution_report.md`
- 日志：`outputs/logs/report_quality_check.json`
```

## 与现有组件的关系

- `ReflectionAgent`：保留为初稿自检和是否触发一次修订的机制。
- `ReportQualityChecker`：只检查最终报告，不生成新模型、不调用 LLM、不改正文。
- `ReportExporter`：可读取质量结果，把导出警告追加到 `report_quality_check.json` 的 `minor_flaws` 或 `artifacts_checked.export_warnings`。
- benchmark metrics：可继续保留；后续可把 `overall_score`、`quality_level`、`major_flaw_count` 加入 benchmark summary。

## 最小实现建议

第一版只做确定性检查即可：

- Markdown heading parser：提取 `#`、`##`、`###` 标题及章节正文长度。
- Required section checker：对照 `PaperWriterAgent.REQUIRED_SECTIONS`。
- Placeholder checker：匹配占位短语和空列表。
- Question coverage checker：对照 `parsed_problem.questions`。
- Formula/result checker：统计 `$...$`、`$$...$$`、`analysis_results.json`、`summary_table.csv`、图表路径和 `result_analysis.findings`。
- Artifact checker：验证报告中引用的本地路径是否存在。
- Gate calculator：按维度扣分、生成等级、输出 major/minor/suggested fixes。

这能补上当前最大缺口：报告已经生成后，系统仍能明确告诉用户“为什么这份论文只能算草稿、缺什么、先修哪里”，且不引入新的 agent 运行架构。
