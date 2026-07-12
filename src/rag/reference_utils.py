from __future__ import annotations

from typing import Any


def select_references(
    retrieved_references: Any,
    purpose: str | None = None,
    question_id: str | None = None,
    limit: int = 5,
) -> list[dict[str, Any]]:
    """Return de-duplicated RAG references from old list or new structured dict format."""
    if not retrieved_references:
        return []
    if isinstance(retrieved_references, list):
        return _dedupe(retrieved_references)[:limit]
    if not isinstance(retrieved_references, dict):
        return []

    refs: list[dict[str, Any]] = []
    if question_id:
        refs.extend(retrieved_references.get("question_references", {}).get(question_id, []))
    if purpose:
        refs.extend(retrieved_references.get("purpose_references", {}).get(purpose, []))
    refs.extend(retrieved_references.get("global_references", []))
    return _dedupe(refs)[:limit]


def count_references(retrieved_references: Any) -> int:
    if isinstance(retrieved_references, list):
        return len(retrieved_references)
    if not isinstance(retrieved_references, dict):
        return 0
    total = len(retrieved_references.get("global_references", []))
    for values in retrieved_references.get("question_references", {}).values():
        total += len(values)
    for values in retrieved_references.get("purpose_references", {}).values():
        total += len(values)
    return total


def reference_summary(references: list[dict[str, Any]], limit: int = 3) -> str:
    parts = []
    for ref in references[:limit]:
        title = ref.get("title") or ref.get("section") or ref.get("relative_path") or "knowledge chunk"
        category = ref.get("category") or ref.get("metadata", {}).get("category_from_path") or "general"
        purpose = ref.get("purpose") or ref.get("metadata", {}).get("purpose_from_path") or "general"
        parts.append(f"{title} ({category}/{purpose})")
    return "; ".join(parts)


def _dedupe(references: list[Any]) -> list[dict[str, Any]]:
    result = []
    seen = set()
    for ref in references:
        if not isinstance(ref, dict):
            continue
        key = ref.get("chunk_id") or (ref.get("source_path"), ref.get("text_preview"))
        if key in seen:
            continue
        seen.add(key)
        result.append(ref)
    return result
