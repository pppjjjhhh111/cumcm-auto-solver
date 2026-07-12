from __future__ import annotations

import re
from typing import Any


HEADING_PATTERN = re.compile(r"^(#{1,3})\s+(.+?)\s*$")


def chunk_text(text: str, chunk_size: int = 900, overlap: int = 120) -> list[dict[str, Any]]:
    """Split text into Markdown-aware chunks with section metadata."""
    normalized = "\n".join(line.strip() for line in text.splitlines() if line.strip())
    if not normalized:
        return []
    sections = _markdown_sections(normalized)
    chunks: list[dict[str, Any]] = []
    for section in sections:
        for split_text in _split_long_text(section["text"], chunk_size=chunk_size, overlap=overlap):
            metadata = {
                "title": section.get("title", ""),
                "section": section.get("section", ""),
                "title_path": section.get("title_path", []),
                "chunk_index": len(chunks),
            }
            chunks.append({"text": split_text, "metadata": metadata})
    return chunks


def _markdown_sections(text: str) -> list[dict[str, Any]]:
    sections: list[dict[str, Any]] = []
    title_path: list[str] = []
    current_lines: list[str] = []
    current_title = ""
    current_path: list[str] = []

    def flush() -> None:
        if not current_lines:
            return
        section_text = "\n".join(current_lines).strip()
        if not section_text:
            return
        sections.append(
            {
                "title": current_title,
                "section": " / ".join(current_path),
                "title_path": list(current_path),
                "text": section_text,
            }
        )

    for line in text.splitlines():
        match = HEADING_PATTERN.match(line)
        if match:
            flush()
            level = len(match.group(1))
            title = match.group(2).strip()
            title_path = title_path[: level - 1]
            title_path.append(title)
            current_title = title
            current_path = list(title_path)
            current_lines = [line]
            continue
        current_lines.append(line)

    flush()
    return sections or [{"title": "", "section": "", "title_path": [], "text": text}]


def _split_long_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    if len(text) <= chunk_size:
        return [text]
    chunks = []
    start = 0
    while start < len(text):
        end = min(len(text), start + chunk_size)
        chunks.append(text[start:end].strip())
        if end == len(text):
            break
        start = max(0, end - overlap)
    return [chunk for chunk in chunks if chunk]
