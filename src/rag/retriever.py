from __future__ import annotations

from pathlib import Path
from typing import Any

from src.rag.vector_store import KeywordVectorStore
from src.utils.json_utils import write_json


class Retriever:
    def __init__(self, kb_dir: Path, logs_dir: Path | None = None) -> None:
        self.kb_dir = kb_dir.resolve()
        self.store = KeywordVectorStore(self.kb_dir)
        self.logs_dir = logs_dir
        self.warning: str | None = None
        try:
            if not self.kb_dir.exists():
                self.warning = f"Knowledge base directory does not exist: {self.kb_dir}"
                return
            if self.store.index_path.exists():
                self.store.load_index()
            else:
                self.store.build_index()
            if not self.store.documents:
                self.warning = f"Knowledge base contains no readable documents: {self.kb_dir}"
        except Exception as exc:  # pragma: no cover - defensive guard for optional RAG.
            self.warning = f"RAG index unavailable: {type(exc).__name__}: {exc}"

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        purpose: str | None = None,
        category: str | None = None,
    ) -> list[dict[str, Any]]:
        if self.warning:
            results: list[dict[str, Any]] = []
            payload = {
                "query": query,
                "top_k": top_k,
                "purpose": purpose,
                "category": category,
                "results": results,
                "warnings": [self.warning],
                "status": "skipped",
            }
            if self.logs_dir is not None:
                write_json(self.logs_dir / "rag_retrievals.json", payload)
            return results
        try:
            results = self.store.retrieve(query, top_k=top_k, purpose=purpose, category=category)
            warnings = [] if results else [f"No RAG matches found in {self.kb_dir}."]
            status = "ok" if results else "no_matches"
        except Exception as exc:  # pragma: no cover - defensive guard for optional RAG.
            results = []
            warnings = [f"RAG retrieval failed: {type(exc).__name__}: {exc}"]
            status = "error"
        if self.logs_dir is not None:
            write_json(
                self.logs_dir / "rag_retrievals.json",
                {
                    "query": query,
                    "top_k": top_k,
                    "purpose": purpose,
                    "category": category,
                    "results": results,
                    "warnings": warnings,
                    "status": status,
                },
            )
        return results
