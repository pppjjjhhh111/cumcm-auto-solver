# UI Review: Streamlit 产品体验审查

审查对象：`app.py`

角色：开发子 Agent F，UI 与产品体验 Agent

## 范围与约束核对

- DeepSeek 固定：当前 `make_llm_client()` 只返回 `DeepSeekLLMClient()`，Sidebar 也只展示 `LLM Provider：DeepSeek`，符合固定 DeepSeek 的方向。
- 无 LLM provider 下拉：未发现 provider `selectbox` 或多 provider 入口，符合要求。
- 无示例题入口：Sidebar 仅提供文件上传，未发现示例题按钮或示例题选择入口，符合要求。
- 无 Agent Team Mode/Tab：主导航为 10 个业务 Tab，未发现 Agent Team Mode 文案或 Tab，符合要求。
- 当前主要缺口：质量评分、ConsistencyChecker、一致性状态和报告质量 summary 没有在 Dashboard 中成为首屏核心信息；`ConsistencyChecker` 在 `app.py` 和 `src` 中未发现明确 UI 接入点。

## Dashboard 建议

当前 `render_dashboard()` 以启动面板、工作流完成度、时间线、产物数量为主，适合工程状态监控，但还不像面向用户交付的质量 Dashboard。建议把首屏改成“任务状态 + 质量结论 + 产物可用性”的组合：

- 在工作流进度下新增 `Quality Snapshot` 区域，4 张卡片并排展示：`Overall Quality`、`Report Quality`、`Consistency`、`Need Revision`。
- `Overall Quality` 和 `Report Quality` 从 `reflection_report` 读取；若未生成，显示 `未评估`，不要显示 0 分，避免用户误以为真实低分。
- `Consistency` 从未来的 `state["consistency_report"]` 或 `outputs/logs/consistency_check.json` 读取；未运行时明确显示 `未运行`，而不是隐藏。
- Dashboard 的“报告状态”不要只显示已生成/未生成，建议显示三态：`未生成`、`已生成但未质检`、`已质检可审阅`。
- 现有 6 个 metric 卡片偏数量导向，建议保留但降级为第二行，把质量状态前置。

建议展示顺序：

1. 启动/输入状态
2. 工作流完成度
3. 质量总览：Overall、Report、Consistency、Revision
4. 产物概览：报告、图表、代码、日志
5. 详细时间线

## 质量评分区域建议

当前评分分布在候选模型卡、方案比较、反思与修订页，缺少统一的评分语义。`normalize_score()` 会根据数值大小猜测 5 分制、10 分制或 100 分制，这对产品化展示不够稳。

建议：

- 为不同评分源显式定义量纲，例如 `reflection_report` 使用 100 分制，`solution_competition.score` 使用 5 分制，模型选择分项如果是累加分则不要混成百分比。
- `score_bar()` 接收 `max_score` 或 `scale` 参数，避免自动猜测导致 5 分、10 分、100 分视觉上都被拉满。
- 评分区增加文字等级：`优秀`、`可用`、`需复核`、`风险高`。用户不应只看数字判断是否可交付。
- `render_candidate_card()` 当前只展示 `data_fit_score`、`implementation_score`、`interpretability_score`、`stability_score`、`reportability_score`，但 `model_selector.py` 还产生 `formula_quality_score` 和 `sensitivity_potential_score`。建议补齐这些维度，或在 UI 中明确只展示核心 5 项。
- 反思评分建议采用一个专门的 `render_quality_panel(reflection, consistency)`，Dashboard 和“反思与修订”页复用同一组件，避免首屏与详情页口径不一致。

## ConsistencyChecker 建议

当前未看到 `ConsistencyChecker` 在 `app.py` 或 `src` 中的命名引用；`outputs/logs` 里的 “consistency check” 主要是建模方法文本，不是产品级一致性检查结果。

建议为 ConsistencyChecker 建立稳定 UI 数据契约：

```json
{
  "status": "pass | warn | fail | not_run",
  "score": 0,
  "issue_count": 0,
  "contradictions": [],
  "missing_evidence": [],
  "report_alignment": [],
  "checked_at": "ISO timestamp"
}
```

UI 呈现建议：

- Dashboard：只显示状态、分数、问题数量、最高风险一句话。
- 反思与修订 Tab：展示完整 issue 列表，按 `contradiction`、`missing_evidence`、`report_alignment` 分组。
- 论文报告 Tab：在目录左侧增加 `Consistency` 小卡，告诉用户当前报告是否通过一致性检查。
- Expert Mode：展示原始 ConsistencyChecker JSON；普通模式只展示可行动摘要。

## 报告质量 Summary 建议

当前 `render_report_tab()` 主要负责 Markdown 预览、目录和下载；报告质量只在 `render_reflection_tab()` 中作为一个分数出现。建议在报告页加入“报告质量 summary”，让用户在阅读正文前先判断能否交付。

建议内容：

- `Report Quality Score`：来自 `reflection_report.report_quality_score`。
- `Coverage`：报告是否覆盖问题、小问、模型、结果、图表、敏感性分析、改进建议。
- `Top Issues`：来自 `detected_problems` 的前 3 条。
- `Suggested Fixes`：来自 `suggested_fixes` 的前 3 条。
- `Consistency Status`：来自 ConsistencyChecker。
- `Reader State`：完整报告 / 截断预览 / 空报告 / 文件不可读。

当 Markdown 为空字符串时，不应渲染空白阅读器；应显示“报告文件存在但内容为空或不可读”的空态，并保留下载入口供排查。

## 空状态建议

当前 `empty_state()` 统一使用 `Awaiting Agent Run`，视觉一致，但语义过于单一。建议根据上下文提供更精确的空态：

- 未上传题面：提示上传赛题文件，不提供示例题入口。
- 未配置 DeepSeek Key：提示只能浏览已有产物，不能启动新任务。
- 工作流未运行：提示启动自动建模。
- Reflection 未启用：显示“Reflection Loop 未启用，本次不会生成质量评分”，而不是“等待反思结果”。
- ConsistencyChecker 未运行：显示“尚未进行一致性检查”，并说明它不等同于失败。
- 报告未生成：保留当前文案，但建议同时显示当前已完成到哪个工作流步骤。
- 日志/图表/代码为空：区分“尚未运行”和“本次运行没有生成该类产物”。

空态里的行动按钮应保持克制：只引导上传、启动、开启 Reflection 或查看日志，不增加示例题入口。

## Expert Mode 建议

当前 Expert Mode 控制原始 JSON、代码预览、路径细节和报告默认完整展开，方向合理。产品化建议：

- 将 Sidebar 文案从 `Expert Mode` 改为更明确的 `Expert Mode / 原始诊断`，避免普通用户误开。
- 普通模式只展示业务摘要；文件系统路径、完整 JSON、stdout/stderr、源代码、长日志继续留在 Expert Mode。
- 大 JSON 建议默认折叠，并限制首屏渲染体积；特别是日志和报告较大时，避免 `st.json()` 或完整 Markdown 影响页面响应。
- Expert Mode 不应改变质量结论本身，只改变证据展开深度。当前“展开完整报告”的默认值跟随 Expert Mode 可以保留，但建议在 UI 上说明这是阅读范围，不是质量判断。

## outputs 为空时稳健性建议

当前 `get_runtime_state()` 只读取 `st.session_state["last_state"]`，而 `is_current_session_file()` 又依赖 `RUN_STARTED_KEY`。这会带来一个产品体验问题：Hero 文案说未配置 Key 时仍可浏览历史产物，但重新进入页面或 outputs 中已有报告时，UI 不会自动识别为当前可浏览产物。

建议：

- 明确产品策略：如果只展示当前会话产物，就把 Hero 文案改为“可浏览当前会话产物”；如果要浏览历史产物，则增加安全的历史产物发现逻辑。
- 当 `outputs` 目录不存在、为空、或缺少 `reports/logs/code/figures` 子目录时，所有列表函数都应返回空列表，并展示对应空态。
- `list_files()` 当前直接 `root.rglob("*")`，遇到无权限子目录可能抛异常；建议改成容错遍历，跳过不可读目录并在 Expert Mode 下提示。
- `render_download_button()` 已通过 `is_current_session_file()` 保护下载按钮，但当没有 `RUN_STARTED_KEY` 时会隐藏所有已有产物。若支持历史浏览，应提供 `current_only` 与 `history` 两种模式。
- 报告页应区分：`state` 为空、报告文件不存在、报告文件存在但非当前会话、报告文件存在但内容为空。
- ConsistencyChecker 与 reflection 的 fallback 日志读取应允许“有 state 但某字段缺失”的局部成功，不要因为一个质量文件缺失而让整个质量区域消失。

## 优先级建议

- P0：Dashboard 增加质量总览，把 `report_quality_score`、`need_revision`、ConsistencyChecker 状态前置。
- P0：为空/未运行/未配置 Key/未生成报告建立更准确的空态文案。
- P1：定义 ConsistencyChecker 输出 JSON 契约，并在 Dashboard、反思页、报告页三处接入。
- P1：重构评分组件，取消自动猜测量纲，显式传入评分 scale。
- P1：报告页加入质量 summary，不再只做 Markdown 阅读器。
- P2：Expert Mode 增加大 JSON/长日志渲染保护。
- P2：历史 outputs 浏览策略产品化，解决 Hero 文案与 `get_runtime_state()` 行为不一致的问题。
