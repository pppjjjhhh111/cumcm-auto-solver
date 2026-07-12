from pathlib import Path
from uuid import uuid4

from src.rag.ingest import ingest_documents


def test_ingest_metadata_from_path_and_markdown_titles() -> None:
    root = Path(__file__).resolve().parents[1]
    kb_dir = root / "outputs" / "test_runs" / f"rag_metadata_{uuid4().hex}"
    method_file = kb_dir / "methods" / "evaluation" / "entropy.md"
    method_file.parent.mkdir(parents=True, exist_ok=True)
    method_file.write_text("# 熵权法\n## 适用问题\n综合评价和权重计算。", encoding="utf-8")

    documents = ingest_documents(kb_dir)
    doc = documents[0]
    metadata = doc["metadata"]

    assert doc["relative_path"] == "methods/evaluation/entropy.md"
    assert metadata["category_from_path"] == "evaluation"
    assert metadata["purpose_from_path"] == "method"
    assert metadata["title_path"] == ["熵权法"]
    assert metadata["title"] == "熵权法"


def test_ingest_metadata_for_templates_and_code_patterns() -> None:
    root = Path(__file__).resolve().parents[1]
    kb_dir = root / "outputs" / "test_runs" / f"rag_metadata_paths_{uuid4().hex}"
    paper_file = kb_dir / "paper_templates" / "prediction.md"
    code_file = kb_dir / "code_patterns" / "plotting.md"
    paper_file.parent.mkdir(parents=True, exist_ok=True)
    code_file.parent.mkdir(parents=True, exist_ok=True)
    paper_file.write_text("# 预测论文模板\n误差评价、预测结果和不确定性分析。", encoding="utf-8")
    code_file.write_text("# 画图代码套路\n折线图、残差图和灵敏度曲线。", encoding="utf-8")

    documents = ingest_documents(kb_dir)
    by_path = {doc["relative_path"]: doc for doc in documents}

    assert by_path["paper_templates/prediction.md"]["metadata"]["category_from_path"] == "paper_template"
    assert by_path["paper_templates/prediction.md"]["metadata"]["purpose_from_path"] == "paper"
    assert by_path["code_patterns/plotting.md"]["metadata"]["category_from_path"] == "code_pattern"
    assert by_path["code_patterns/plotting.md"]["metadata"]["purpose_from_path"] == "code"
