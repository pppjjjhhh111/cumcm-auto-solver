from __future__ import annotations

from pathlib import Path


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def ensure_output_tree(output_dir: Path) -> dict[str, Path]:
    dirs = {
        "output_dir": output_dir,
        "code_dir": output_dir / "code",
        "code_workspace_dir": output_dir / "code_workspace",
        "figures_dir": output_dir / "figures",
        "logs_dir": output_dir / "logs",
        "reports_dir": output_dir / "reports",
    }
    for path in dirs.values():
        ensure_dir(path)
    return dirs


def is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False
