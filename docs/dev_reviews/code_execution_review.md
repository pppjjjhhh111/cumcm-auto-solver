# 代码执行与实验可靠性审查报告

审查角色：开发子 Agent C，代码执行与实验可靠性方向。

审查对象：`CodeGeneratorAgent`、`PythonExecutor`、`CodeRepairAgent`、`CodeSafetyChecker`、`DataProfiler`、`FigurePlannerAgent`，以及它们在 `WorkflowRunner._execute_with_repair_loop` 中的串联方式。

约束确认：本报告只建议在现有组件内做低风险增强；不建议新增运行时 Agent Team，不涉及 `src/team` 或 `src/team_agents`。

## 总体结论

当前实现的可靠性基础是好的：生成代码使用确定性模板，执行前有静态安全检查，代码在 `outputs/code_workspace` 中运行，`execution_attempts.json` 保留每次执行记录，`DataProfiler` 对缺失数据路径有降级结果，`FigurePlannerAgent` 能稳定输出图表计划。

主要缺口集中在执行成功后的结果可信度判断：现在 `PythonExecutor` 基本以进程返回码作为成功标准，`ResultAnalyzerAgent` 之后才发现 `analysis_results.json` 缺失或内容不足，修复循环不会因为“进程成功但结果不可用”而继续修复。建议补一个轻量 `result_sanity_check.json`，把产物存在性、JSON 可读性、图表文件、空数据状态和安全检查摘要统一写入日志，并挂到每个 execution attempt 上。

## P1 建议

### 1. 新增 `result_sanity_check.json`，不要只依赖 returncode

证据：

- `PythonExecutor.execute` 在 `src/tools/python_executor.py:50` 执行代码，并在 `src/tools/python_executor.py:95-101` 用 `returncode == 0`、`generated_files`、`all_output_files` 形成结果。
- `WorkflowRunner._execute_with_repair_loop` 在 `src/core/workflow.py:247` 把首次执行结果直接作为 `state.execution_result`，后续修复循环只看 `success`。
- `ResultAnalyzerAgent` 后续才检查 `analysis_results.json` 是否存在；这时已经错过修复循环和 post-execution figure planning。
- 代码库中没有发现 `result_sanity_check.json` 或等价实现。

风险：

- 代码进程成功退出，但没有写 `analysis_results.json`，工作流仍可能停止修复。
- `analysis_results.json` 存在但字段缺失、JSON 非法、包含 NaN/Infinity、`figures` 指向不存在文件时，后续论文和验证阶段才暴露问题。
- 空数据时可以生成 0 行结果和空 SVG，但仍被当成成功实验。

低风险改法：

- 在每次 `executor.execute(...)` 后立即做一个同步 sanity check，不新增 Agent，只放在 `WorkflowRunner` 或 `PythonExecutor` 的私有函数中。
- 写入 `outputs/logs/result_sanity_check.json`，并可选写入 `result_sanity_check_attempt_{n}.json`。
- 将结果挂到 `execution_result["result_sanity"]`，并增加 `execution_result["usable_for_analysis"]`。
- 保持 `success` 表示进程成功，新增 `usable_for_analysis` 表示产物可用；修复循环可用 `if not success or not usable_for_analysis` 触发。

建议检查项：

- `analysis_results.json` 是否存在、能否解析为 JSON。
- 必需字段是否存在：`row_count`、`numeric_columns`、`summary`、`figures`、`notes`。
- `row_count` 是否为非负整数；无数据时应给出 warning，而不是静默 ok。
- `summary` 中数值是否为 finite number，避免 NaN/Infinity 进入报告。
- `figures` 中每个路径是否在 `figures_dir` 下、文件是否存在、大小是否大于最小阈值、SVG 是否包含有效 `<svg` 和可见内容。
- `summary_table.csv` 是否存在并非空。
- `generated_files` 是否只包含 output tree 内产物。

建议 JSON 结构：

```json
{
  "status": "ok | warning | failed",
  "attempt": 0,
  "blocking_errors": [],
  "warnings": [],
  "checks": {
    "analysis_results_exists": true,
    "analysis_results_json_valid": true,
    "required_fields_present": true,
    "figures_exist": true,
    "figures_nonempty": true,
    "numbers_are_finite": true
  },
  "artifact_counts": {
    "figures": 2,
    "tables": 1
  }
}
```

### 2. 丰富 `execution_attempts.json`，记录修复循环停止原因和产物质量

证据：

- `execution_attempts.json` 在 `src/core/workflow.py:281` 写出，目前是 attempt 字典数组。
- 每次执行的 `safety` 会内联在 attempt 中，但 `code_safety.json` 在 `src/tools/python_executor.py:144` 只保留最近一次安全检查。
- `CodeRepairAgent.run` 接收 `previous_repair_attempts`，但目前主要只把数量传给 LLM trace，没有用于避免重复修复。

风险：

- 多次修复后，单独看 `code_safety.json` 会丢失前几次安全拦截细节。
- 当 repair agent 返回 `changed == False` 时，停止原因只写在最终 execution result 上，不容易形成完整审计链。
- 如果两次修复生成相同代码，当前循环只靠执行失败和最大次数退出，缺少代码 hash 去提前识别重复。

低风险改法：

- 保持 `execution_attempts.json` 仍是数组，避免破坏现有测试和消费方。
- 给每个 attempt 增加稳定字段：`started_at`、`ended_at`、`duration_seconds`、`code_sha256`、`stdout_tail`、`stderr_tail`、`generated_file_count`、`safety_status`、`result_sanity_status`。
- 当 repair 没有产生可执行代码时，在最终 attempt 上追加 `repair_stopped_reason` 和 `repair_decision`，或增加一个 companion `execution_attempts_summary.json`。
- 同时保留 `code_safety.json` 作为 latest view，但增加 `code_safety_attempt_{n}.json`，或至少把 `attempt` 和 `code_sha256` 写入 `code_safety.json`。
- 在修复循环中维护 `seen_code_hashes`，遇到重复修复代码时停止，并把停止原因写入 attempts。

### 3. 修正 `CodeSafetyChecker` 对 SyntaxError 的安全语义

证据：

- `CodeSafetyChecker.check_code` 先做逐行 substring 扫描，再 `ast.parse`。
- 如果 `ast.parse` 抛 `SyntaxError`，`src/tools/code_safety_checker.py:54` 会直接返回 `is_safe: True`、空 `blocked_reasons`、空 `risky_lines`。

风险：

- 语法错误代码中的危险 substring 扫描结果会被丢弃。
- `code_safety.json` 可能显示安全通过，但真实情况只是 AST 未能检查。
- 修复语法错误后，原先隐藏的危险调用可能进入下一轮。

低风险改法：

- SyntaxError 分支不要清空已发现的 `blocked_reasons` 和 `risky_lines`。
- 返回 `parse_error` 字段，建议：
  - 如果已有 line-level 风险，`is_safe = False`。
  - 如果没有 line-level 风险，`is_safe = True` 也可以，但 `suggested_fix` 应明确为 `Syntax error prevented AST-level safety checks`。
- 在 `code_safety.json` 中记录 `ast_checked: false`，便于后续判断安全检查覆盖范围。

## P2 建议

### 4. 缺失数据和不可读数据应有更明确的降级状态

证据：

- `DataProfiler._empty_profile` 在 `src/tools/data_profiler.py:74` 已能优雅处理无数据路径、路径不存在、无 csv/xlsx 文件。
- `DataProfiler._read_csv` 在 `src/tools/data_profiler.py:115` 固定使用 `utf-8-sig`。
- `CodeRepairAgent` 对 `FileNotFoundError` 只记录“提供了 available data files”，但 `src/agents/code_repair_agent.py:52-55` 不做确定性路径修复。
- `CodeGeneratorAgent` 的生成代码只发现 CSV；`DataProfiler` 支持 XLSX，但生成代码没有 XLSX 分支。

风险：

- XLSX 数据可以被 profiler 识别，但执行代码可能加载 0 个 CSV，最后生成 0 行分析结果。
- CSV 编码异常会让 profiler 记录 file error；如果所有文件都是 error entry，当前状态仍可能接近 `ok`，不够醒目。
- 无数据时生成的报告可能看起来像成功实验，而不是“文本建模 / 数据不足”的降级路径。

低风险改法：

- 在 `DataProfiler` 中增加 `read_error_count` 和 `status: partial | error | skipped | ok`。
- CSV 读取增加编码 fallback：`utf-8-sig`、`gb18030`、`utf-8 errors=replace`，并把实际编码写入 profile。
- `CodeGeneratorAgent` 生成的 `analysis_results.json` 增加 `status: ok | no_data | unsupported_data_format | partial` 和 `warnings`。
- 当 `data_profile.summary.recommended_figures` 为空、`row_count == 0` 或只有 XLSX 时，生成代码应写明确 warning，并让 `result_sanity_check.json` 返回 `warning`。
- `CodeRepairAgent` 对 `FileNotFoundError` 可以先做低风险建议：把可用数据文件 manifest 写进 repair trace；只有当缺失路径 literal 与单个 available data file 明确匹配时才自动替换。

### 5. 图表保存和 post-execution figure planning 需要连起来

证据：

- `FigurePlannerAgent` 在 `src/agents/figure_planner_agent.py:132` 从 `execution_results.get("figures", [])` 读取既有图表。
- `PythonExecutor.execute` 返回 `generated_files` 和 `all_output_files`，但没有 `figures` 字段。
- `CodeGeneratorAgent` 生成的脚本会把 figure paths 写进 `analysis_results.json`，但 post-execution planner 在 `ResultAnalyzerAgent` 读取结果之前运行。
- `DataProfiler._write_histogram_svg` 和 generated code 的空图逻辑会写 `<svg ...></svg>` 这类空 SVG。

风险：

- post-execution figure planner 几乎总是看不到已生成图表，`existing_figures` 为空。
- 空数据或空数值列时会留下空白 SVG，文件存在但不可用于论文。
- 图表路径存在于 `analysis_results.json`，但没有统一验证路径、大小和内容。

低风险改法：

- 在 post-execution planner 前，从 `analysis_results.json` 读取 `figures`，或从 `generated_files` 过滤 `figures_dir` 下的 `.svg/.png/.jpg` 文件，填充 `execution_result["figures"]`。
- 所有图表写入函数在无数据时写带标题和说明的 placeholder，而不是空 SVG。
- 图表写入采用临时文件再替换，避免中途异常留下半文件。
- `result_sanity_check.json` 校验图表路径必须在 `figures_dir` 下，且文件大小和 SVG 内容满足最小可用标准。
- 对 planned placeholder 增加 `placeholder: true` 元数据，避免后续把“计划图”误当成真实分析图。

### 6. `PythonExecutor._list_outputs` 建议更窄、更容错

证据：

- `_list_outputs` 在 `src/tools/python_executor.py:134` 对 `code_dir.parent` 做递归 `rglob("*")`。
- 默认输出根通常是 `outputs`；如果其中已有历史测试目录、临时目录或权限受限目录，递归扫描会变慢或抛权限异常。

风险：

- 执行前后的文件差异可能包含历史输出噪声。
- 权限异常可能让执行器在真正运行代码前失败。

低风险改法：

- 只扫描本次运行的受控目录：`code_dir`、`workspace_dir`、`figures_dir`、`logs_dir`、必要时 `reports_dir`。
- 捕获 `PermissionError`，写入 `output_scan_warnings`，不要中断代码执行。
- 在 `generated_files` 中附带 `size_bytes`、`mtime` 和分类：`code | figure | table | log | result_json`。

## 建议测试

- `test_result_sanity_check_marks_missing_analysis_results_failed`：代码 returncode 为 0 但不写 `analysis_results.json`，应写 `result_sanity_check.json` 且 `usable_for_analysis` 为 false。
- `test_result_sanity_check_validates_figures`：`analysis_results.json` 指向不存在或空 SVG，sanity 应 warning/failed。
- `test_execution_attempts_include_safety_and_sanity_status`：每个 attempt 都有 `safety_status` 和 `result_sanity_status`。
- `test_code_safety_checker_preserves_line_risks_on_syntax_error`：含 `os.remove(` 且语法错误的代码不能返回完全安全。
- `test_data_profiler_reports_partial_when_all_files_error`：不可读 CSV 不应静默等同 ok。
- `test_post_execution_figure_planner_receives_existing_figures`：执行结果已有 figure 文件时，`FigurePlannerAgent` 的 `existing_figures` 非空。

## 推荐落地顺序

1. 先加 `result_sanity_check.json` 和 `execution_result["usable_for_analysis"]`，这是提升稳定性的最小闭环。
2. 再丰富 `execution_attempts.json` 和 per-attempt `code_safety` 记录，增强可调试性。
3. 修正 `CodeSafetyChecker` SyntaxError 分支，避免安全日志误报“安全”。
4. 最后补数据缺失、XLSX/编码降级、图表 placeholder 和 existing figures 串联。

这些改动都可以在现有类和 workflow 内完成，不需要新增运行时 Agent 或新建 team 目录。
