from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from src.tools.code_safety_checker import CodeSafetyChecker
from src.utils.json_utils import write_json
from src.utils.path_utils import is_relative_to


class PythonExecutor:
    """Execute generated Python code inside outputs/code_workspace."""

    def __init__(
        self,
        project_root: Path,
        code_dir: Path,
        workspace_dir: Path | None = None,
        timeout_seconds: int = 120,
        logs_dir: Path | None = None,
        figures_dir: Path | None = None,
    ) -> None:
        self.project_root = project_root.resolve()
        self.code_dir = code_dir.resolve()
        self.workspace_dir = (workspace_dir or self.code_dir.parent / "code_workspace").resolve()
        self.timeout_seconds = timeout_seconds
        self.logs_dir = logs_dir.resolve() if logs_dir is not None else None
        self.figures_dir = (figures_dir or self.code_dir.parent / "figures").resolve()
        self.safety_checker = CodeSafetyChecker(self.project_root)
        self.code_dir.mkdir(parents=True, exist_ok=True)
        self.workspace_dir.mkdir(parents=True, exist_ok=True)
        self.figures_dir.mkdir(parents=True, exist_ok=True)
        if not is_relative_to(self.code_dir, self.project_root):
            raise ValueError(f"code_dir must be inside project_root: {self.code_dir}")
        if not is_relative_to(self.workspace_dir, self.project_root):
            raise ValueError(f"workspace_dir must be inside project_root: {self.workspace_dir}")
        if not is_relative_to(self.figures_dir, self.project_root):
            raise ValueError(f"figures_dir must be inside project_root: {self.figures_dir}")

    def write_code(self, filename: str, code: str) -> Path:
        path = (self.code_dir / filename).resolve()
        if not is_relative_to(path, self.code_dir):
            raise ValueError(f"Refusing to write code outside code_dir: {path}")
        path.write_text(code, encoding="utf-8")
        return path

    def execute(self, code_file: Path) -> dict[str, Any]:
        code_file = code_file.resolve()
        if not is_relative_to(code_file, self.code_dir):
            return self._failed_result(code_file, f"Refusing to execute source outside code_dir: {code_file}")

        code = code_file.read_text(encoding="utf-8")
        safety_result = self.safety_checker.check_code(code)
        self._log_safety(code_file, safety_result)
        if not safety_result.get("is_safe"):
            reasons = safety_result.get("blocked_reasons", [])
            return self._failed_result(
                code_file,
                "Safety check failed. " + "; ".join(str(reason) for reason in reasons),
                safety_result=safety_result,
            )

        workspace_file = (self.workspace_dir / code_file.name).resolve()
        if not is_relative_to(workspace_file, self.workspace_dir):
            return self._failed_result(code_file, f"Refusing workspace path outside code_workspace: {workspace_file}")
        workspace_file.write_text(code, encoding="utf-8")

        before = self._list_outputs()
        env = os.environ.copy()
        env["PYTHONUTF8"] = "1"
        env["MPLBACKEND"] = "Agg"
        env["CUMCM_PROJECT_ROOT"] = str(self.project_root)
        env["CUMCM_CODE_OUTPUT_DIR"] = str(self.code_dir)
        env["CUMCM_CODE_WORKSPACE_DIR"] = str(self.workspace_dir)
        env["CUMCM_FIGURES_DIR"] = str(self.figures_dir)

        try:
            completed = subprocess.run(
                [sys.executable, workspace_file.name],
                cwd=self.workspace_dir,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
                env=env,
                check=False,
            )
            after = self._list_outputs()
            return {
                "success": completed.returncode == 0,
                "returncode": completed.returncode,
                "stdout": completed.stdout,
                "stderr": completed.stderr,
                "code_file": str(code_file),
                "workspace_code_file": str(workspace_file),
                "execution_cwd": str(self.workspace_dir),
                "generated_files": sorted(after - before),
                "all_output_files": sorted(after),
                "safety": safety_result,
            }
        except subprocess.TimeoutExpired as exc:
            return {
                "success": False,
                "returncode": None,
                "stdout": exc.stdout or "",
                "stderr": f"TimeoutExpired: execution exceeded {self.timeout_seconds}s",
                "code_file": str(code_file),
                "workspace_code_file": str(workspace_file),
                "execution_cwd": str(self.workspace_dir),
                "generated_files": [],
                "safety": safety_result,
            }

    def _failed_result(
        self,
        code_file: Path,
        stderr: str,
        safety_result: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return {
            "success": False,
            "returncode": None,
            "stdout": "",
            "stderr": stderr,
            "code_file": str(code_file),
            "workspace_code_file": "",
            "execution_cwd": str(self.workspace_dir),
            "generated_files": [],
            "safety": safety_result or {},
        }

    def _list_outputs(self) -> set[str]:
        output_root = self.code_dir.parent
        if not output_root.exists():
            return set()
        return {str(p.resolve()) for p in output_root.rglob("*") if p.is_file()}

    def _log_safety(self, code_file: Path, safety_result: dict[str, Any]) -> None:
        if self.logs_dir is None:
            return
        write_json(
            self.logs_dir / "code_safety.json",
            {
                "code_file": str(code_file),
                "workspace_dir": str(self.workspace_dir),
                **safety_result,
            },
        )
