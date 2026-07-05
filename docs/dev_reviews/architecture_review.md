# 架构审查报告

审查范围：`main.py`、`app.py`、`WorkflowRunner`、`src/agents`、`src/tools`、`src/core`，以及 DeepSeek 固定逻辑、示例题入口、mock/auto provider 残留、日志结构和 UI 字段依赖。

## 当前架构摘要

当前项目是单一顺序流水线架构，核心运行时入口只有两类：

- `main.py`：CLI 入口。负责解析参数、构建 DeepSeek LLM 客户端、触发知识库索引、Benchmark 或 `WorkflowRunner`。
- `app.py`：Streamlit UI 入口。负责上传题面和数据文件、检查 `DEEPSEEK_API_KEY`、构建 DeepSeek LLM 客户端、调用 `WorkflowRunner`，并读取本次运行的状态、产物和日志。

`src/core` 是运行时核心：

- `src/core/workflow.py` 中的 `WorkflowRunner` 是唯一主编排器，按固定顺序调用文件加载、题目解析、任务拆解、数据画像、模型推荐、模型选择、方案竞争、公式、图表规划、代码生成、代码执行与修复、结果分析、验证、论文生成、反思修订和导出。
- `src/core/state.py` 定义 `SolverState`，是 UI、日志快照和下游 agent 之间的共享状态结构。
- `src/core/llm_client.py` 定义 provider-neutral 的 `BaseLLMClient`，并保留 `MockLLMClient`、`OpenAICompatibleLLMClient`、`DeepSeekLLMClient` 等适配器。

`src/agents` 是阶段性执行单元，不直接知道 UI：

- 每个 agent 返回结构化 `dict`，通常包含 `agent`、`llm_trace` 和阶段字段。
- `StrategyGeneratorAgent` 依赖 `src/tools/model_zoo.py`。
- `PaperWriterAgent` 依赖 `src/tools/paper_pattern_library.py`。
- `CodeRepairAgent` 是执行失败后的确定性修复模块，`src/agents/code_repair.py` 只是兼容性 re-export。

`src/tools` 是工具和副作用层：

- `FileLoader` 读取题面和数据。
- `DataProfiler` 生成数据画像和数据画像图。
- `PythonExecutor` 在 `outputs/code_workspace` 执行生成代码，并调用 `CodeSafetyChecker`。
- `ReportExporter` 负责 Markdown 到 Word/PDF 的可选导出。
- `ModelZoo` 和 `PaperPatternLibrary` 是配置/知识库式辅助组件。

未发现源码层面的运行时团队编排目录或主编排替代物。`src` 目录只有 `agents/core/evaluation/rag/tools/utils` 等现有模块；历史产物和 `__pycache__` 中出现过旧命名，但不是当前源码入口。

## 发现的问题

| 编号 | 风险等级 | 问题 | 影响 | 建议修改文件 |
| --- | --- | --- | --- | --- |
| A1 | 高 | DeepSeek 产品模式与底层 fallback 行为不完全一致。`main.py` 和 `app.py` 都要求 `DEEPSEEK_API_KEY`，但 `OpenAICompatibleLLMClient._generate_impl()` 在真实 API 调用失败时，默认 `strict=False` 会静默回退到 `MockLLMClient`。 | 用户以为使用 DeepSeek，实际可能得到 mock 结果；报告和日志里虽然有 `provider` 字段，但 UI 仍展示 DeepSeek 已连接。 | `main.py`、`app.py`、`src/core/llm_client.py`、`tests/test_product_mode.py`、`tests/test_llm_client.py` |
| A2 | 中 | CLI 仍保留隐藏的 `--llm`、`--llm-config` 参数；UI 仍保留 `provider` 配置、`effective_provider` session state 和 `hero(provider, ...)` 参数，但实际只支持 DeepSeek。 | 对维护者形成多 provider 入口仍存在的错觉，后续改动容易绕开固定 DeepSeek 产品约束。 | `main.py`、`app.py`、`tests/test_product_mode.py` |
| A3 | 中 | UI 和 agent 输出之间没有集中 schema 契约。`app.py` 直接依赖大量字符串字段和固定日志文件名。 | 任一 agent 字段改名或日志文件名调整，都可能导致 UI 空状态、展示错误或 fallback 读取不到数据。 | `app.py`、`src/core/state.py`，可新增很小的 `src/core/log_contract.py` 或等价常量模块 |
| A4 | 中 | 日志结构有两套写法：`WorkflowRunner._log()` 写带序号的阶段快照，部分 agent/tool 同时写固定文件名，例如 `model_recommendations.json`、`data_profile.json`、`solution_competition.json`、`figure_plan.json`。 | 两套日志可能语义重复；`figure_plan.json` 会被执行前后两次规划覆盖，只有带序号日志保留完整历史。UI 目前依赖固定文件名和本次运行时间过滤。 | `src/core/workflow.py`、`app.py`、相关 agent/tool 的日志写入点 |
| A5 | 中 | UI 当前绑定全局 `outputs` 子目录和文件 mtime 过滤。`last_state` 存在时优先用 state，fallback 日志要求当前会话 mtime。 | 多次运行同一 `outputs` 目录会累积旧日志；页面刷新后不会自动加载历史 state，这是当前设计，但维护者容易误以为日志就是完整当前态。 | `app.py`、`src/core/state.py`、`tests/test_ui_legacy_filter.py` |
| A6 | 低 | 没有活跃的示例题 UI/CLI 入口，但存在 `LEGACY_SAMPLE_MARKERS`、历史 `outputs`/`benchmark/results` 产物和测试 fixture。 | 审查搜索时容易把历史 sample/minimal 产物误判为运行时入口。 | 不建议作为核心逻辑修改；若清理，应单独做产物清理提交 |
| A7 | 低 | `WorkflowRunner` 默认 `llm_client or MockLLMClient()`，`BatchRunner` 也默认 mock。 | 对单元测试是有用契约；但生产代码如果绕过 `main.py/app.py` 直接实例化 runner，可能意外进入 mock。 | `src/core/workflow.py`、`src/evaluation/batch_runner.py`、测试文档 |

## DeepSeek 固定逻辑审查

当前产品入口已经基本固定 DeepSeek：

- `main.py.build_llm_client()` 在缺少 `DEEPSEEK_API_KEY` 时直接报错。
- `app.py.make_llm_client()` 在缺少 `DEEPSEEK_API_KEY` 时直接报错。
- README 明确说明正式 CLI 和 Streamlit UI 不提供 mock 运行入口。
- `tests/test_product_mode.py` 覆盖了 CLI 缺 key 报错和有 key 时返回 `DeepSeekLLMClient`。

主要缺口是 API 调用失败时的静默 mock fallback。若产品模式要求“正式入口永远不回退 mock”，最小修复应让 `main.py` 和 `app.py` 构造 `DeepSeekLLMClient(strict=True)`，或将 `DeepSeekLLMClient` 默认改为 strict，并只在测试中显式使用 `MockLLMClient`。

不建议删除 `MockLLMClient`。它仍被单元测试、workflow smoke test 和低层兼容性测试使用，且 AGENTS.md 明确要求保留 mock 仅用于测试和低层兼容。

## 示例题入口和 provider 残留

未发现当前 UI 或 CLI 有“运行示例题”的显式入口：

- `examples` 目录存在，但当前未看到活跃样例文件。
- `app.py` 只允许上传题面和数据文件。
- `main.py` 要求 `--problem`，除非运行 `--build-kb` 或 `--benchmark`。
- `tests/fixtures/minimal_problem` 是测试 fixture，不是产品入口。

存在的残留：

- `main.py` 隐藏接收 `--llm` 和 `--llm-config`，但没有实际分支。
- `app.py` 返回 `{"provider": "deepseek"}`，并维护 `effective_provider`，但没有可选 provider UI。
- `src/core/llm_client.py` 保留 `RealLLMClient` 和 `LocalHTTPLLMClient`，目前没有产品入口调用。
- 历史输出中出现过旧的团队相关日志名，这些是生成产物，不是当前源码结构。

建议清理入口层残留，但保留 core 层 LLM 抽象和 mock 测试能力。

## 日志结构和 UI 字段依赖

UI 强依赖以下 state/log 字段：

- `parsed_problem`: `background`、`data_description`、`questions`、`keywords`、`problem_type`
- `data_profile`: `file_count`、`table_count`、`files`、`warnings`、`summary.numeric_columns`、`summary.categorical_columns`、`summary.time_columns`、`summary.recommended_preprocessing_steps`
- `candidate_strategies`: `strategies[].task_id`、`task_type`、`task_description`、`candidates[]`
- `candidate`: `model_id`、`name`、`category`、`implementation_difficulty`、`why_suitable`、`expected_output`、`input_data_requirements`、`risks_and_limitations`、`scores.total_score`
- `selected_model`: `selected_strategies[]`、`selected_solution`、`overall_route`、`solution_competition`
- `solution_competition`: `candidate_solutions[]`、`selected_solution`、`score.total_score`、`risk_points`、`paper_narrative`
- `formulas`: `variables`、`latex_blocks`
- `figure_plan`: `figure_plan[].figure_id`、`title`、`caption`、`purpose_in_paper`
- `execution_attempts`: `attempt`、`success`、`stdout`、`stderr`、`repair`
- `execution_result`: `success`、`returncode`、`stdout`、`stderr`
- `reflection_report`: `completeness_score`、`question_alignment_score`、`data_usage_score`、`modeling_depth_score`、`report_quality_score`、`need_revision`、`detected_problems`、`suggested_fixes`
- `paper`: `report_path`

UI fallback 还依赖这些固定日志文件名：

- `data_profile.json`
- `model_recommendations.json`
- `solution_competition.json`
- `formulas.json`
- `figure_plan.json`
- `execution_attempts.json`
- `reflection_report.json`
- `solver_state.json`
- `llm_calls.jsonl`

建议把这些文件名和关键 state key 提成轻量常量/契约模块，并在测试里覆盖“agent 输出字段变动会影响 UI”的关键路径。

## 建议修改文件

优先修改：

- `main.py`：移除隐藏 provider 参数；产品入口强制 DeepSeek strict；保留 `--deepseek-model`、`--deepseek-base-url`、`--use-rag`、导出和 benchmark 参数。
- `app.py`：构造 strict DeepSeek 客户端；移除无实际选择能力的 provider session state；保留固定 DeepSeek 文案、上传入口、legacy sample artifact filter 和 current-session artifact filter。
- `src/core/llm_client.py`：保留 `MockLLMClient`，但明确 fallback 只能由测试或显式低层调用启用；避免产品入口静默 fallback。
- `src/core/state.py` 或新增轻量契约模块：集中定义 UI 依赖的 state key 和固定日志文件名。
- `tests/test_product_mode.py`：补充 API 失败不应 fallback mock 的产品模式断言。
- `tests/test_ui_legacy_filter.py`：保留 legacy sample artifact 过滤测试，并补充固定日志 fallback 契约测试。
- `tests/test_workflow_smoke.py`：继续覆盖固定日志文件和 `SolverState` 关键字段。

可选、单独处理：

- 历史 `outputs`、`benchmark/results`、`__pycache__` 中的旧产物和缓存命名。此类清理不应混入架构逻辑改动。

## 不建议修改的部分

- 不建议替换 `WorkflowRunner` 的单一顺序编排模型；这是当前 CLI、UI、测试和日志结构共同依赖的主干。
- 不建议新增团队化运行时编排、团队目录、团队代理目录、团队编排器或团队 Tab。本报告的最小方案不包含任何此类改动。
- 不建议把 `src/agents` 合并成一个大类。当前按阶段拆分便于测试和定位日志。
- 不建议让 `src/tools` 反向依赖 UI 或 `WorkflowRunner`。工具层应继续保持可复用服务模块。
- 不建议删除 `MockLLMClient`。它应保留给测试和低层兼容，但不暴露为正式 UI/CLI 入口。
- 不建议删除 `LEGACY_SAMPLE_MARKERS` 和相关 UI 过滤测试，除非先清理历史产物并确认 UI 不再可能读取旧 sample 日志。
- 不建议在同一次修改中重构报告生成、模型推荐和 UI 视觉层。当前风险集中在 provider strictness 和日志/UI 契约，不需要扩大改动面。

## 最小修改方案

1. 锁定产品模式 DeepSeek strict 行为。
   - `main.py` 和 `app.py` 构造 `DeepSeekLLMClient(strict=True)`。
   - 测试覆盖缺 key 报错、有 key 使用 DeepSeek、API 失败不回退 mock。

2. 清理入口层 provider 残留。
   - 删除 `main.py` 中隐藏但未使用的 `--llm`、`--llm-config`。
   - 删除 `app.py` 中无实际分支的 `effective_provider` 状态；保留固定 DeepSeek 显示。

3. 固化日志/UI 契约。
   - 增加轻量常量或文档化字段集合，至少覆盖固定日志文件名和 UI 读取的主 state key。
   - `app.py` 的 fallback 读取使用这些常量，避免硬编码散落。

4. 保持 legacy sample 防护。
   - 不恢复示例题按钮或示例题 CLI 快捷入口。
   - 继续通过 `is_current_session_file()` 和 `is_legacy_sample_artifact()` 避免 UI 误读旧产物。

5. 分离产物清理。
   - 如果要删除历史输出中的旧命名或缓存，放到独立清理提交，不和运行时逻辑改动混在一起。

6. 验证范围。
   - 运行 `python -m pytest tests/test_product_mode.py tests/test_ui_legacy_filter.py tests/test_workflow_smoke.py tests/test_llm_client.py`。
   - 若修改日志契约，再运行全量 `python -m pytest`。
