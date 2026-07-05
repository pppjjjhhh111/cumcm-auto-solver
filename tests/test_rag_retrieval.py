from pathlib import Path
from uuid import uuid4

from src.rag.retriever import Retriever
from src.utils.json_utils import read_json


def test_retriever_gracefully_logs_missing_knowledge_base() -> None:
    root = Path(__file__).resolve().parents[1]
    output_root = root / "outputs" / "test_runs" / f"rag_missing_{uuid4().hex}"
    logs_dir = output_root / "logs"
    missing_kb = output_root / "missing_knowledge_base"

    retriever = Retriever(missing_kb, logs_dir=logs_dir)
    results = retriever.retrieve("entropy TOPSIS prediction", top_k=3)
    payload = read_json(logs_dir / "rag_retrievals.json")

    assert results == []
    assert payload["status"] == "skipped"
    assert payload["warnings"]


def test_retriever_logs_no_matches_without_crashing() -> None:
    root = Path(__file__).resolve().parents[1]
    output_root = root / "outputs" / "test_runs" / f"rag_empty_{uuid4().hex}"
    kb_dir = output_root / "knowledge_base"
    logs_dir = output_root / "logs"
    kb_dir.mkdir(parents=True, exist_ok=True)

    retriever = Retriever(kb_dir, logs_dir=logs_dir)
    results = retriever.retrieve("entropy TOPSIS prediction", top_k=3)
    payload = read_json(logs_dir / "rag_retrievals.json")

    assert results == []
    assert payload["status"] == "skipped"
    assert payload["warnings"]
