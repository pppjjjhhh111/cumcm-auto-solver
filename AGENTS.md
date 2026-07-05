# AGENTS.md

This repository is a research prototype for an automatic mathematical modeling solver agent.

The system is designed for offline experiments on historical or synthetic mathematical modeling problems. It should not be designed as a tool for cheating in live competitions.

Development principles:
1. Prefer modular, readable Python code.
2. Keep every agent independent and testable.
3. Use structured JSON-like dictionaries for agent outputs.
4. Save all intermediate artifacts.
5. Never execute generated code outside the project workspace.
6. Never delete user files.
7. Use clear error handling when required LLM configuration is unavailable.
8. Keep MockLLMClient available for unit tests and low-level compatibility only.
9. Real LLM integration should be implemented behind LLMClient.
10. Prioritize end-to-end runnable workflow over model sophistication.

Maintenance rules for every future change:
1. Read the current project structure and understand existing modules before modifying code. Do not rewrite the whole project.
2. Keep the basic run modes of `main.py` and `app.py` unchanged.
3. Implement only the requested feature in each change. Do not add unrelated functionality.
4. Keep all new modules modular, testable, and reusable.
5. Save all intermediate results to `outputs/logs`.
6. Save all automatically generated code to `outputs/code`.
7. Save all figures to `outputs/figures`.
8. Save all reports to `outputs/reports`.
9. Update `README.md` after adding a user-facing feature.
10. Add or update tests after adding core logic.
11. After each completed change, report:
    - Changed files
    - New capability
    - How to run
    - How to test

Main command:

```bash
python main.py --problem path/to/problem.pdf --data path/to/data_dir
```

Expected output:

```text
outputs/reports/solution_report.md
outputs/code/
outputs/figures/
outputs/logs/
```
