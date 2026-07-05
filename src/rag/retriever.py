from __future__ import annotations

from pathlib import Path
from typing import Any

from src.rag.vector_store import KeywordVectorStore
from src.utils.json_utils import write_json


class Retriever:
    def __init__(self, kb_dir: Path, logs_dir: Path | None = None) -> None:
        self.store = KeywordVectorStore(kb_dir)
        self.logs_dir = logs_dir
        if self.store.index_path.exists():
            self.store.load_index()
        else:
            self.store.build_index()

    def retrieve(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        results = self.store.retrieve(query, top_k=top_k)
        if self.logs_dir is not None:
            write_json(
                self.logs_dir / "rag_retrievals.json",
                {"query": query, "top_k": top_k, "results": results},
            )
        return results
