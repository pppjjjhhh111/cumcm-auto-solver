from __future__ import annotations

from pathlib import Path
from typing import Any

from src.core.llm_client import LLMClient
from src.utils.json_utils import write_json


class BaseAgent:
    name = "BaseAgent"

    def __init__(self, llm_client: LLMClient, logs_dir: Path | None = None) -> None:
        self.llm_client = llm_client
        self.logs_dir = logs_dir

    def save_log(self, payload: dict[str, Any], step: int | None = None) -> None:
        if self.logs_dir is None:
            return
        prefix = f"{step:03d}_" if step is not None else ""
        write_json(self.logs_dir / f"{prefix}{self.name}.json", payload)

