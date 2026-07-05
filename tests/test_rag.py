from pathlib import Path
from uuid import uuid4

from src.rag.vector_store import KeywordVectorStore


def test_rag_builds_index_and_retrieves() -> None:
    root = Path(__file__).resolve().parents[1]
    kb_dir = root / "outputs" / "test_runs" / f"kb_{uuid4().hex}"
    methods = kb_dir / "methods"
    methods.mkdir(parents=True, exist_ok=True)
    (methods / "note.md").write_text("Regression and TOPSIS are useful modeling methods.", encoding="utf-8")

    store = KeywordVectorStore(kb_dir)
    summary = store.build_index()
    store.save_index()
    results = store.retrieve("regression TOPSIS", top_k=2)

    assert summary["document_count"] == 1
    assert (kb_dir / "index.json").exists()
    assert results
    assert "note.md" in results[0]["relative_path"]
