# cumcm-auto-solver

中文 | [English](#english)

## 中文

`cumcm-auto-solver` 是一个用于往年或合成数学建模题复现的本地 Auto-Solver Agent 原型。项目面向离线实验、教学研究和可复现分析，不用于正在进行的真实竞赛。

系统可以读取赛题和数据文件，自动完成题目解析、任务拆解、数据画像、模型库推荐、多方案比较、公式生成、代码生成、安全执行、错误修复、结果分析、图表规划、反思修订，并输出 Markdown 论文草稿。

### 功能概览

- 支持 `txt`、`pdf`、`docx`、`csv`、`xlsx` 输入。
- 使用模块化 Agent 架构，所有中间结果保存为 JSON 日志。
- 内置 Model Zoo，用于常见预测、优化、评价、分类、网络和仿真模型推荐。
- 内置 Paper Pattern Library，用于生成更接近数学建模论文格式的结构。
- 支持 Data Profiler、Figure Planner、Formula Agent、Reflection Loop。
- 支持 Mock LLM、DeepSeek、OpenAI-compatible API 和本地 HTTP LLM。
- 支持 Streamlit 可视化工作台。
- 支持本地 RAG 知识库和 Benchmark 批量评测。
- 自动生成代码、图表、报告，并提供 Word / PDF 导出能力。

### 安装

建议使用 Python 3.11。

```bash
pip install -r requirements.txt
```

### 命令行运行

运行示例题：

```bash
python main.py --problem examples/sample_problem/problem.txt --data examples/sample_problem/data
```

导出 Word：

```bash
python main.py --problem examples/sample_problem/problem.txt --data examples/sample_problem/data --export-docx
```

尝试导出 PDF：

```bash
python main.py --problem examples/sample_problem/problem.txt --data examples/sample_problem/data --export-docx --export-pdf
```

构建本地知识库索引：

```bash
python main.py --build-kb knowledge_base/
```

启用 RAG：

```bash
python main.py --problem examples/sample_problem/problem.txt --data examples/sample_problem/data --use-rag
```

运行 Benchmark：

```bash
python main.py --benchmark benchmark/benchmark_config.yaml
```

### Streamlit 工作台

```bash
streamlit run app.py
```

如果 `streamlit` 命令不可用，可以使用：

```bash
python -m streamlit run app.py
```

如果默认端口被占用：

```bash
python -m streamlit run app.py --server.port 8504
```

前端包含以下页面：

- `总览 Dashboard`：工作流进度、核心指标、最终路线、报告状态。
- `题目解析`：背景摘要、小问列表、关键词、题型判断。
- `数据画像`：表结构、缺失值、预处理建议、EDA 图表。
- `建模策略`：Model Zoo 候选模型、模型评分、RAG 参考。
- `方案比较`：保守方案、增强方案、混合方案比较。
- `公式与图表`：符号表、LaTeX 公式、图表规划、生成图表。
- `代码执行`：执行尝试、修复记录、stdout / stderr、代码下载。
- `反思与修订`：质量评分、发现问题、修订建议。
- `论文报告`：Markdown 报告预览和下载。
- `运行日志`：JSON / JSONL 日志查看器。

如果某些日志、图表或报告尚未生成，页面会显示空状态，不会直接崩溃。

### DeepSeek / LLM 配置

Mock 模式不需要 API key，是默认兜底模式。

真实 LLM 的配置在 `config/model_config.yaml` 中。API key 必须通过环境变量提供，不要写入代码或配置文件。

Windows PowerShell 示例：

```powershell
setx DEEPSEEK_API_KEY "your_deepseek_key"
setx DEEPSEEK_MODEL "deepseek-v4-flash"
setx DEEPSEEK_BASE_URL "https://api.deepseek.com"
```

重新打开终端后运行：

```bash
python main.py --llm deepseek --problem examples/sample_problem/problem.txt --data examples/sample_problem/data
```

OpenAI-compatible 示例：

```bash
set OPENAI_API_KEY=your_key_here
set OPENAI_BASE_URL=https://api.example.com/v1
set OPENAI_MODEL=your-model
python main.py --llm openai-compatible --problem examples/sample_problem/problem.txt --data examples/sample_problem/data
```

支持的客户端：

- `MockLLMClient`
- `DeepSeekLLMClient`
- `OpenAICompatibleLLMClient`
- `LocalHTTPLLMClient`

LLM 调用日志保存到 `outputs/logs/llm_calls.jsonl`。

### RAG 知识库

本地知识库存放在：

- `knowledge_base/problems/`
- `knowledge_base/methods/`
- `knowledge_base/paper_templates/`
- `knowledge_base/notes/`

支持文件类型：`txt`、`md`、`pdf`、`docx`。

第一版使用确定性的关键词检索。检索内容只作为方法启发，报告应重新组织表达，避免复制原文。

检索日志保存到 `outputs/logs/rag_retrievals.json`。

### Benchmark

Benchmark 配置文件：

```text
benchmark/benchmark_config.yaml
```

每个任务包含：

- `task_id`
- `problem_file`
- `data_dir`
- `expected_problem_type`
- `expected_outputs`
- `scoring_rubric`

输出：

- `benchmark/results/{task_id}/`
- `benchmark/results/summary.csv`
- `benchmark/results/benchmark_report.md`

### 安全边界

自动生成的 Python 代码保存到 `outputs/code/`，并且只允许在 `outputs/code_workspace/` 中执行。

执行前，`CodeSafetyChecker` 会拦截：

- 删除文件或删除目录
- `subprocess`、shell 命令、`shell=True`
- socket / requests 网络访问
- 用户主目录路径和项目外绝对路径
- 修改环境变量
- `pip install`

不安全代码不会被执行。安全检查结果保存到 `outputs/logs/code_safety.json`。

执行尝试保存到 `outputs/logs/execution_attempts.json`。修复版本保存为：

- `outputs/code/attempt_1.py`
- `outputs/code/attempt_2.py`
- `outputs/code/attempt_3.py`

### 输出目录

- `outputs/logs/`：JSON 日志、LLM 调用、安全检查、执行尝试、RAG 检索记录。
- `outputs/code/`：生成的 Python 代码和结果文件。
- `outputs/code_workspace/`：受控代码执行目录。
- `outputs/figures/`：生成图表。
- `outputs/figures/data_profile/`：数据画像图表。
- `outputs/reports/solution_report.md`：Markdown 报告。
- `outputs/reports/solution_report.docx`：可选 Word 导出。
- `outputs/reports/solution_report.pdf`：可选 PDF 导出。

### 测试

```bash
python -m pytest
```

测试覆盖文件读取、模型库、论文模板、数据画像、图表规划、公式生成、代码修复、安全检查、RAG、Benchmark、报告导出、LLM mock 行为和完整工作流冒烟测试。

### 隐私与密钥

不要提交 `.env`、API key、真实竞赛数据或个人敏感文件。项目 `.gitignore` 默认排除了 `.env`、`.env.*`、`outputs/`、运行日志、生成报告、benchmark 结果和本地索引文件。

---

## English

`cumcm-auto-solver` is a local Auto-Solver Agent prototype for replaying historical or synthetic mathematical modeling problems. It is intended for offline experiments, teaching, research, and reproducible analysis, not for active live competitions.

The system reads a problem statement and data files, parses the problem, decomposes tasks, profiles data, recommends models from a model zoo, compares multiple solution routes, generates formulas and Python code, executes code in a controlled workspace, repairs failures, analyzes outputs, plans figures, reflects on report quality, and writes a Markdown paper draft.

### Features

- Supports `txt`, `pdf`, `docx`, `csv`, and `xlsx` inputs.
- Modular Agent architecture with structured JSON logs.
- Model Zoo for prediction, optimization, evaluation, classification, network, and simulation models.
- Paper Pattern Library for mathematical modeling paper templates.
- Data Profiler, Figure Planner, Formula Agent, and Reflection Loop.
- Mock LLM, DeepSeek, OpenAI-compatible API, and local HTTP LLM support.
- Streamlit visual workbench.
- Local RAG knowledge base and Benchmark batch evaluation.
- Generated code, figures, reports, and optional Word / PDF exports.

### Installation

Python 3.11 is recommended.

```bash
pip install -r requirements.txt
```

### Command Line

Run the included sample problem:

```bash
python main.py --problem examples/sample_problem/problem.txt --data examples/sample_problem/data
```

Export Word:

```bash
python main.py --problem examples/sample_problem/problem.txt --data examples/sample_problem/data --export-docx
```

Try PDF export:

```bash
python main.py --problem examples/sample_problem/problem.txt --data examples/sample_problem/data --export-docx --export-pdf
```

Build the local knowledge base index:

```bash
python main.py --build-kb knowledge_base/
```

Run with RAG:

```bash
python main.py --problem examples/sample_problem/problem.txt --data examples/sample_problem/data --use-rag
```

Run benchmark:

```bash
python main.py --benchmark benchmark/benchmark_config.yaml
```

### Streamlit Workbench

```bash
streamlit run app.py
```

If the `streamlit` command is unavailable:

```bash
python -m streamlit run app.py
```

If the default port is occupied:

```bash
python -m streamlit run app.py --server.port 8504
```

The workbench includes tabs for dashboard, problem parsing, data profile, modeling strategy, solution comparison, formulas and figures, code execution, reflection, paper report, and logs.

Missing logs, figures, or reports are handled with empty states instead of page crashes.

### DeepSeek / LLM Configuration

Mock mode requires no API key and is the default fallback.

Real LLM settings live in `config/model_config.yaml`. API keys must be supplied through environment variables and must not be written into code or config files.

Windows PowerShell example:

```powershell
setx DEEPSEEK_API_KEY "your_deepseek_key"
setx DEEPSEEK_MODEL "deepseek-v4-flash"
setx DEEPSEEK_BASE_URL "https://api.deepseek.com"
```

Restart the terminal, then run:

```bash
python main.py --llm deepseek --problem examples/sample_problem/problem.txt --data examples/sample_problem/data
```

OpenAI-compatible example:

```bash
set OPENAI_API_KEY=your_key_here
set OPENAI_BASE_URL=https://api.example.com/v1
set OPENAI_MODEL=your-model
python main.py --llm openai-compatible --problem examples/sample_problem/problem.txt --data examples/sample_problem/data
```

Supported clients:

- `MockLLMClient`
- `DeepSeekLLMClient`
- `OpenAICompatibleLLMClient`
- `LocalHTTPLLMClient`

LLM call logs are saved to `outputs/logs/llm_calls.jsonl`.

### RAG Knowledge Base

Local knowledge files live under:

- `knowledge_base/problems/`
- `knowledge_base/methods/`
- `knowledge_base/paper_templates/`
- `knowledge_base/notes/`

Supported file types: `txt`, `md`, `pdf`, `docx`.

The first implementation uses deterministic keyword retrieval. Retrieved content is used only as method inspiration; generated reports should rewrite all text and avoid copying source passages.

RAG retrieval logs are saved to `outputs/logs/rag_retrievals.json`.

### Benchmark

Benchmark config:

```text
benchmark/benchmark_config.yaml
```

Each task includes:

- `task_id`
- `problem_file`
- `data_dir`
- `expected_problem_type`
- `expected_outputs`
- `scoring_rubric`

Outputs:

- `benchmark/results/{task_id}/`
- `benchmark/results/summary.csv`
- `benchmark/results/benchmark_report.md`

### Safety Boundary

Generated Python code is saved to `outputs/code/` and executed only in `outputs/code_workspace/`.

Before execution, `CodeSafetyChecker` blocks:

- file or directory deletion
- `subprocess`, shell commands, and `shell=True`
- socket / requests network access
- user home paths and project-external absolute paths
- environment variable mutation
- `pip install`

Unsafe code is not executed. The safety result is saved to `outputs/logs/code_safety.json`.

Execution attempts are saved to `outputs/logs/execution_attempts.json`. Repair versions are saved as:

- `outputs/code/attempt_1.py`
- `outputs/code/attempt_2.py`
- `outputs/code/attempt_3.py`

### Output Directories

- `outputs/logs/`: JSON logs, LLM calls, safety checks, execution attempts, RAG retrievals.
- `outputs/code/`: generated Python code and result files.
- `outputs/code_workspace/`: controlled execution working directory.
- `outputs/figures/`: generated figures.
- `outputs/figures/data_profile/`: data profiling figures.
- `outputs/reports/solution_report.md`: Markdown report.
- `outputs/reports/solution_report.docx`: optional Word export.
- `outputs/reports/solution_report.pdf`: optional PDF export.

### Tests

```bash
python -m pytest
```

The test suite covers file loading, model zoo, paper patterns, data profiling, figure planning, formula generation, code repair, safety checks, RAG, benchmark evaluation, report export, LLM mock behavior, and workflow smoke execution.

### Privacy And Secrets

Do not commit `.env`, API keys, live competition data, or sensitive personal files. The project `.gitignore` excludes `.env`, `.env.*`, `outputs/`, logs, generated reports, benchmark results, and local indexes by default.
