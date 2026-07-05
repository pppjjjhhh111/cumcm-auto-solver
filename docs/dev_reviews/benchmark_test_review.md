# Benchmark/Test Review

## Findings

- The baseline benchmark path remains `benchmark/benchmark_config.yaml` and continues to exercise the minimal workflow.
- Quality-focused outputs now have first-class artifacts: `report_quality_check.json`, `consistency_check.json`, `result_sanity_check.json`, and `report_quality_summary.md`.
- Existing tests covered the MVP workflow, but did not previously assert quality gates, RAG graceful degradation, model selection trace persistence, or result sanity scoring.
- No runtime Agent Team architecture is needed for this improvement. The project should not add `src/team`, `src/team_agents`, `TeamOrchestrator`, or UI/CLI Agent Team modes.

## Recommended Minimal Changes

- Keep ordinary batch evaluation unchanged so `python main.py --benchmark benchmark/benchmark_config.yaml` remains stable.
- Add a separate quality benchmark config for quality-gate experiments instead of overloading the default config.
- Extend evaluator metrics with `report_quality_score`, `consistency_score`, and `result_sanity_score`.
- Keep all quality checks deterministic so they can run under `MockLLMClient` in tests.

## Suggested Tests

- `tests/test_report_quality_checker.py`: report sections, quality JSON, and summary Markdown.
- `tests/test_consistency_checker.py`: cross-artifact pass/fail behavior.
- `tests/test_rag_retrieval.py`: missing or empty knowledge base logs warnings and does not crash.
- `tests/test_model_selection_quality.py`: selection trace, added scoring dimensions, and trace file.
- `tests/test_result_sanity_check.py`: expected code outputs produce a passing sanity score.
- `tests/test_workflow_smoke.py`: end-to-end workflow writes all quality artifacts.

## Acceptance Commands

```bash
python -m compileall app.py main.py src tests
python -m pytest -q
python main.py --benchmark benchmark/benchmark_config.yaml
python main.py --benchmark benchmark/quality_config.yaml
```

DeepSeek-backed CLI/UI runs still require `DEEPSEEK_API_KEY`; tests should not depend on real API calls.
