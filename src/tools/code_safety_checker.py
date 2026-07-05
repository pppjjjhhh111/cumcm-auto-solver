from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Any

from src.utils.path_utils import is_relative_to


class CodeSafetyChecker:
    """Static safety gate for generated Python code."""

    BLOCKED_SUBSTRINGS = [
        "subprocess",
        "socket",
        "requests",
        "urllib.request",
        "http.client",
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
    ]

    def __init__(self, project_root: Path | None = None) -> None:
        self.project_root = project_root.resolve() if project_root is not None else None

    def check_code(self, code: str) -> dict[str, Any]:
        blocked_reasons: list[str] = []
        risky_lines: list[dict[str, Any]] = []

        for line_number, line in enumerate(code.splitlines(), start=1):
            normalized = line.replace(" ", "")
            lower = line.lower()
            for pattern in self.BLOCKED_SUBSTRINGS:
                if pattern.replace(" ", "").lower() in normalized.lower() or pattern.lower() in lower:
                    blocked_reasons.append(f"Blocked unsafe pattern: {pattern}")
                    risky_lines.append({"line": line_number, "content": line, "reason": pattern})
            if re.search(r"os\.environ\s*(\[|\.|=)", line) and ".get(" not in line:
                blocked_reasons.append("Blocked environment variable mutation.")
                risky_lines.append({"line": line_number, "content": line, "reason": "environment mutation"})

        try:
            tree = ast.parse(code)
        except SyntaxError:
            return {
                "is_safe": True,
                "blocked_reasons": [],
                "risky_lines": [],
                "suggested_fix": "Fix Python syntax before safety validation can inspect AST paths.",
            }

        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                reason = self._unsafe_call_reason(node)
                if reason:
                    blocked_reasons.append(reason)
                    risky_lines.append(
                        {
                            "line": getattr(node, "lineno", None),
                            "content": self._line_at(code, getattr(node, "lineno", 0)),
                            "reason": reason,
                        }
                    )
                open_reason = self._unsafe_open_reason(node)
                if open_reason:
                    blocked_reasons.append(open_reason)
                    risky_lines.append(
                        {
                            "line": getattr(node, "lineno", None),
                            "content": self._line_at(code, getattr(node, "lineno", 0)),
                            "reason": open_reason,
                        }
                    )
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                reason = self._unsafe_path_reason(node.value)
                if reason:
                    blocked_reasons.append(reason)
                    risky_lines.append(
                        {
                            "line": getattr(node, "lineno", None),
                            "content": self._line_at(code, getattr(node, "lineno", 0)),
                            "reason": reason,
                        }
                    )

        deduped_reasons = self._dedupe(blocked_reasons)
        return {
            "is_safe": not deduped_reasons,
            "blocked_reasons": deduped_reasons,
            "risky_lines": self._dedupe_risky_lines(risky_lines),
            "suggested_fix": (
                "Remove dangerous filesystem, shell, network, environment mutation, and external absolute path access."
                if deduped_reasons
                else "Code passed static safety checks."
            ),
        }

    def _unsafe_call_reason(self, node: ast.Call) -> str | None:
        name = self._call_name(node.func)
        if name in {
            "subprocess.run",
            "subprocess.Popen",
            "os.remove",
            "os.unlink",
            "os.rmdir",
            "os.system",
            "os.popen",
            "shutil.rmtree",
            "Path.home",
            "socket.socket",
            "requests.get",
            "requests.post",
            "requests.request",
        }:
            return f"Blocked unsafe call: {name}"
        for keyword in node.keywords:
            if keyword.arg == "shell" and isinstance(keyword.value, ast.Constant) and keyword.value.value is True:
                return "Blocked shell=True."
        return None

    def _unsafe_open_reason(self, node: ast.Call) -> str | None:
        name = self._call_name(node.func)
        if name not in {"open", "Path.open", "pathlib.Path.open"}:
            return None
        if not node.args:
            return None
        arg = node.args[0]
        if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
            reason = self._unsafe_path_reason(arg.value)
            if reason:
                return f"Blocked open access: {reason}"
        return None

    def _unsafe_path_reason(self, value: str) -> str | None:
        text = value.strip()
        if not text:
            return None
        normalized = text.replace("\\", "/")
        if normalized in {"/", "\\"}:
            return "Blocked root directory access."
        if normalized.startswith("/Users") or normalized.startswith("/home"):
            return "Blocked user-home path access."
        if re.match(r"^[A-Za-z]:/", normalized):
            try:
                candidate = Path(text).resolve()
            except OSError:
                return "Blocked Windows absolute path access."
            if self.project_root is not None and is_relative_to(candidate, self.project_root):
                return None
            return f"Absolute paths outside project_root are blocked: {text}"
        if Path(text).is_absolute():
            try:
                candidate = Path(text).resolve()
            except OSError:
                return f"Blocked absolute path access: {text}"
            if self.project_root is not None and is_relative_to(candidate, self.project_root):
                return None
            return f"Absolute paths outside project_root are blocked: {text}"
        return None

    def _call_name(self, node: ast.AST) -> str:
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            parent = self._call_name(node.value)
            return f"{parent}.{node.attr}" if parent else node.attr
        return ""

    def _line_at(self, code: str, line_number: int) -> str:
        if line_number <= 0:
            return ""
        lines = code.splitlines()
        return lines[line_number - 1] if line_number <= len(lines) else ""

    def _dedupe(self, values: list[str]) -> list[str]:
        result = []
        for value in values:
            if value not in result:
                result.append(value)
        return result

    def _dedupe_risky_lines(self, values: list[dict[str, Any]]) -> list[dict[str, Any]]:
        result = []
        seen = set()
        for item in values:
            key = (item.get("line"), item.get("reason"), item.get("content"))
            if key not in seen:
                seen.add(key)
                result.append(item)
        return result
