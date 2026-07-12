# Knowledge Base Index Notes

## 本次精修文件清单

| 文件 | 卡片类别 | 推荐检索关键词 | 适合题型 | 人工复核优先级 |
| --- | --- | --- | --- | --- |
| problems/common_subquestion_patterns.md | 题型套路卡 | 第一问、第二问、第三问、最后一问、数据理解、核心建模、推广建议、鲁棒性 | 混合类、综合建模 | 高 |
| problems/problem_type_router.md | 题型路由卡 | 评价类、预测类、优化类、分类聚类、仿真类、网络图论、混合类、题型判断 | 全部题型 | 高 |
| problems/modeling_route_selection.md | 建模路线选择卡 | data_fit_score、implementation_score、interpretability_score、stability_score、reportability_score、formula_quality_score、sensitivity_analysis_potential | 多方案比较、模型选择 | 高 |
| methods/evaluation/entropy_weight.md | 评价方法卡 | 熵权法、客观赋权、指标标准化、权重扰动、综合评价、熵权 TOPSIS | 评价类、排序类 | 高 |
| methods/evaluation/topsis.md | 评价方法卡 | TOPSIS、理想解、接近度、综合排序、熵权 TOPSIS、排名解释 | 评价类、排序类 | 高 |
| paper_templates/evaluation_problem_template.md | 论文模板卡 | 评价类论文、指标体系、综合评价、排名解释、灵敏度分析 | 评价类 | 高 |
| methods/optimization/linear_programming.md | 优化方法卡 | 线性规划、连续决策变量、目标函数、约束条件、资源分配 | 优化类 | 高 |
| methods/optimization/integer_programming.md | 优化方法卡 | 整数规划、0-1 变量、选择分配、排班、路径、整数约束 | 优化类、路径类 | 高 |
| paper_templates/optimization_problem_template.md | 论文模板卡 | 优化类论文、决策变量、目标函数、约束条件、最优方案、敏感性分析 | 优化类 | 高 |
| notes/sensitivity_analysis.md | 写作与验证卡 | 灵敏度分析、权重扰动、参数扰动、约束扰动、排名稳定性、目标函数变化 | 评价类、预测类、优化类、仿真类 | 高 |
| notes/abstract_writing.md | 写作卡 | 论文摘要、方法路线、关键结果、误差评价、模型结论、摘要扣分点 | 全部题型 | 高 |
| notes/figure_design.md | 图表规划卡 | 图表设计、权重柱状图、预测对比图、资源分配图、聚类散点图、网络结构图、灵敏度曲线 | 全部题型 | 高 |

## 精修卡使用建议

- 模型选择阶段优先检索 `problems/` 和 `methods/`：用于判断题型、选择候选模型、说明适用与不适用边界。
- 公式生成阶段优先检索 `methods/`：用于提取变量、目标函数、约束条件、评价指标和核心公式。
- 图表规划阶段优先检索 `notes/figure_design.md` 与方法卡的推荐图表：用于决定论文中必须生成的核心图。
- 论文写作阶段优先检索 `paper_templates/` 与 `notes/abstract_writing.md`：用于组织章节和生成竞赛风格表达。
- 验证与反思阶段优先检索 `notes/sensitivity_analysis.md`：用于补充权重扰动、参数扰动、约束扰动和排名稳定性说明。

## 人工复核优先级说明

- 高：直接影响题型判断、模型选择、公式表达、最终论文结构和评分。
- 中：主要影响代码实现、图表风格或局部表述。
- 低：作为补充背景材料，通常不决定主模型路线。

| 文件 | 类别 | 适合题型 | 推荐检索关键词 | 精修优先级 |
| --- | --- | --- | --- | --- |
| code_patterns/classification_pattern.md | 代码套路 | classification pattern | classification pattern、数学建模、RAG | 中 |
| code_patterns/clustering_pattern.md | 代码套路 | clustering pattern | clustering pattern、数学建模、RAG | 中 |
| code_patterns/data_cleaning_pattern.md | 代码套路 | data cleaning pattern | data cleaning pattern、数学建模、RAG | 中 |
| code_patterns/optimization_pattern.md | 代码套路 | optimization pattern | optimization pattern、数学建模、RAG | 中 |
| code_patterns/regression_pattern.md | 代码套路 | regression pattern | regression pattern、数学建模、RAG | 中 |
| code_patterns/report_figure_pattern.md | 代码套路 | report figure pattern | report figure pattern、数学建模、RAG | 中 |
| code_patterns/robustness_check_pattern.md | 代码套路 | robustness check pattern | robustness check pattern、数学建模、RAG | 中 |
| code_patterns/safe_code_execution_pattern.md | 代码套路 | safe code execution pattern | safe code execution pattern、数学建模、RAG | 中 |
| code_patterns/sensitivity_analysis_pattern.md | 代码套路 | sensitivity analysis pattern | sensitivity analysis pattern、数学建模、RAG | 中 |
| code_patterns/visualization_pattern.md | 代码套路 | visualization pattern | visualization pattern、数学建模、RAG | 中 |
| methods/baseline_methods.md | 方法卡 | baseline methods | baseline methods、数学建模、RAG | 高 |
| methods/classification/dbscan.md | 方法卡 | dbscan | dbscan、数学建模、RAG | 高 |
| methods/classification/hierarchical_clustering.md | 方法卡 | hierarchical clustering | hierarchical clustering、数学建模、RAG | 高 |
| methods/classification/kmeans.md | 方法卡 | kmeans | kmeans、数学建模、RAG | 高 |
| methods/classification/pca_dimension_reduction.md | 方法卡 | pca dimension reduction | pca dimension reduction、数学建模、RAG | 高 |
| methods/classification/random_forest_classifier.md | 方法卡 | random forest classifier | random forest classifier、数学建模、RAG | 高 |
| methods/classification/svm.md | 方法卡 | svm | svm、数学建模、RAG | 高 |
| methods/evaluation/ahp.md | 方法卡 | ahp | ahp、数学建模、RAG | 高 |
| methods/evaluation/comprehensive_score_model.md | 方法卡 | comprehensive score model | comprehensive score model、数学建模、RAG | 高 |
| methods/evaluation/entropy_weight.md | 方法卡 | entropy weight | entropy weight、数学建模、RAG | 高 |
| methods/evaluation/fuzzy_evaluation.md | 方法卡 | fuzzy evaluation | fuzzy evaluation、数学建模、RAG | 高 |
| methods/evaluation/grey_relational_analysis.md | 方法卡 | grey relational analysis | grey relational analysis、数学建模、RAG | 高 |
| methods/evaluation/pca_evaluation.md | 方法卡 | pca evaluation | pca evaluation、数学建模、RAG | 高 |
| methods/evaluation/topsis.md | 方法卡 | topsis | topsis、数学建模、RAG | 高 |
| methods/network/community_detection.md | 方法卡 | community detection | community detection、数学建模、RAG | 高 |
| methods/network/max_flow.md | 方法卡 | max flow | max flow、数学建模、RAG | 高 |
| methods/network/min_cost_flow.md | 方法卡 | min cost flow | min cost flow、数学建模、RAG | 高 |
| methods/network/network_centrality.md | 方法卡 | network centrality | network centrality、数学建模、RAG | 高 |
| methods/network/pagerank.md | 方法卡 | pagerank | pagerank、数学建模、RAG | 高 |
| methods/network/shortest_path.md | 方法卡 | shortest path | shortest path、数学建模、RAG | 高 |
| methods/optimization/genetic_algorithm.md | 方法卡 | genetic algorithm | genetic algorithm、数学建模、RAG | 高 |
| methods/optimization/goal_programming.md | 方法卡 | goal programming | goal programming、数学建模、RAG | 高 |
| methods/optimization/integer_programming.md | 方法卡 | integer programming | integer programming、数学建模、RAG | 高 |
| methods/optimization/linear_programming.md | 方法卡 | linear programming | linear programming、数学建模、RAG | 高 |
| methods/optimization/multi_objective_optimization.md | 方法卡 | multi objective optimization | multi objective optimization、数学建模、RAG | 高 |
| methods/optimization/nonlinear_programming.md | 方法卡 | nonlinear programming | nonlinear programming、数学建模、RAG | 高 |
| methods/optimization/simulated_annealing.md | 方法卡 | simulated annealing | simulated annealing、数学建模、RAG | 高 |
| methods/prediction/arima.md | 方法卡 | arima | arima、数学建模、RAG | 高 |
| methods/prediction/grey_prediction_gm11.md | 方法卡 | grey prediction gm11 | grey prediction gm11、数学建模、RAG | 高 |
| methods/prediction/linear_regression.md | 方法卡 | linear regression | linear regression、数学建模、RAG | 高 |
| methods/prediction/model_error_metrics.md | 方法卡 | model error metrics | model error metrics、数学建模、RAG | 高 |
| methods/prediction/polynomial_regression.md | 方法卡 | polynomial regression | polynomial regression、数学建模、RAG | 高 |
| methods/prediction/random_forest_prediction.md | 方法卡 | random forest prediction | random forest prediction、数学建模、RAG | 高 |
| methods/prediction/time_series_forecasting.md | 方法卡 | time series forecasting | time series forecasting、数学建模、RAG | 高 |
| methods/simulation/agent_based_simulation.md | 方法卡 | agent based simulation | agent based simulation、数学建模、RAG | 高 |
| methods/simulation/cellular_automata.md | 方法卡 | cellular automata | cellular automata、数学建模、RAG | 高 |
| methods/simulation/monte_carlo.md | 方法卡 | monte carlo | monte carlo、数学建模、RAG | 高 |
| methods/simulation/scenario_simulation.md | 方法卡 | scenario simulation | scenario simulation、数学建模、RAG | 高 |
| methods/simulation/system_dynamics.md | 方法卡 | system dynamics | system dynamics、数学建模、RAG | 高 |
| notes/abstract_writing.md | 通用经验 | abstract writing | abstract writing、数学建模、RAG | 中 |
| notes/assumptions_writing.md | 通用经验 | assumptions writing | assumptions writing、数学建模、RAG | 中 |
| notes/common_failure_modes.md | 通用经验 | common failure modes | common failure modes、数学建模、RAG | 中 |
| notes/common_modeling_workflow.md | 通用经验 | common modeling workflow | common modeling workflow、数学建模、RAG | 中 |
| notes/figure_design.md | 通用经验 | figure design | figure design、数学建模、RAG | 中 |
| notes/model_evaluation_writing.md | 通用经验 | model evaluation writing | model evaluation writing、数学建模、RAG | 中 |
| notes/national_prize_quality_checklist.md | 通用经验 | national prize quality checklist | national prize quality checklist、数学建模、RAG | 中 |
| notes/result_interpretation.md | 通用经验 | result interpretation | result interpretation、数学建模、RAG | 中 |
| notes/robustness_analysis.md | 通用经验 | robustness analysis | robustness analysis、数学建模、RAG | 中 |
| notes/sensitivity_analysis.md | 通用经验 | sensitivity analysis | sensitivity analysis、数学建模、RAG | 中 |
| paper_templates/basic_structure.md | 论文模板 | basic structure | basic structure、数学建模、RAG | 高 |
| paper_templates/classification_problem_template.md | 论文模板 | classification problem template | classification problem template、数学建模、RAG | 高 |
| paper_templates/evaluation_problem_template.md | 论文模板 | evaluation problem template | evaluation problem template、数学建模、RAG | 高 |
| paper_templates/mixed_problem_template.md | 论文模板 | mixed problem template | mixed problem template、数学建模、RAG | 高 |
| paper_templates/network_problem_template.md | 论文模板 | network problem template | network problem template、数学建模、RAG | 高 |
| paper_templates/optimization_problem_template.md | 论文模板 | optimization problem template | optimization problem template、数学建模、RAG | 高 |
| paper_templates/prediction_problem_template.md | 论文模板 | prediction problem template | prediction problem template、数学建模、RAG | 高 |
| paper_templates/simulation_problem_template.md | 论文模板 | simulation problem template | simulation problem template、数学建模、RAG | 高 |
| problems/common_subquestion_patterns.md | 题型套路 | common subquestion patterns | common subquestion patterns、数学建模、RAG | 高 |
| problems/cumcm_common_problem_types.md | 题型套路 | cumcm common problem types | cumcm common problem types、数学建模、RAG | 高 |
| problems/final_question_patterns.md | 题型套路 | final question patterns | final question patterns、数学建模、RAG | 高 |
| problems/first_question_patterns.md | 题型套路 | first question patterns | first question patterns、数学建模、RAG | 高 |
| problems/mixed_problem_decomposition.md | 题型套路 | mixed problem decomposition | mixed problem decomposition、数学建模、RAG | 高 |
| problems/modeling_route_selection.md | 题型套路 | modeling route selection | modeling route selection、数学建模、RAG | 高 |
| problems/problem_type_router.md | 题型套路 | problem type router | problem type router、数学建模、RAG | 高 |
| QUALITY_CHECKLIST.md | 说明文档 | QUALITY CHECKLIST | QUALITY CHECKLIST、数学建模、RAG | 中 |
| README.md | 说明文档 | README | README、数学建模、RAG | 中 |
