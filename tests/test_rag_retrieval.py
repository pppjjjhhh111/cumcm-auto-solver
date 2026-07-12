from pathlib import Path
from uuid import uuid4

from src.agents.strategy_generator import StrategyGeneratorAgent
from src.core.llm_client import MockLLMClient
from src.rag.retriever import Retriever
from src.rag.vector_store import KeywordVectorStore
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


def test_chinese_ngram_query_hits_chinese_knowledge_card() -> None:
    root = Path(__file__).resolve().parents[1]
    kb_dir = root / "outputs" / "test_runs" / f"rag_chinese_{uuid4().hex}"
    method_dir = kb_dir / "methods" / "evaluation"
    method_dir.mkdir(parents=True, exist_ok=True)
    (method_dir / "entropy.md").write_text(
        "# 熵权法\n熵权法适用于综合评价、指标权重计算和灵敏度分析。",
        encoding="utf-8",
    )

    store = KeywordVectorStore(kb_dir)
    store.build_index()

    assert store.retrieve("综合评价", top_k=1)
    assert store.retrieve("熵权法", top_k=1)
    assert store.retrieve("灵敏度分析", top_k=1)


def test_retrieve_purpose_biases_paper_templates_and_methods() -> None:
    root = Path(__file__).resolve().parents[1]
    kb_dir = root / "outputs" / "test_runs" / f"rag_purpose_{uuid4().hex}"
    paper_dir = kb_dir / "paper_templates"
    method_dir = kb_dir / "methods" / "prediction"
    paper_dir.mkdir(parents=True, exist_ok=True)
    method_dir.mkdir(parents=True, exist_ok=True)
    (paper_dir / "prediction.md").write_text("# 预测模板\n预测模型需要误差评价和结果分析。", encoding="utf-8")
    (method_dir / "arima.md").write_text("# ARIMA\n预测模型公式和时间序列建模步骤。", encoding="utf-8")

    store = KeywordVectorStore(kb_dir)
    store.build_index()
    paper_results = store.retrieve("预测模型 误差评价", top_k=2, purpose="paper")
    formula_results = store.retrieve("预测模型 公式", top_k=2, purpose="formula")

    assert paper_results[0]["category"] == "paper_template"
    assert formula_results[0]["category"] == "prediction"


def test_strategy_generator_accepts_list_and_structured_rag_references() -> None:
    task = {"tasks": [{"id": "Q1.1", "question_id": "Q1", "task_type": "prediction", "description": "预测趋势"}]}
    list_refs = [{"chunk_id": "a", "title": "ARIMA", "category": "prediction", "purpose": "strategy", "text_preview": "预测"}]
    dict_refs = {
        "global_references": [],
        "question_references": {"Q1": list_refs},
        "purpose_references": {"strategy": [{"chunk_id": "b", "title": "预测方法", "category": "prediction", "purpose": "strategy"}]},
    }
    agent = StrategyGeneratorAgent(MockLLMClient())

    list_result = agent.run(task, retrieved_references=list_refs)
    dict_result = agent.run(task, retrieved_references=dict_refs)

    assert list_result["strategies"][0]["candidates"][0]["retrieved_references"]
    assert dict_result["strategies"][0]["candidates"][0]["retrieved_references"]
    assert "知识库依据摘要" in dict_result["strategies"][0]["candidates"][0]["why_suitable"]
