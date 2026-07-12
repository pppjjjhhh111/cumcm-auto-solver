from __future__ import annotations

from pathlib import Path
from typing import Any

from src.rag.chunker import chunk_text


SUPPORTED_EXTENSIONS = {".txt", ".md", ".pdf", ".docx"}


def ingest_documents(input_dir: Path) -> list[dict[str, Any]]:
    input_dir = input_dir.resolve()
    documents = []
    if not input_dir.exists():
        return documents
    files = sorted(path for path in input_dir.rglob("*") if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS)
    for file_path in files:
        text = _read_document(file_path)
        relative_path = file_path.relative_to(input_dir).as_posix()
        category = _category_from_path(relative_path)
        purpose = _purpose_from_path(relative_path)
        for idx, chunk in enumerate(chunk_text(text)):
            metadata = {
                "extension": file_path.suffix.lower(),
                "chunk_index": idx,
                "category_from_path": category,
                "purpose_from_path": purpose,
            }
            if isinstance(chunk, dict):
                chunk_text_value = chunk.get("text", "")
                metadata.update(chunk.get("metadata", {}))
            else:
                chunk_text_value = str(chunk)
            documents.append(
                {
                    "chunk_id": f"{relative_path}::{idx}",
                    "source_path": str(file_path),
                    "relative_path": relative_path,
                    "text": chunk_text_value,
                    "metadata": metadata,
                }
            )
    return documents


def _category_from_path(relative_path: str) -> str:
    parts = [part.lower() for part in Path(relative_path).parts]
    if not parts:
        return "general"
    if parts[0] == "methods":
        return parts[1] if len(parts) > 1 else "method"
    if parts[0] == "paper_templates":
        return "paper_template"
    if parts[0] == "code_patterns":
        return "code_pattern"
    if parts[0] == "notes":
        return "note"
    if parts[0] == "problems":
        return "problem_pattern"
    return parts[0]


def _purpose_from_path(relative_path: str) -> str:
    parts = [part.lower() for part in Path(relative_path).parts]
    if not parts:
        return "general"
    mapping = {
        "methods": "method",
        "paper_templates": "paper",
        "code_patterns": "code",
        "notes": "note",
        "problems": "problem",
    }
    return mapping.get(parts[0], "general")


def _read_document(file_path: Path) -> str:
    suffix = file_path.suffix.lower()
    if suffix in {".txt", ".md"}:
        return _read_text(file_path)
    if suffix == ".docx":
        try:
            from docx import Document
        except ImportError:
            return ""
        document = Document(file_path)
        return "\n".join(p.text for p in document.paragraphs if p.text.strip())
    if suffix == ".pdf":
        try:
            from pypdf import PdfReader
        except ImportError:
            return ""
        reader = PdfReader(str(file_path))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    return ""


def _read_text(file_path: Path) -> str:
    for encoding in ("utf-8", "utf-8-sig", "gb18030"):
        try:
            return file_path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    return file_path.read_text(errors="replace")
