# cumcm-auto-solver

中文 | [English](#english)

## 中文

`cumcm-auto-solver` 是一个用于往年或合成数学建模题复现的 Auto-Solver Agent 工作台。项目面向离线实验、教学研究和可复现分析，不用于正在进行的真实竞赛。

系统固定使用 DeepSeek 作为正式 LLM Provider。用户上传赛题文件和可选数据文件后，系统会完成题目解析、任务拆解、数据画像、模型推荐、多方案比较、公式生成、代码生成与安全执行、错误修复、结果分析、图表规划、反思修订和论文草稿生成。

### 功能

- 支持 `txt`、`pdf`、`docx`、`csv`、`xlsx` 输入。
- Streamlit 工作台支持上传题面和多个数据文件。
- Model Zoo 管理预测、优化、评价、分类、网络和仿真模型。
- Paper Pattern Library 根据题型生成数学建模论文结构。
- Data Profiler 自动识别字段类型、缺失值、相关性和可视化建议。
- Figure Planner、Formula Agent、Solution Competition、Reflection Loop。
- 自动生成代码、图表、Markdown 报告，并可导出 Word / PDF。
- 生成代码只允许在 `outputs/code_workspace/` 内执行。

### 安装

建议使用 Python 3.11。

```bash
pip install -r requirements.txt
```

### 配置 DeepSeek

未配置 `DEEPSEEK_API_KEY` 时，命令行和 UI 都会直接报错，不会自动回退到 mock。

macOS / Linux:

```bash
export DEEPSEEK_API_KEY="你的 DeepSeek API Key"
export DEEPSEEK_MODEL="deepseek-v4-flash"
export DEEPSEEK_BASE_URL="https://api.deepseek.com"
```

Windows PowerShell:

```powershell
$env:DEEPSEEK_API_KEY="你的 DeepSeek API Key"
$env:DEEPSEEK_MODEL="deepseek-v4-flash"
$env:DEEPSEEK_BASE_URL="https://api.deepseek.com"
```

如果希望永久保存到当前 Windows 用户环境变量，可使用：

```powershell
setx DEEPSEEK_API_KEY "你的 DeepSeek API Key"
setx DEEPSEEK_MODEL "deepseek-v4-flash"
setx DEEPSEEK_BASE_URL "https://api.deepseek.com"
```

执行 `setx` 后请重新打开终端。

### 命令行运行

带数据目录运行：

```bash
python main.py --problem path/to/problem.pdf --data path/to/data_dir --export-docx
```

无数据文件运行：

```bash
python main.py --problem path/to/problem.pdf --export-docx
```

自定义 DeepSeek 模型：

```bash
python main.py --problem path/to/problem.docx --data path/to/data_dir --deepseek-model deepseek-v4-flash
```

启用 RAG：

```bash
python main.py --problem path/to/problem.pdf --data path/to/data_dir --use-rag
```

构建本地知识库索引：

```bash
python main.py --build-kb knowledge_base/
```

运行 Benchmark：

```bash
python main.py --benchmark benchmark/benchmark_config.yaml
```

### Streamlit 工作台

```bash
streamlit run app.py
```

如果 `streamlit` 命令不可用：

```bash
python -m streamlit run app.py
```

如果默认端口被占用：

```bash
python -m streamlit run app.py --server.port 8504
```

UI 只支持上传赛题文件和数据文件。未上传赛题文件时无法运行；未上传数据文件时，系统会提示并仅基于题面文本建模。

### RAG 知识库

本地知识库目录：

- `knowledge_base/problems/`
- `knowledge_base/methods/`
- `knowledge_base/paper_templates/`
- `knowledge_base/notes/`

支持 `txt`、`md`、`pdf`、`docx`。检索结果只作为方法启发，报告会重新组织表达。

### Benchmark

配置文件：

```text
benchmark/benchmark_config.yaml
```

输出：

- `benchmark/results/{task_id}/`
- `benchmark/results/summary.csv`
- `benchmark/results/benchmark_report.md`

### 输出目录

- `outputs/logs/`: JSON 日志、LLM 调用、安全检查、执行尝试、RAG 检索记录。
- `outputs/code/`: 生成的 Python 代码和结果文件。
- `outputs/code_workspace/`: 受控代码执行目录。
- `outputs/figures/`: 生成图表。
- `outputs/figures/data_profile/`: 数据画像图表。
- `outputs/reports/solution_report.md`: Markdown 报告。
- `outputs/reports/solution_report.docx`: 可选 Word 导出。
- `outputs/reports/solution_report.pdf`: 可选 PDF 导出。

### 安全边界

执行前 `CodeSafetyChecker` 会拦截删除文件、`subprocess`、shell 命令、网络访问、用户主目录路径、项目外绝对路径、环境变量修改和 `pip install`。不安全代码不会被执行。

### 测试

```bash
python -m pytest
```

底层 mock 客户端仍保留用于单元测试和兼容性测试，但正式 CLI 与 Streamlit UI 不再提供 mock 运行入口。

### 隐私与密钥

不要提交 `.env`、API key、真实竞赛数据或个人敏感文件。`.gitignore` 默认排除 `.env`、`.env.*`、`outputs/`、运行日志、生成报告、benchmark 结果和本地索引文件。

---

## English

`cumcm-auto-solver` is an Auto-Solver Agent workbench for replaying historical or synthetic mathematical modeling problems. It is intended for offline experiments, teaching, research, and reproducible analysis, not for active live competitions.

The product mode uses DeepSeek as the fixed LLM provider. After a user uploads a problem file and optional data files, the system parses the problem, decomposes tasks, profiles data, recommends models, compares full solution routes, generates formulas and Python code, executes code in a controlled workspace, repairs failures, analyzes results, plans figures, reflects on quality, and writes a paper draft.

### Features

- Supports `txt`, `pdf`, `docx`, `csv`, and `xlsx` inputs.
- Streamlit workbench for uploading a problem file and multiple data files.
- Model Zoo for prediction, optimization, evaluation, classification, network, and simulation methods.
- Paper Pattern Library for mathematical modeling paper structures.
- Data Profiler for schema, missing values, correlations, and visualization suggestions.
- Figure Planner, Formula Agent, Solution Competition, and Reflection Loop.
- Generates code, figures, Markdown reports, and optional Word / PDF exports.
- Generated code executes only under `outputs/code_workspace/`.

### Install

Python 3.11 is recommended.

```bash
pip install -r requirements.txt
```

### Configure DeepSeek

If `DEEPSEEK_API_KEY` is missing, both CLI and UI fail with a clear error and do not fall back to mock.

macOS / Linux:

```bash
export DEEPSEEK_API_KEY="your DeepSeek API key"
export DEEPSEEK_MODEL="deepseek-v4-flash"
export DEEPSEEK_BASE_URL="https://api.deepseek.com"
```

Windows PowerShell:

```powershell
$env:DEEPSEEK_API_KEY="your DeepSeek API key"
$env:DEEPSEEK_MODEL="deepseek-v4-flash"
$env:DEEPSEEK_BASE_URL="https://api.deepseek.com"
```

### CLI

Run with a data directory:

```bash
python main.py --problem path/to/problem.pdf --data path/to/data_dir --export-docx
```

Run without data files:

```bash
python main.py --problem path/to/problem.pdf --export-docx
```

Use RAG:

```bash
python main.py --problem path/to/problem.pdf --data path/to/data_dir --use-rag
```

Build the local knowledge base:

```bash
python main.py --build-kb knowledge_base/
```

Run benchmark:

```bash
python main.py --benchmark benchmark/benchmark_config.yaml
```

### Streamlit Workbench

```bash
streamlit run app.py
```

If needed:

```bash
python -m streamlit run app.py --server.port 8504
```

The UI accepts uploaded problem and data files only. A problem file is required; data files are optional.

### RAG

Knowledge base directories:

- `knowledge_base/problems/`
- `knowledge_base/methods/`
- `knowledge_base/paper_templates/`
- `knowledge_base/notes/`

Supported files: `txt`, `md`, `pdf`, `docx`.

### Benchmark

Config:

```text
benchmark/benchmark_config.yaml
```

Outputs:

- `benchmark/results/{task_id}/`
- `benchmark/results/summary.csv`
- `benchmark/results/benchmark_report.md`

### Outputs

- `outputs/logs/`: JSON logs, LLM calls, safety checks, execution attempts, RAG retrievals.
- `outputs/code/`: generated Python code and result files.
- `outputs/code_workspace/`: controlled execution workspace.
- `outputs/figures/`: generated figures.
- `outputs/figures/data_profile/`: data profiling figures.
- `outputs/reports/solution_report.md`: Markdown report.
- `outputs/reports/solution_report.docx`: optional Word export.
- `outputs/reports/solution_report.pdf`: optional PDF export.

### Tests

```bash
python -m pytest
```

The low-level mock client remains available for tests, but the production CLI and Streamlit UI no longer expose mock mode.
