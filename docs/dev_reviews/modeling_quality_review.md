# 建模质量审查报告

审查对象：`ProblemParserAgent`、`TaskDecomposerAgent`、`StrategyGeneratorAgent`、`ModelSelectorAgent`、`FormulaAgent`、`ValidationAgent`、`PaperWriterAgent`、`ModelZoo`、`Paper Pattern Library`、`FigurePlannerAgent`。

约束：不重写全部 Agent；不新增运行时 Agent Team；不新增 `src/team` 或 `src/team_agents`。建议均限定为现有链路内的字段补强、评分细化、trace 透传和论文呈现增强。

## 总体判断

当前系统已经有一条可用的建模链路：题面解析 -> 小问拆解 -> Model Zoo 推荐 -> 模型评分选择 -> 多方案竞争 -> 公式生成 -> 图表规划 -> 验证建议 -> 论文写作。主要短板不是缺少 Agent，而是“建模意图证据”和“模型选择理由”在链路中没有形成稳定、可审计的结构化 trace。

样例日志显示，Q1/Q2 的描述性分析任务被推荐并选择为 TOPSIS，Q3 才选择 Grey Prediction。这说明当前整体题型能识别为 `prediction`，但小问级建模目标、目标变量、候选模型适用边界和非建模任务过滤还不够细。最终论文有“建模方案比较与选择”表，但没有把每个候选模型的评分字段、扣分理由、淘汰理由、假设风险和验证计划讲清楚。

另一个实际质量风险是中文文本在日志和报告中出现 mojibake。若这是读写路径或 fixture 编码问题，会直接影响题型识别、关键词匹配和论文可读性，应作为建模质量问题一并处理。

## 现状证据

- `ProblemParserAgent` 依赖关键词候选和简单规则输出 `problem_type`、`questions`、`objective`、`expected_outputs`，见 `src/agents/problem_parser.py:12`、`:59`、`:78`、`:94`。
- `TaskDecomposerAgent` 对每个小问固定拆成数据预处理、模型建立、结果解释三步，见 `src/agents/task_decomposer.py:21`、`:29`、`:37`。
- `StrategyGeneratorAgent` 已从 Model Zoo 生成候选模型，并携带 `why_suitable`、`input_data_requirements`、`risks_and_limitations`、`recommendation_score`、`data_type`，见 `src/agents/strategy_generator.py:65`、`:73`、`:103`。
- `ModelSelectorAgent` 已有 `data_fit_score`、`implementation_score`、`interpretability_score`、`stability_score`、`reportability_score`，但没有每项评分原因和淘汰原因，见 `src/agents/model_selector.py:33`、`:45`、`:61`。
- `SolutionCompetitionAgent` 已有三类方案和方案级评分维度，见 `src/agents/solution_competition_agent.py:44`、`:54`、`:132`。但评分更像固定风格偏好，不够基于题面证据和数据约束。
- `FormulaAgent` 使用模型名模板生成公式，样例中 `grey_prediction_GM11` 被映射成通用加权评分公式，说明公式模板与模型 ID 没有严格绑定，见 `src/agents/formula_agent.py:94`。
- `ValidationAgent` 输出通用误差、敏感性和稳健性建议，没有按已选模型、数据规模、目标变量和执行结果生成可检查项，见 `src/agents/validation.py:15`。
- `PaperWriterAgent` 已有“建模方案比较与选择”和每小问模型行，但正文只呈现选中模型、总分和简短理由，未呈现候选模型差异、评分 trace、未选原因，见 `src/agents/paper_writer.py:213`、`:418`。
- `FigurePlannerAgent` 按数据列顺序生成图，而不是按目标变量和小问目标生成图。样例中会画 `is_weekend versus temperature_c`、`temperature_c by date`，但未优先围绕 `orders`，见 `src/agents/figure_planner_agent.py:23`、`:43`、`:87`、`:102`。
- `ModelZoo` 校验基础字段，推荐分主要来自目标类别、data_type 和关键词命中，见 `src/tools/model_zoo.py:108`、`:129`、`:148`。缺少结构化适用条件、假设、验证指标和模型公式模板 ID。
- `PaperPatternLibrary` 已支持按整体题型和小问 objective 推荐 pattern，见 `src/tools/paper_pattern_library.py:42`、`:54`、`:70`，但 pattern 尚未约束“模型选择理由”应如何写入论文。

## 最小改进建议

### 1. 题型识别：从单标签改成带证据的多层识别

保留当前 `problem_type`，新增最小字段：

```json
{
  "problem_type": "prediction",
  "problem_type_candidates": [
    {"type": "prediction", "confidence": 0.82, "evidence": ["未来3天", "预测", "时间列date"]},
    {"type": "descriptive_modeling", "confidence": 0.55, "evidence": ["预处理", "描述统计", "变化规律"]}
  ],
  "question_type_summary": {"Q1": "descriptive_modeling", "Q2": "relationship_analysis", "Q3": "prediction"}
}
```

每个 question 建议补充：

- `question_type`：比现有 `objective` 更细，例如 `descriptive_statistics`、`factor_relationship`、`forecasting`、`optimization`、`evaluation_ranking`。
- `target_variables`：从题面和 data profile 推断，例如 `orders`。
- `driver_variables`：例如 `temperature_c`、`is_weekend`、`bikes_available`。
- `decision_variables`、`constraints`：优化题才需要。
- `deliverables`：数值表、预测区间、排名表、调度方案、敏感性分析等。
- `evidence`：触发识别的题面短语、数据列或规则名称。

这可以直接在 `ProblemParserAgent.run()` 结果中增加字段，不需要改变下游 Agent 类的数量。

### 2. 小问拆解：区分“建模任务”和“辅助任务”

当前每个小问都会产生 `data_preprocessing` 和 `result_interpretation`，这些辅助任务也会进入模型推荐，导致 TOPSIS/熵权被用于“预处理”和“解释”。建议在 `TaskDecomposerAgent` 的 task 中新增：

```json
{
  "task_role": "modeling",
  "requires_model_selection": true,
  "question_type": "forecasting",
  "target_variables": ["orders"],
  "validation_required": ["holdout_error", "residual_check"]
}
```

最小规则：

- `data_preprocessing`：`task_role = "support"`，`requires_model_selection = false`。
- `result_interpretation`：`task_role = "reporting"`，`requires_model_selection = false`。
- 只有核心建模任务进入 Model Zoo 推荐。
- Q1 描述统计可生成 `descriptive_statistics` 或 `eda_summary`，不强行选择 TOPSIS。
- Q2 关系分析应优先进入 `relationship_analysis`，候选可包含相关分析、线性回归、偏相关或解释型回归。
- Q3 预测任务才进入预测模型候选。

### 3. Model Zoo：补齐模型适用边界和论文表达元数据

保持 YAML 驱动，不需要新增工具。建议给每个模型增加以下可选字段：

```yaml
applicability:
  question_types: [forecasting, factor_relationship]
  data_types: [tabular, time_series_or_tabular]
  min_rows: 10
  target_required: true
  supports_small_sample: true
assumptions:
  - ordered positive sequence
  - smooth trend
validation_metrics:
  - posterior_error_ratio
  - residual_check
formula_template_id: grey_prediction_gm11
figure_suggestions:
  - actual_vs_predicted
  - residual_plot
selection_penalties:
  - volatile_series
```

这样 `ModelSelectorAgent` 可以按结构化字段打分，而不是只在拼接文本里搜关键词。当前已有 `advantages`、`limitations`、`paper_expression_template`，建议继续保留，并把它们用于报告正文。

### 4. 模型评分字段：从总分扩展为可解释 scorecard

当前评分维度方向是对的，但还缺少建模质量关键项。建议将 `ModelSelectorAgent.criteria` 最小扩展为：

- `problem_fit_score`：是否匹配小问类型和题面目标。
- `data_fit_score`：数据行数、目标变量、时间列、标签、约束数据是否满足。
- `mathematical_validity_score`：模型假设是否能被题面和数据支持。
- `validation_feasibility_score`：是否能做误差、敏感性、稳健性或可行性检查。
- `interpretability_score`：论文解释是否清楚。
- `implementation_score`：当前依赖和代码复杂度是否可控。
- `reportability_score`：公式、图表、表格是否好写入论文。
- `risk_penalty`：数据不足、假设过强、目标变量缺失、模型不适用等扣分。
- `total_score`。

每项分数都应带 `reason`：

```json
{
  "scores": {
    "problem_fit_score": {"value": 5, "reason": "Q3 explicitly asks future 3-day forecast."},
    "data_fit_score": {"value": 4, "reason": "date and orders exist, but only 14 rows."},
    "risk_penalty": {"value": -1, "reason": "Small sample limits validation reliability."},
    "total_score": 27
  }
}
```

这样论文和日志可以解释“为什么选它”，而不是只给一个 23/24 的总分。

### 5. 多方案比较：比较完整建模路线，不比较固定风格标签

现有 `conservative_solution`、`advanced_solution`、`hybrid_solution` 可以保留，但方案评分应基于每个小问的模型路线：

- `baseline_route`：描述统计/线性回归/简单预测等。
- `main_route`：系统推荐的主方案。
- `alternative_route`：更复杂或更稳健的备选方案。

每个方案建议新增：

```json
{
  "coverage_by_question": {"Q1": true, "Q2": true, "Q3": true},
  "model_route": [{"question_id": "Q3", "model_id": "grey_prediction_GM11"}],
  "why_selected": ["small sample", "forecasting objective", "high reportability"],
  "why_rejected_for_others": ["random_forest rejected: insufficient rows"],
  "validation_plan": ["posterior error", "rolling holdout if enough rows"]
}
```

论文表格应至少展示：方案名、覆盖小问、主模型、优点、风险、验证可行性、总分、选择/淘汰理由。

### 6. 模型选择 trace：作为一等字段贯穿下游

在 `ModelSelectorAgent.run()` 结果中新增：

```json
{
  "model_selection_trace": [
    {
      "task_id": "Q3.2",
      "question_id": "Q3",
      "question_type": "forecasting",
      "input_evidence": ["预测", "未来3天", "date column", "orders target"],
      "candidate_ids": ["grey_prediction_GM11", "linear_regression", "polynomial_regression"],
      "selected_model_id": "grey_prediction_GM11",
      "selection_reason": "Best fit for small-sample ordered forecasting with clear formula.",
      "rejected_reasons": {
        "linear_regression": "Good baseline but target has only 14 rows; keep as comparison.",
        "polynomial_regression": "Higher overfitting risk for 14 rows."
      }
    }
  ]
}
```

`PaperWriterAgent`、`FormulaAgent`、`ValidationAgent`、`FigurePlannerAgent` 都应优先读这个 trace。这样不用新增 Agent，也能让建模理由稳定落地。

### 7. 公式生成：从模型名判断改为 Model Zoo 公式模板

当前 `FormulaAgent._formula_for_model()` 用字符串包含关系生成公式，容易错配。最小改法：

- 在 Model Zoo 增加 `formula_template_id` 和 `symbols`。
- `FormulaAgent` 根据 `model_id` 选择公式模板。
- `checks` 增加 `formula_matches_model_id`、`formula_covers_each_modeling_task`、`symbols_used_are_defined`。
- 对 `grey_prediction_GM11`、`ARIMA`、`linear_regression`、`TOPSIS`、`entropy_weight`、`linear_programming` 先补最常用模板即可。

验收示例：`grey_prediction_GM11` 不应再输出通用 `S_i=sum w_j z_ij` 作为主公式。

### 8. 验证：按模型和小问生成可执行检查项

`ValidationAgent` 应消费 `model_selection_trace`、`data_profile`、`execution_result`、`formulas`，输出 per-question 验证计划：

```json
{
  "validation_by_question": [
    {
      "question_id": "Q3",
      "model_id": "grey_prediction_GM11",
      "checks": [
        {"name": "sample_size_warning", "status": "warn", "evidence": "14 rows"},
        {"name": "posterior_error_ratio", "status": "todo"},
        {"name": "sensitivity_window", "status": "todo", "perturbation": "last point +/-10%"}
      ]
    }
  ]
}
```

优化题要检查约束可行性；评价题要检查权重扰动和排名稳定性；预测题要检查残差、误差指标、外推风险；分类题要检查轮廓系数或混淆矩阵。

### 9. 论文写作：把模型选择理由写成正文资产

`PaperWriterAgent` 当前已有章节，但模型选择理由不够像论文。建议在“建模方案比较与选择”和每个小问的“模型建立”中固定加入：

- 小问题型和证据。
- 候选模型对比表：模型、适用性、数据要求、假设、优点、风险、验证方式、综合分。
- 选中理由：明确对应题面目标、数据条件、可解释性和可验证性。
- 未选理由：说明复杂模型为何不采用或只作为备选。
- 模型假设与适用边界。
- 与公式、图表、验证计划的引用关系。

`_selected_model_lines()` 不应只写 “模型名 + why_suitable + 总分”，而应使用 `model_selection_trace` 生成更短、更像论文的理由。

### 10. Paper Patterns：增加“模型选择段落”约束

在 `paper_patterns.yaml` 每类题型中增加：

```yaml
model_selection_requirements:
  - compare at least one baseline and one alternative where available
  - report assumptions and validation metrics
  - explain rejected models briefly
recommended_model_comparison_columns:
  - model
  - applicable_question
  - data_requirement
  - assumptions
  - validation_method
  - risk
  - score
```

这可以直接被 `PaperWriterAgent` 使用，不需要新增 Agent。

### 11. FigurePlanner：按小问目标和目标变量规划图

当前图表按列顺序生成，容易偏离题目。建议输入 `question_type_summary`、`target_variables`、`selected_model_trace` 后生成：

- Q1 描述统计：目标变量分布、时间趋势、缺失/异常概览。
- Q2 关系分析：目标变量 `orders` vs 驱动变量散点、相关热力图、回归系数或变量重要性图。
- Q3 预测：真实值-拟合值、未来预测图、残差图、敏感性曲线。

新增字段：

```json
{
  "question_id": "Q3",
  "linked_model_id": "grey_prediction_GM11",
  "target_variable": "orders",
  "figure_relevance_score": 5,
  "required_result_fields": ["actual", "predicted", "forecast"]
}
```

残差图、预测图、敏感性图应在没有相应结果字段时标记为 `planned_but_missing_data`，不要默认当作已经可画。

## 建议实施顺序

1. 先修 Parser 和 Decomposer 字段：加入小问题型、目标变量、证据、`requires_model_selection`。这是后续质量的根。
2. 改 StrategyGenerator 过滤逻辑：只对 `requires_model_selection=true` 的任务推荐模型，辅助任务保留为工作步骤。
3. 扩展 Model Zoo 元数据和 ModelSelector scorecard：增加评分 reason、reject reason、`model_selection_trace`。
4. 让 Formula、Validation、FigurePlanner 从 trace 读模型和目标变量，修正公式错配和图表偏题。
5. 最后改 PaperWriter：把 trace 写入“方案比较与选择”和每小问“模型建立”，形成可审计论文理由。

## 验收标准

- 样例题中 Q1 不再选择 TOPSIS 作为“数据预处理模型”；Q2 不再把 TOPSIS 作为关系分析主模型；Q3 能说明为什么选择预测模型以及为什么不选更复杂模型。
- 每个核心建模任务都有 `selected_model_id`、候选模型列表、分项评分、选择理由、未选理由。
- 论文正文能看到模型选择 trace，而不是只看到总分。
- FormulaAgent 生成的核心公式与 `model_id` 一致。
- ValidationAgent 输出按小问和模型划分的检查项。
- FigurePlanner 的主图围绕目标变量和小问目标，而不是数据列顺序。
- 中文题面、日志和最终报告不出现 mojibake。

## 不建议做的事

- 不新增运行时 Agent Team、`src/team`、`src/team_agents`。
- 不把当前 Agent 全部重写成 LLM prompt 流程。
- 不把多方案比较变成另一个独立团队；复用现有 `SolutionCompetitionAgent` 或把方案比较逻辑保留在现有选择链路即可。
- 不只提高模型复杂度。建模质量的核心是题意匹配、数据可行、假设清楚、验证可做、论文理由可审计。
