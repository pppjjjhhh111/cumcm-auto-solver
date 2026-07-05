from pathlib import Path

from src.tools.file_loader import FileLoader


def test_file_loader_reads_sample_txt_and_csv() -> None:
    root = Path(__file__).resolve().parents[1]
    loader = FileLoader()

    problem = loader.load_problem(root / "examples" / "sample_problem" / "problem.txt")
    data = loader.load_data(root / "examples" / "sample_problem" / "data")

    assert "共享单车" in problem["content"]
    assert len(data) == 1
    assert data[0]["tables"][0]["columns"] == [
        "date",
        "temperature_c",
        "is_weekend",
        "bikes_available",
        "orders",
    ]

