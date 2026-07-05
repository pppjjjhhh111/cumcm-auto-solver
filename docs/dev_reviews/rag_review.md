# RAG 与知识库审查报告

审查日期：2026-07-05  
审查角色：开发子 Agent E（RAG 与知识库）

## 审查范围

- `knowledge_base/` 与 `knowledge_base/index.json`
- `src/rag/chunker.py`、`src/rag/ingest.py`、`src/rag/vector_store.py`、`src/rag/retriever.py`
- `main.py` 中的 `--build-kb`、`--use-rag`、`--kb-dir`
- `src/core/workflow.py` 中 RAG 检索与状态传递
- `StrategyGeneratorAgent`、`FormulaAgent`、`FigurePlannerAgent`、`PaperWriterAgent` 的 RAG 使用情况
- `outputs/logs/rag_retrievals.json` 当前结构与可审计性

本报告只给出审查和改进建议。后续实现不应新增运行时 `Agent Team`，也不应新增或修改 `src/team`、`src/team_agents`。

## 总体结论

当前 RAG 是一个可选的本地关键词检索通道，但它更像“可记录的附件”，还没有稳定地变成建模方法启发。`--build-kb` 可以生成 JSON 索引，`--use-rag` 会在 workflow 中检索并把结果传给 `StrategyGeneratorAgent`，但缺失知识库、空知识库、无命中、索引陈旧等状态没有清晰 warning；下游 `FormulaAgent`、`FigurePlannerAgent`、`PaperWriterAgent` 也没有直接接收 RAG 上下文。

优先改进方向是：让本地知识库缺失时优雅降级并留下显式状态；把检索结果转成短小的“方法启发/写作约束/来源元数据”，而不是把原文 preview 原样传递；让日志稳定产出并可解释；通过现有 workflow 和现有 Agent 参数扩展完成，不引入新的运行时团队编排。

## 关键发现

### P1：缺失或空知识库会静默降级，用户看不到 warning

证据：

- `src/rag/ingest.py:12-16` 中 `ingest_documents()` 在目录不存在时直接返回空列表。
- `src/rag/vector_store.py:33-38` 中 `retrieve()` 如果没有索引会调用 `build_index()`，空目录或不存在目录都会得到空文档集。
- `src/rag/retriever.py:14-17` 中 `Retriever.__init__()` 在索引不存在时直接构建索引，没有 warning 或状态记录。
- `main.py:48-56` 中 `--build-kb` 无论是否索引到 0 个 chunk，都会打印 `Knowledge base indexed: ...`。
- `src/core/workflow.py:93-95` 只有在 `state.rag_retrievals` 非空时才写编号日志；无命中或缺失知识库时没有 workflow 级状态。

影响：

- 用户启用 `--use-rag` 后可能以为知识库已生效，实际可能是目录不存在、索引为空或完全无命中。
- `--build-kb missing_dir` 这类显式构建命令会给出“成功但 0 chunks”的弱信号，不足以暴露配置错误。
- UI 中只显示 RAG ON/OFF，无法区分“启用了但无知识库”“启用了但无命中”“启用了且已使用”。

建议：

- 为检索增加稳定状态对象，例如 `enabled`、`kb_dir`、`index_exists`、`document_count`、`status`、`warnings`、`results`。
- `--use-rag` 遇到知识库不存在或空索引时继续运行，但必须在 `rag_retrievals.json` 和 workflow 编号日志中写 warning。
- `--build-kb` 是显式构建命令，目录不存在应返回非 0 或至少打印 `WARNING` 到 stderr；目录存在但无支持文件也应明确提示。
- 不要在普通 `--use-rag` 降级路径中抛异常中断主流程，除非索引 JSON 损坏且没有回退构建策略。

### P1：RAG 检索结果没有真正影响方法选择

证据：

- `src/core/workflow.py:93-101` 只把 `state.rag_retrievals` 传给 `StrategyGeneratorAgent`。
- `src/agents/strategy_generator.py:21-24` 接收 `retrieved_references`，但 `src/agents/strategy_generator.py:107` 只是把前 3 条引用挂到每个候选模型上。
- `ModelSelectorAgent` 的候选文本评分不读取 `retrieved_references`，因此 RAG 不会改变模型排序。
- `SolutionCompetitionAgent` 的 `_candidate_text()` 也不读取 `retrieved_references`，因此完整方案竞争不会利用知识库启发。
- `FormulaAgent.run()`、`FigurePlannerAgent.run()`、`PaperWriterAgent.run()` 的签名没有 RAG 参数；workflow 调用它们时也没有传递 RAG 上下文。

影响：

- 知识库目前主要被记录和透传，不能稳定引导“采用哪些方法、为何采用、公式怎么组织、图表怎么设计、论文怎么重写表达”。
- `knowledge_base/methods/baseline_methods.md` 里的方法启发无法转化为模型选择或论文结构中的可解释依据。

建议：

- 在 `src/rag` 内增加非 Agent 的轻量转换层，把原始 retrieval 转成 `method_hints`，字段可包括 `source_id`、`relative_path`、`score`、`hint_type`、`method_keywords`、`paraphrased_hint`、`do_not_copy`。
- `StrategyGeneratorAgent` 应使用 `method_hints` 调整候选生成或候选解释，例如给匹配 TOPSIS、entropy weight、regression、sensitivity 的模型增加可解释理由，而不是把同一批原文 preview 挂到每个候选。
- `FormulaAgent` 可接收 `method_hints` 或从 `selected_strategy` 中读取规范化后的 hints，用于选择公式模板和变量说明。
- `FigurePlannerAgent` 可接收 hints 中的验证/敏感性/对比图建议，用于补充图表目的，而不复制知识库文字。
- `PaperWriterAgent` 应只接收短提示和来源 metadata，不能接收长原文 preview；论文中应重写表达，并可在“参考依据/方法启发”处记录相对路径来源。

### P2：`rag_retrievals.json` 有产出，但状态不完整且 workflow 日志不稳定

证据：

- `src/rag/retriever.py:19-27` 会写 `outputs/logs/rag_retrievals.json`，包含 `query`、`top_k`、`results`。
- 当前样例 `outputs/logs/rag_retrievals.json` 存在，但 `results` 为空；它没有说明是无命中、空知识库、索引缺失、查询为空还是语言/分词不匹配。
- `src/core/workflow.py:94-95` 只有有结果才写 `00x_RAGRetriever.json`，导致无命中时缺少与其它 Agent 一致的编号审计记录。

影响：

- 无法可靠回答“RAG 是否启用、查了哪个知识库、知识库是否存在、索引是否加载、为什么没有命中”。
- 下游 benchmark 或 UI 只能看到 RAG ON/OFF，不能判断 RAG 是否真的参与。

建议：

- `rag_retrievals.json` 固定包含状态字段，而不是只写 query/results。
- 无论 enabled 后是否命中，都写 workflow 编号日志，例如 `RAGRetriever` payload 中包含 `status: ok|disabled|empty_query|missing_kb|empty_index|no_hits|error_fallback`。
- 对 `query` 做长度上限或同时保存 `query_hash`、`query_preview`，避免把完整题面长期写入日志。
- 保留 `relative_path`、`chunk_id`、`score`，但把 `text_preview` 控制为短摘要或提示，不作为论文生成输入。

### P2：存在原文复制风险，当前约束只写在知识库文本里

证据：

- `knowledge_base/index.json` 中 `methods/baseline_methods.md` 的文本包含“只作为方法启发、不要原文复制”的说明。
- `src/rag/vector_store.py:59` 把原文 `text` 前 500 字作为 `text_preview` 返回。
- `src/agents/strategy_generator.py:48` 和 `src/agents/strategy_generator.py:107` 将完整 retrieval 对象继续保存在策略输出和候选中。
- `PaperWriterAgent` 目前没有 RAG 参数，也没有显式的“不要复制知识库原文”检查或重写约束；`src/agents/paper_writer.py:196` 只是固定写了一句第一版 RAG 说明。

影响：

- 一旦后续把 retrieval 直接注入写作提示词或报告正文，很容易复制 `text_preview`。
- 当前知识库里的“不要复制”本身也可能被当作原文内容传递，约束不够工程化。

建议：

- 原始 `text_preview` 只留在审计日志，不传给论文写作 Agent。
- 给 PaperWriter 的 RAG 输入应是短的 `paraphrased_hint` 和 source metadata，并带 `must_rewrite: true`。
- 增加一个本地检查：生成报告与知识库 chunk 做 n-gram 或最长公共子串检测，超过阈值则 warning 或在 reflection 中标记。
- 知识库条目可以保留原文，但面向 Agent 的上下文应先被压缩成“方法名、适用场景、注意事项、来源路径”。

### P2：索引可用性与新鲜度缺少校验

证据：

- `knowledge_base/index.json` 保存了绝对 `kb_dir` 和绝对 `source_path`。
- `src/rag/vector_store.py:65-73` 直接保存/加载索引，没有 schema version、文件哈希、mtime、支持文件数量或构建时间。
- `src/rag/retriever.py:14-17` 只要 `index.json` 存在就加载，不验证知识库文件是否变更或路径是否迁移。

影响：

- 项目移动后检索仍能基于内嵌文本工作，但日志里的 `source_path` 可能指向旧路径。
- 修改知识库文件后，如果忘记 `--build-kb`，`--use-rag` 可能继续使用陈旧索引。

建议：

- `index.json` 增加 `schema_version`、`built_at`、`file_count`、`source_files`、`content_hash` 或 mtime 摘要。
- 加载索引时对比当前 `knowledge_base` 文件清单，发现陈旧时 warning 并可选择回退到即时构建。
- 日志和下游 Agent 优先使用 `relative_path`，绝对路径只用于本地调试。

### P3：关键词检索对中文题面和英文知识库的匹配较弱

证据：

- `src/rag/vector_store.py:82-85` 仅用 ASCII token 和连续中文片段做简单切词。
- 当前 `outputs/logs/rag_retrievals.json` 样例中，题面是中文共享单车预测类问题，知识库有 regression、correlation、sensitivity 等英文方法词，但 `results` 为空。

影响：

- CUMCM 题面通常是中文，而基础方法知识库可能中英混合；简单关键词检索会错过本应有启发价值的基线方法。

建议：

- 在检索前做轻量 query expansion，不必引入外部向量服务：例如 `预测 -> prediction/regression/forecast`、`评价 -> TOPSIS/entropy weight/AHP`、`敏感性 -> sensitivity`、`相关关系 -> correlation/regression`。
- 从 `parsed_problem.problem_type`、任务类型、数据画像字段中补充英文检索词。
- 将 `ModelZoo` 的模型 id/name 作为可控同义词来源，避免新增运行时 Agent。

### P3：缺少 RAG 专项测试

证据：

- `tests/` 中未检索到 `rag`、`knowledge_base`、`--build-kb`、`--use_rag`、`rag_retrievals` 相关测试。

建议补充测试：

- `--build-kb` 对不存在目录给出 warning 或非 0 返回；对空目录给出明确 warning。
- `--use-rag --kb-dir missing` 不中断 workflow，并写出带 `missing_kb` 状态的 `rag_retrievals.json`。
- 中文预测类 query 能通过扩展词命中 `baseline_methods.md`。
- `StrategyGeneratorAgent` 使用 `method_hints` 改变候选解释或评分 trace，而不是只保存 raw references。
- `PaperWriterAgent` 输出不得包含知识库 chunk 的长原文片段。

## 建议的改造路径

1. 先改 `src/rag` 的返回结构：把 retrieval 结果包装成稳定报告对象，保留 `results`，新增 `status` 与 `warnings`。
2. 改 `WorkflowRunner._retrieve_rag()`：无论有无结果都写 `state.rag_retrievals` 或 `state.rag_context`，并始终写 `RAGRetriever` 编号日志。
3. 改 `main.py build_kb()`：区分目录不存在、无支持文件、成功构建；显式命令可以失败，运行时 `--use-rag` 则 warning 后继续。
4. 在 `src/rag` 内增加普通 helper，把 raw results 转为 `method_hints`；不要新增 Agent，不要新增 `src/team` 或 `src/team_agents`。
5. 扩展现有四个 Agent 的参数或读取路径：
   - `StrategyGeneratorAgent`：用 hints 影响候选解释/轻量打分。
   - `FormulaAgent`：用 hints 选择公式模板和变量说明。
   - `FigurePlannerAgent`：用 hints 补充验证图、敏感性图、对比图建议。
   - `PaperWriterAgent`：只接收重写后的 hints 和 source metadata，禁止接收长原文。
6. 补测试和日志验收，确保 disabled、missing、empty、no_hits、ok 都有可观察产物。

## 建议的 `rag_retrievals.json` 目标形态

```json
{
  "enabled": true,
  "status": "no_hits",
  "kb_dir": "knowledge_base",
  "index_path": "knowledge_base/index.json",
  "index_exists": true,
  "document_count": 2,
  "query_hash": "sha256:...",
  "query_preview": "problem background and task keywords...",
  "top_k": 5,
  "warnings": [
    "No retrieval hits. Workflow continued without RAG method hints."
  ],
  "results": [],
  "method_hints": []
}
```

命中时，`method_hints` 建议使用短字段：

```json
{
  "source_id": "methods/baseline_methods.md::0",
  "relative_path": "methods/baseline_methods.md",
  "score": 3.2,
  "hint_type": "method_inspiration",
  "method_keywords": ["regression", "correlation", "sensitivity"],
  "paraphrased_hint": "Use interpretable baseline modeling and sensitivity checks as a robust first pass.",
  "must_rewrite": true
}
```

## 验收标准

- 启用 `--use-rag` 且知识库不存在时，主 workflow 不中断，终端或日志中出现明确 warning，`rag_retrievals.json` 包含 `status: "missing_kb"`。
- 启用 `--use-rag` 且无命中时，`rag_retrievals.json` 包含 `status: "no_hits"`，workflow 编号日志也有 `RAGRetriever` 记录。
- `--build-kb` 对不存在目录和空目录不再伪装成普通成功。
- RAG 命中后，策略、公式、图表、论文至少有一个可审计字段显示“采用了哪些方法启发”，且来源可追踪到 `relative_path`。
- 论文正文不包含知识库 chunk 的长原文片段；RAG 只作为方法启发和来源提示。
- 改造不新增运行时 Agent Team，不新增 `src/team` 或 `src/team_agents`。
