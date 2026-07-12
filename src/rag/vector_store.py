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

    PURPOSE_WEIGHTS = {
        "strategy": {"method": 1.45, "problem": 1.35},
        "formula": {"method": 1.65},
        "paper": {"paper": 1.8},
        "figure": {"note": 1.35, "code": 1.25},
        "code": {"code": 1.8},
        "validation": {"note": 1.35, "method": 1.35},
        "general": {},
    }

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

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        purpose: str | None = None,
        category: str | None = None,
    ) -> list[dict[str, Any]]:
        if not self.documents:
            if self.index_path.exists():
                self.load_index()
            else:
                self.build_index()
        terms = self._tokens(query)
        scored = []
        for document in self.documents:
            if category and document.get("metadata", {}).get("category_from_path") != category:
                continue
            doc_terms = self._tokens(self._document_search_text(document))
            tf = Counter(doc_terms)
            score = 0.0
            for term in terms:
                if not tf.get(term):
                    continue
                idf = math.log((1 + len(self.documents)) / (1 + self.doc_freq.get(term, 0))) + 1
                score += tf[term] * idf
            if score > 0:
                score *= self._purpose_weight(document, purpose)
                scored.append((score, document))
        scored.sort(key=lambda item: (-item[0], item[1].get("relative_path", "")))
        return [self._result_item(score, item, purpose) for score, item in scored[:top_k]]

    def save_index(self) -> Path:
        payload = {"kb_dir": str(self.kb_dir), "documents": self.documents, "doc_freq": self.doc_freq}
        write_json(self.index_path, payload)
        return self.index_path

    def load_index(self) -> dict[str, Any]:
        payload = read_json(self.index_path)
        self.documents = payload.get("documents", [])
        self._rebuild_doc_freq()
        return {"document_count": len(self.documents), "term_count": len(self.doc_freq)}

    def _rebuild_doc_freq(self) -> None:
        doc_freq: Counter[str] = Counter()
        for document in self.documents:
            doc_freq.update(set(self._tokens(self._document_search_text(document))))
        self.doc_freq = dict(doc_freq)

    def _tokens(self, text: str) -> list[str]:
        ascii_terms = re.findall(r"[A-Za-z][A-Za-z0-9_+-]*|[0-9]+(?:\.[0-9]+)?", text.lower())
        cjk_terms: list[str] = []
        for sequence in re.findall(r"[\u4e00-\u9fff]+", text):
            cjk_terms.extend(self._cjk_ngrams(sequence))
        return ascii_terms + cjk_terms

    def _cjk_ngrams(self, text: str) -> list[str]:
        tokens = []
        length = len(text)
        for n in (2, 3, 4):
            if length < n:
                continue
            tokens.extend(text[i : i + n] for i in range(0, length - n + 1))
        if 1 < length <= 8:
            tokens.append(text)
        return tokens

    def _document_search_text(self, document: dict[str, Any]) -> str:
        metadata = document.get("metadata", {})
        values = [
            document.get("text", ""),
            metadata.get("title", ""),
            metadata.get("section", ""),
            " ".join(metadata.get("title_path", []) or []),
            metadata.get("category_from_path", ""),
            metadata.get("purpose_from_path", ""),
            document.get("relative_path", ""),
        ]
        return " ".join(str(value) for value in values if value)

    def _purpose_weight(self, document: dict[str, Any], purpose: str | None) -> float:
        if not purpose:
            return 1.0
        purpose_key = purpose.lower()
        metadata = document.get("metadata", {})
        doc_purpose = str(metadata.get("purpose_from_path", "")).lower()
        category = str(metadata.get("category_from_path", "")).lower()
        weights = self.PURPOSE_WEIGHTS.get(purpose_key, {})
        if not weights:
            return 1.0
        return weights.get(doc_purpose, weights.get(category, 0.75))

    def _result_item(self, score: float, document: dict[str, Any], purpose: str | None) -> dict[str, Any]:
        metadata = document.get("metadata", {})
        text = document.get("text", "")
        return {
            "score": score,
            "source_path": document.get("source_path"),
            "relative_path": document.get("relative_path"),
            "chunk_id": document.get("chunk_id"),
            "text": text,
            "text_preview": text[:500],
            "metadata": metadata,
            "title": metadata.get("title", ""),
            "section": metadata.get("section", ""),
            "purpose": purpose or metadata.get("purpose_from_path", "general"),
            "category": metadata.get("category_from_path", "general"),
        }
