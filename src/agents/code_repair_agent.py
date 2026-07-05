from __future__ import annotations

import re
from typing import Any

from src.agents.base import BaseAgent


class CodeRepairAgent(BaseAgent):
    """Deterministic repair rules for generated Python code."""

    name = "CodeRepairAgent"

    def run(
        self,
        original_code: str,
        stderr: str,
        stdout: str = "",
        execution_context: dict[str, Any] | None = None,
        available_data_files: list[str] | None = None,
        previous_repair_attempts: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        execution_context = execution_context or {}
        available_data_files = available_data_files or []
        previous_repair_attempts = previous_repair_attempts or []
        repaired_code = original_code
        changed_lines: list[str] = []
        explanation_parts: list[str] = []
        confidence = 0.2

        if "NameError" in stderr and "name 'prnt' is not defined" in stderr:
            repaired_code = repaired_code.replace("prnt(", "print(")
            changed_lines.append("Replaced prnt(...) with print(...).")
            explanation_parts.append("Fixed misspelled print function.")
            confidence = 0.9

        if "UnicodeDecodeError" in stderr and 'encoding="utf-8-sig"' in repaired_code:
            repaired_code = repaired_code.replace('encoding="utf-8-sig"', 'encoding="gb18030", errors="replace"')
            changed_lines.append("Changed CSV encoding from utf-8-sig to gb18030 with replacement.")
            explanation_parts.append("Handled possible Chinese CSV encoding mismatch.")
            confidence = max(confidence, 0.75)

        missing_import = self._missing_name(stderr)
        if missing_import:
            import_line = self._import_for_name(missing_import)
            if import_line and import_line not in repaired_code:
                repaired_code = import_line + "\n" + repaired_code
                changed_lines.append(f"Added missing import: {import_line}")
                explanation_parts.append(f"Resolved missing name: {missing_import}.")
                confidence = max(confidence, 0.65)

        if "FileNotFoundError" in stderr and available_data_files:
            explanation_parts.append(
                "FileNotFoundError detected; available data files were provided for manual path correction."
            )
            changed_lines.append("No deterministic file path rewrite was applied.")

        if "Safety check failed" in stderr:
            repaired, safety_changes = self._repair_safety_violations(repaired_code)
            if repaired != repaired_code:
                repaired_code = repaired
                changed_lines.extend(safety_changes)
                explanation_parts.append("Removed or neutralized lines that violated generated-code safety rules.")
                confidence = max(confidence, 0.55)
            else:
                explanation_parts.append("Executor reported a safety violation; no deterministic unsafe-line rewrite matched.")
                changed_lines.append("No change applied because the generated code violated safety rules.")
                confidence = min(confidence, 0.2)

        if repaired_code == original_code and not explanation_parts:
            explanation_parts.append("No deterministic repair rule matched the execution error.")
            changed_lines.append("No code changes were applied.")

        return {
            "agent": self.name,
            "llm_trace": self.llm_client.complete_json(
                "code_repair",
                {
                    "stderr": stderr[:1000],
                    "stdout": stdout[:1000],
                    "execution_context": execution_context,
                    "available_data_file_count": len(available_data_files),
                    "previous_repair_count": len(previous_repair_attempts),
                },
            ),
            "repaired_code": repaired_code,
            "repair_explanation": " ".join(explanation_parts),
            "changed_lines_summary": changed_lines,
            "confidence_score": confidence,
            "changed": repaired_code != original_code,
            "execution_context": execution_context,
        }

    def _missing_name(self, stderr: str) -> str | None:
        match = re.search(r"NameError: name '([^']+)' is not defined", stderr)
        return match.group(1) if match else None

    def _import_for_name(self, name: str) -> str | None:
        imports = {
            "pd": "import pandas as pd",
            "np": "import numpy as np",
            "plt": "import matplotlib.pyplot as plt",
            "json": "import json",
            "csv": "import csv",
            "Path": "from pathlib import Path",
            "math": "import math",
            "statistics": "import statistics",
        }
        return imports.get(name)

    def _repair_safety_violations(self, code: str) -> tuple[str, list[str]]:
        dangerous_markers = [
            "subprocess",
            "socket",
            "requests",
            "shutil.rmtree",
            "os.remove",
            "os.unlink",
            "os.rmdir",
            "os.system",
            "os.popen",
            ".unlink(",
            ".rmdir(",
            "Path.home(",
            "expanduser(",
            "pip install",
            "shell=True",
            "C:/",
            "C:\\",
            "/Users",
            "/home",
        ]
        changed = []
        repaired_lines = []
        for line in code.splitlines():
            if any(marker in line for marker in dangerous_markers):
                repaired_lines.append(f"# SAFETY_REMOVED: {line}")
                changed.append(f"Commented unsafe line: {line.strip()[:120]}")
            else:
                repaired_lines.append(line)
        repaired = "\n".join(repaired_lines)
        if code.endswith("\n"):
            repaired += "\n"
        return repaired, changed
