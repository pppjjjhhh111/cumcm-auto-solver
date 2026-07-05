from __future__ import annotations

import math
import re
from collections import Counter
from pathlib import Path
from typing import Any

from src.rag.ingest import ingest_documents
from src.utils.json_utils import read_json, write_json


class KeywordVectorStore:
    """Small local keyword/BM25-style store with JSON persistence."""

    def __init__(self, kb_dir: Path, index_path: Path | None = None) -> None:
        self.kb_dir = kb_dir.resolve()
        self.index_path = index_path or self.kb_dir / "index.json"
        self.documents: list[dict[str, Any]] = []
        self.doc_freq: dict[str, int] = {}

    def ingest_documents(self, input_dir: Path | None = None) -> list[dict[str, Any]]:
        self.documents = ingest_documents(input_dir or self.kb_dir)
        self._rebuild_doc_freq()
        return self.documents

    def build_index(self) -> dict[str, Any]:
        if not self.documents:
            self.ingest_documents(self.kb_dir)
        self._rebuild_doc_freq()
        return {"document_count": len(self.documents), "term_count": len(self.doc_freq)}

    def retrieve(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        if not self.documents:
            if self.index_path.exists():
                self.load_index()
            else:
                self.build_index()
        terms = self._tokens(query)
        scored = []
        for document in self.documents:
            doc_terms = self._tokens(document.get("text", ""))
            tf = Counter(doc_terms)
            score = 0.0
            for term in terms:
                if not tf.get(term):
                    continue
                idf = math.log((1 + len(self.documents)) / (1 + self.doc_freq.get(term, 0))) + 1
                score += tf[term] * idf
            if score > 0:
                scored.append((score, document))
        scored.sort(key=lambda item: (-item[0], item[1].get("relative_path", "")))
        return [
            {
                "score": score,
                "source_path": item.get("source_path"),
                "relative_path": item.get("relative_path"),
                "chunk_id": item.get("chunk_id"),
                "text_preview": item.get("text", "")[:500],
                "metadata": item.get("metadata", {}),
            }
            for score, item in scored[:top_k]
        ]

    def save_index(self) -> Path:
        payload = {"kb_dir": str(self.kb_dir), "documents": self.documents, "doc_freq": self.doc_freq}
        write_json(self.index_path, payload)
        return self.index_path

    def load_index(self) -> dict[str, Any]:
        payload = read_json(self.index_path)
        self.documents = payload.get("documents", [])
        self.doc_freq = payload.get("doc_freq", {})
        return {"document_count": len(self.documents), "term_count": len(self.doc_freq)}

    def _rebuild_doc_freq(self) -> None:
        doc_freq: Counter[str] = Counter()
        for document in self.documents:
            doc_freq.update(set(self._tokens(document.get("text", ""))))
        self.doc_freq = dict(doc_freq)

    def _tokens(self, text: str) -> list[str]:
        ascii_terms = re.findall(r"[A-Za-z0-9_]{2,}", text.lower())
        cjk_terms = re.findall(r"[\u4e00-\u9fff]{2,}", text)
        return ascii_terms + cjk_terms
