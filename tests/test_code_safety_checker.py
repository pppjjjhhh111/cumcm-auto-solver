from pathlib import Path

from src.tools.code_safety_checker import CodeSafetyChecker


def test_code_safety_checker_blocks_dangerous_code() -> None:
    root = Path(__file__).resolve().parents[1]
    checker = CodeSafetyChecker(root)
    result = checker.check_code("import os\nos.remove('important.txt')\n")

    assert result["is_safe"] is False
    assert result["blocked_reasons"]


def test_code_safety_checker_allows_common_analysis_imports() -> None:
    root = Path(__file__).resolve().parents[1]
    checker = CodeSafetyChecker(root)
    code = "import pandas as pd\nimport matplotlib.pyplot as plt\nfrom sklearn.linear_model import LinearRegression\nprint('ok')\n"
    result = checker.check_code(code)

    assert result["is_safe"] is True
