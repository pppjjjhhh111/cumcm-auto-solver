from src.rag.chunker import chunk_text


def test_markdown_chunker_preserves_title_path() -> None:
    text = """
# 熵权法
熵权法适用于综合评价。
## 适用问题
可用于指标权重计算和综合评分。
### 注意事项
需要先做数据标准化。
"""

    chunks = chunk_text(text, chunk_size=200)

    assert chunks
    assert chunks[0]["metadata"]["title_path"] == ["熵权法"]
    assert any(chunk["metadata"]["title_path"] == ["熵权法", "适用问题"] for chunk in chunks)
    assert any(chunk["metadata"]["title_path"] == ["熵权法", "适用问题", "注意事项"] for chunk in chunks)


def test_markdown_chunker_splits_long_sections_with_metadata() -> None:
    text = "# 线性规划\n" + "约束条件和目标函数。" * 120

    chunks = chunk_text(text, chunk_size=120, overlap=20)

    assert len(chunks) > 1
    assert all(chunk["metadata"]["title"] == "线性规划" for chunk in chunks)
    assert [chunk["metadata"]["chunk_index"] for chunk in chunks] == list(range(len(chunks)))
