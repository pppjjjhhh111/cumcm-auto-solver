# cumcm-auto-solver

`cumcm-auto-solver` is a local research prototype for replaying historical or synthetic mathematical modeling problems. It is intended for offline experiments, teaching, and reproducibility work, not for active live competitions.

The project reads a problem statement and data files, decomposes the task, profiles data, recommends models from a model zoo, compares multiple full solution routes, generates formulas and code, executes the code in a controlled workspace, repairs failures, analyzes outputs, plans figures, reflects on report quality, and writes a Markdown paper draft.

## Install

Python 3.11 is recommended.

```bash
pip install -r requirements.txt
```

## Command Line

Run the included sample problem:

```bash
python main.py --problem examples/sample_problem/problem.txt --data examples/sample_problem/data
```

Run and export Word:

```bash
python main.py --problem examples/sample_problem/problem.txt --data examples/sample_problem/data --export-docx
```

Try PDF export too:

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

## Streamlit Workbench

```bash
streamlit run app.py
```

The web page is a Streamlit workbench for running and inspecting the solver without changing the command-line workflow. It supports problem/data upload, RAG toggle, Reflection Loop toggle, LLM provider selection, Word/PDF export options, run status, report/code/figure/log downloads, and a dashboard that can also read existing results from `outputs/logs/solver_state.json`.

Main tabs:

- `总览 Dashboard`: workflow progress, key metrics, latest route, report status.
- `题目解析`: background summary, questions, keywords, raw parsed JSON.
- `数据画像`: table shapes, missing values, preprocessing suggestions, EDA figures.
- `建模策略`: Model Zoo candidates, selected model cards, RAG references.
- `方案比较`: conservative, advanced, and hybrid solution comparison.
- `公式与图表`: symbol table, LaTeX formulas, figure plan, generated figures.
- `代码执行`: execution attempts, repair records, stdout/stderr, code downloads.
- `反思与修订`: reflection scores, detected issues, suggested fixes.
- `论文报告`: Markdown preview plus report downloads.
- `运行日志`: selectable JSON/JSONL log viewer.

If a log, figure, or report has not been generated yet, the UI shows an empty state instead of crashing. The sidebar does not delete files automatically; output cleanup is intentionally left manual to protect generated artifacts.

## LLM Configuration

Mock mode works without API keys and is the default fallback.

Real providers are configured in `config/model_config.yaml`. API keys must be supplied through environment variables, not written into code or config.

Examples:

```bash
set DEEPSEEK_API_KEY=your_key_here
python main.py --llm deepseek --problem examples/sample_problem/problem.txt --data examples/sample_problem/data
```

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

All agents call the shared LLM interface. LLM call logs are saved to `outputs/logs/llm_calls.jsonl`.

## RAG Knowledge Base

Local knowledge files live under:

- `knowledge_base/problems/`
- `knowledge_base/methods/`
- `knowledge_base/paper_templates/`
- `knowledge_base/notes/`

Supported file types: `txt`, `md`, `pdf`, `docx`.

The first implementation uses deterministic keyword retrieval. Retrieved content is used only as method inspiration; generated reports should rewrite all text and avoid copying source passages.

RAG retrieval logs are saved to `outputs/logs/rag_retrievals.json`.

## Benchmark

Benchmark config lives at `benchmark/benchmark_config.yaml`.

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

Metrics include end-to-end success, code execution success, report completeness, question coverage, data usage, figure count, model alignment, repair iterations, and runtime.

## Safety Boundary

Generated Python code is saved to `outputs/code/` and executed only in `outputs/code_workspace/`.

Before execution, `CodeSafetyChecker` blocks:

- dangerous file deletion or directory deletion
- `subprocess`, shell commands, and `shell=True`
- network access through sockets or requests
- user home paths and project-external absolute paths
- environment variable mutation
- `pip install`

Unsafe code is not executed. The safety result is saved to `outputs/logs/code_safety.json` and passed to `CodeRepairAgent`.

Execution attempts are saved to `outputs/logs/execution_attempts.json`. Repair versions are saved as:

- `outputs/code/attempt_1.py`
- `outputs/code/attempt_2.py`
- `outputs/code/attempt_3.py`

## Output Directories

- `outputs/logs/`: JSON logs, LLM calls, safety checks, execution attempts, RAG retrievals.
- `outputs/code/`: generated Python code and result files.
- `outputs/code_workspace/`: controlled execution working directory.
- `outputs/figures/`: generated figures.
- `outputs/figures/data_profile/`: data profiling figures.
- `outputs/reports/solution_report.md`: Markdown report.
- `outputs/reports/solution_report.docx`: optional Word export.
- `outputs/reports/solution_report.pdf`: optional PDF export.

## Tests

```bash
python -m pytest
```

The test suite covers file loading, model zoo, paper patterns, data profiling, figure planning, formula generation, code repair, safety checks, RAG, benchmark evaluation, report export, LLM mock behavior, and workflow smoke execution.
