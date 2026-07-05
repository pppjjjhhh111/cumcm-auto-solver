from __future__ import annotations

import html
import io
import json
import os
import re
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

import streamlit as st

from src.core.llm_client import (
    DeepSeekLLMClient,
    LocalHTTPLLMClient,
    MockLLMClient,
    OpenAICompatibleLLMClient,
)
from src.core.workflow import WorkflowRunner


PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_PROBLEM = PROJECT_ROOT / "examples" / "sample_problem" / "problem.txt"
DEFAULT_DATA = PROJECT_ROOT / "examples" / "sample_problem" / "data"
UPLOAD_ROOT = PROJECT_ROOT / "outputs" / "uploads"
OUTPUT_DIR = PROJECT_ROOT / "outputs"
LOGS_DIR = OUTPUT_DIR / "logs"
CODE_DIR = OUTPUT_DIR / "code"
FIGURES_DIR = OUTPUT_DIR / "figures"
REPORTS_DIR = OUTPUT_DIR / "reports"
SUPPORTED_FILES = ["pdf", "docx", "txt", "csv", "xlsx"]

WORKFLOW_STEPS = [
    ("文件读取", "file_loader", "Input"),
    ("题目解析", "parsed_problem", "Parse"),
    ("数据画像", "data_profile", "Profile"),
    ("策略生成", "candidate_strategies", "Model"),
    ("方案竞争", "solution_competition", "Compete"),
    ("公式生成", "formulas", "Formula"),
    ("图表规划", "figure_plan", "Figure"),
    ("代码执行", "execution_result", "Execute"),
    ("结果分析", "result_analysis", "Analyze"),
    ("反思修订", "reflection_report", "Reflect"),
    ("报告生成", "paper", "Report"),
]


st.set_page_config(
    page_title="数学建模 Auto-Solver Agent",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)


def inject_css() -> None:
    st.markdown(
        """
        <style>
        :root {
            --bg: #020617;
            --bg-2: #08111f;
            --panel: rgba(15, 23, 42, 0.72);
            --panel-strong: rgba(15, 23, 42, 0.88);
            --panel-soft: rgba(30, 41, 59, 0.56);
            --border: rgba(148, 163, 184, 0.18);
            --border-strong: rgba(34, 211, 238, 0.34);
            --text: #e5eefb;
            --muted: #94a3b8;
            --muted-2: #64748b;
            --cyan: #22d3ee;
            --cyan-soft: rgba(34, 211, 238, 0.12);
            --blue: #60a5fa;
            --violet: #a78bfa;
            --green: #34d399;
            --amber: #fbbf24;
            --red: #fb7185;
            --shadow: 0 18px 60px rgba(0, 0, 0, 0.28);
            --glow-cyan: 0 0 0 1px rgba(34, 211, 238, 0.38), 0 0 36px rgba(34, 211, 238, 0.18);
        }

        .stApp {
            background:
                radial-gradient(circle at 78% -8%, rgba(124, 58, 237, 0.28), transparent 32rem),
                radial-gradient(circle at 12% 4%, rgba(34, 211, 238, 0.18), transparent 28rem),
                linear-gradient(135deg, #020617 0%, #07111f 42%, #0f172a 100%);
            color: var(--text);
        }

        .stApp::before {
            content: "";
            position: fixed;
            inset: 0;
            pointer-events: none;
            z-index: 0;
            background-image:
                linear-gradient(rgba(148, 163, 184, 0.055) 1px, transparent 1px),
                linear-gradient(90deg, rgba(148, 163, 184, 0.055) 1px, transparent 1px);
            background-size: 42px 42px;
            mask-image: linear-gradient(to bottom, rgba(0,0,0,0.8), rgba(0,0,0,0.18) 54%, transparent);
        }

        .block-container {
            position: relative;
            z-index: 1;
            max-width: 1440px;
            padding-top: 1.85rem;
            padding-bottom: 3rem;
        }

        h1, h2, h3, h4, h5, h6, p, li, label, span, div {
            letter-spacing: 0;
        }

        [data-testid="stSidebar"] {
            background:
                linear-gradient(180deg, rgba(2, 6, 23, 0.94), rgba(15, 23, 42, 0.86)),
                radial-gradient(circle at 20% 0%, rgba(34, 211, 238, 0.11), transparent 18rem);
            border-right: 1px solid rgba(34, 211, 238, 0.18);
            box-shadow: 18px 0 54px rgba(0, 0, 0, 0.24);
        }

        [data-testid="stSidebar"] * {
            color: var(--text);
        }

        [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
        [data-testid="stSidebar"] .stCaptionContainer {
            color: var(--muted);
        }

        [data-testid="stSidebar"] section,
        [data-testid="stSidebar"] div[data-testid="stVerticalBlock"] {
            gap: 0.74rem;
        }

        .sidebar-title {
            margin: 0 0 12px;
            padding: 14px 14px 12px;
            border: 1px solid rgba(34, 211, 238, 0.22);
            border-radius: 8px;
            background: rgba(15, 23, 42, 0.62);
            box-shadow: var(--shadow);
        }

        .sidebar-title .kicker {
            color: var(--cyan);
            font-size: 11px;
            font-weight: 800;
            text-transform: uppercase;
        }

        .sidebar-title .title {
            color: #f8fafc;
            font-size: 19px;
            font-weight: 780;
            margin-top: 4px;
        }

        .sidebar-section {
            margin: 16px 0 8px;
            padding: 9px 11px;
            border: 1px solid rgba(148, 163, 184, 0.16);
            border-radius: 8px;
            background: rgba(15, 23, 42, 0.50);
            color: #cbd5e1;
            font-size: 12px;
            font-weight: 760;
            text-transform: uppercase;
        }

        div[data-testid="stButton"] > button,
        div[data-testid="stDownloadButton"] > button {
            border-radius: 8px;
            border: 1px solid rgba(148, 163, 184, 0.25);
            background: rgba(15, 23, 42, 0.72);
            color: #e2e8f0;
            box-shadow: none;
            font-weight: 700;
            transition: transform 160ms ease, border-color 160ms ease, box-shadow 160ms ease, background 160ms ease;
        }

        div[data-testid="stButton"] > button:hover,
        div[data-testid="stDownloadButton"] > button:hover {
            transform: translateY(-1px);
            border-color: rgba(34, 211, 238, 0.52);
            box-shadow: 0 0 30px rgba(34, 211, 238, 0.12);
            background: rgba(30, 41, 59, 0.88);
        }

        div[data-testid="stButton"] > button[kind="primary"] {
            border: 1px solid rgba(96, 165, 250, 0.72);
            background: linear-gradient(135deg, #2563eb, #7c3aed 55%, #0891b2);
            box-shadow: 0 0 36px rgba(96, 165, 250, 0.24);
        }

        .app-hero {
            position: relative;
            overflow: hidden;
            border: 1px solid rgba(148, 163, 184, 0.18);
            border-radius: 8px;
            background:
                linear-gradient(135deg, rgba(15, 23, 42, 0.84), rgba(2, 6, 23, 0.86)),
                radial-gradient(circle at 78% 20%, rgba(34, 211, 238, 0.18), transparent 20rem),
                radial-gradient(circle at 58% -20%, rgba(124, 58, 237, 0.22), transparent 24rem);
            box-shadow: var(--shadow);
            padding: 30px;
            margin-bottom: 18px;
        }

        .app-hero::before {
            content: "";
            position: absolute;
            inset: 0;
            pointer-events: none;
            background-image:
                linear-gradient(rgba(34, 211, 238, 0.07) 1px, transparent 1px),
                linear-gradient(90deg, rgba(34, 211, 238, 0.07) 1px, transparent 1px);
            background-size: 36px 36px;
            mask-image: linear-gradient(110deg, rgba(0,0,0,0.75), transparent 70%);
        }

        .hero-grid {
            position: relative;
            z-index: 1;
            display: grid;
            grid-template-columns: minmax(0, 1.35fr) minmax(320px, 0.65fr);
            gap: 24px;
            align-items: stretch;
        }

        .hero-kicker, .section-kicker {
            color: var(--cyan);
            font-size: 12px;
            font-weight: 800;
            letter-spacing: 0.08em;
            text-transform: uppercase;
        }

        .hero-title {
            color: #f8fafc;
            font-size: clamp(34px, 4vw, 54px);
            line-height: 1.04;
            font-weight: 820;
            margin: 9px 0 0;
        }

        .hero-subtitle {
            color: #cbd5e1;
            font-size: 17px;
            line-height: 1.62;
            max-width: 840px;
            margin-top: 14px;
        }

        .hero-description {
            color: #94a3b8;
            font-size: 13px;
            line-height: 1.62;
            margin-top: 8px;
        }

        .hero-orb {
            position: absolute;
            right: -80px;
            top: -90px;
            width: 260px;
            height: 260px;
            background: radial-gradient(circle, rgba(34, 211, 238, 0.22), transparent 65%);
            filter: blur(2px);
            opacity: 0.78;
        }

        .status-row {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 10px;
        }

        .status-card, .metric-card, .soft-card, .solution-card, .step-item, .glass-card, .terminal-card {
            border: 1px solid rgba(148, 163, 184, 0.18);
            border-radius: 8px;
            background: rgba(15, 23, 42, 0.72);
            backdrop-filter: blur(16px);
            box-shadow: var(--shadow);
        }

        .status-card {
            padding: 13px 14px;
        }

        .status-label {
            color: var(--muted);
            font-size: 11px;
            font-weight: 760;
            text-transform: uppercase;
        }

        .status-value {
            color: #f8fafc;
            font-size: 16px;
            font-weight: 780;
            margin-top: 5px;
        }

        .agent-pipeline {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin-top: 20px;
            align-items: center;
        }

        .pipeline-node {
            padding: 7px 10px;
            border-radius: 999px;
            border: 1px solid rgba(34, 211, 238, 0.24);
            background: rgba(8, 47, 73, 0.34);
            color: #dff9ff;
            font-size: 12px;
            font-weight: 760;
            box-shadow: 0 0 24px rgba(34, 211, 238, 0.08);
        }

        .pipeline-arrow {
            color: rgba(148, 163, 184, 0.72);
            font-size: 12px;
        }

        .metric-card, .soft-card, .solution-card {
            padding: 16px;
            height: 100%;
        }

        .metric-card {
            position: relative;
            min-height: 126px;
        }

        .metric-icon {
            position: absolute;
            top: 14px;
            right: 14px;
            min-width: 34px;
            height: 28px;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            border-radius: 8px;
            border: 1px solid rgba(34, 211, 238, 0.20);
            background: rgba(14, 165, 233, 0.10);
            color: var(--cyan);
            font-size: 11px;
            font-weight: 850;
        }

        .metric-label {
            color: #94a3b8;
            font-size: 12px;
            font-weight: 760;
            text-transform: uppercase;
        }

        .metric-value {
            color: #f8fafc;
            font-size: 30px;
            font-weight: 820;
            line-height: 1.1;
            margin-top: 11px;
            word-break: break-word;
        }

        .metric-caption {
            color: #94a3b8;
            font-size: 12px;
            line-height: 1.5;
            margin-top: 9px;
        }

        .section-title {
            color: #f8fafc;
            font-size: 22px;
            font-weight: 800;
            margin: 7px 0 4px;
        }

        .section-caption {
            color: var(--muted);
            font-size: 13px;
            margin: 0 0 14px;
        }

        .selected-card {
            border-color: rgba(34, 211, 238, 0.54);
            box-shadow: var(--glow-cyan), var(--shadow);
            background: linear-gradient(180deg, rgba(15, 23, 42, 0.86), rgba(8, 47, 73, 0.42));
        }

        .card-title {
            color: #f8fafc;
            font-size: 16px;
            font-weight: 790;
            line-height: 1.35;
            margin-bottom: 6px;
        }

        .card-text {
            color: #cbd5e1;
            font-size: 13px;
            line-height: 1.58;
        }

        .muted-line {
            color: var(--muted);
            font-size: 12px;
            line-height: 1.5;
        }

        .pill {
            display: inline-flex;
            align-items: center;
            border-radius: 999px;
            padding: 4px 9px;
            font-size: 11px;
            font-weight: 760;
            border: 1px solid rgba(148, 163, 184, 0.18);
            background: rgba(15, 23, 42, 0.82);
            color: #cbd5e1;
            margin: 0 6px 6px 0;
            white-space: nowrap;
            text-transform: uppercase;
        }

        .pill-ok {
            color: #bbf7d0;
            border-color: rgba(52, 211, 153, 0.45);
            background: rgba(6, 78, 59, 0.42);
            box-shadow: 0 0 18px rgba(52, 211, 153, 0.11);
        }

        .pill-info {
            color: #bae6fd;
            border-color: rgba(34, 211, 238, 0.45);
            background: rgba(8, 47, 73, 0.46);
            box-shadow: 0 0 18px rgba(34, 211, 238, 0.12);
        }

        .pill-warn {
            color: #fde68a;
            border-color: rgba(251, 191, 36, 0.46);
            background: rgba(113, 63, 18, 0.38);
        }

        .pill-danger {
            color: #fecdd3;
            border-color: rgba(251, 113, 133, 0.48);
            background: rgba(127, 29, 29, 0.38);
            box-shadow: 0 0 18px rgba(251, 113, 133, 0.10);
        }

        .step-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(132px, 1fr));
            gap: 9px;
            margin: 8px 0 18px;
        }

        .step-item {
            padding: 11px 12px;
            min-height: 64px;
        }

        .step-done {
            border-color: rgba(34, 211, 238, 0.42);
            box-shadow: 0 0 24px rgba(34, 211, 238, 0.11);
        }

        .step-pending {
            border-color: rgba(148, 163, 184, 0.14);
            background: rgba(15, 23, 42, 0.46);
        }

        .step-failed {
            border-color: rgba(251, 113, 133, 0.48);
            box-shadow: 0 0 24px rgba(251, 113, 133, 0.12);
        }

        .step-label {
            color: #e2e8f0;
            font-size: 13px;
            font-weight: 790;
        }

        .step-status {
            color: #94a3b8;
            font-size: 12px;
            margin-top: 5px;
        }

        .empty-state {
            border: 1px dashed rgba(34, 211, 238, 0.28);
            border-radius: 8px;
            background: rgba(15, 23, 42, 0.58);
            padding: 22px;
            color: #94a3b8;
            line-height: 1.65;
        }

        .empty-state strong {
            color: #e2e8f0;
        }

        .terminal-card {
            padding: 0;
            overflow: hidden;
            margin: 10px 0;
        }

        .terminal-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 10px 13px;
            border-bottom: 1px solid rgba(148, 163, 184, 0.14);
            background: rgba(2, 6, 23, 0.66);
            color: #cbd5e1;
            font-size: 12px;
            font-weight: 780;
        }

        .terminal-body {
            max-height: 340px;
            overflow: auto;
            padding: 13px;
            background: rgba(2, 6, 23, 0.82);
            color: #dbeafe;
            font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, "Liberation Mono", monospace;
            font-size: 12px;
            line-height: 1.55;
            white-space: pre-wrap;
            border-left: 3px solid rgba(34, 211, 238, 0.42);
        }

        .terminal-danger .terminal-body {
            border-left-color: rgba(251, 113, 133, 0.78);
            color: #fecdd3;
        }

        .terminal-ok .terminal-body {
            border-left-color: rgba(52, 211, 153, 0.78);
            color: #dcfce7;
        }

        .code-list {
            border: 1px solid rgba(148, 163, 184, 0.16);
            border-radius: 8px;
            background: rgba(2, 6, 23, 0.62);
            padding: 10px 12px;
            margin-bottom: 8px;
            color: #cbd5e1;
            font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, "Liberation Mono", monospace;
            font-size: 12px;
        }

        .mission-card {
            border: 1px solid rgba(34, 211, 238, 0.18);
            border-radius: 8px;
            background: linear-gradient(135deg, rgba(15, 23, 42, 0.80), rgba(30, 41, 59, 0.50));
            box-shadow: var(--shadow);
            padding: 18px;
            margin-top: 4px;
        }

        .mission-grid {
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 12px;
            margin-top: 12px;
        }

        .mission-item {
            border-left: 1px solid rgba(34, 211, 238, 0.28);
            padding-left: 12px;
        }

        .mission-label {
            color: var(--muted);
            font-size: 11px;
            font-weight: 760;
            text-transform: uppercase;
        }

        .mission-value {
            color: #f8fafc;
            font-size: 14px;
            font-weight: 760;
            margin-top: 4px;
            word-break: break-word;
        }

        .score-chip {
            position: absolute;
            top: 14px;
            right: 14px;
            min-width: 54px;
            padding: 7px 8px;
            border-radius: 8px;
            border: 1px solid rgba(34, 211, 238, 0.36);
            background: rgba(8, 47, 73, 0.58);
            color: #e0f2fe;
            text-align: center;
            box-shadow: 0 0 22px rgba(34, 211, 238, 0.12);
        }

        .score-chip .num {
            font-size: 21px;
            line-height: 1;
            font-weight: 850;
        }

        .score-chip .txt {
            color: var(--muted);
            font-size: 10px;
            text-transform: uppercase;
            margin-top: 3px;
        }

        .candidate-card {
            position: relative;
            padding-right: 82px;
        }

        .small-divider {
            height: 1px;
            background: linear-gradient(90deg, transparent, rgba(34, 211, 238, 0.28), transparent);
            margin: 18px 0;
        }

        div[data-testid="stTabs"] button {
            color: #94a3b8;
            font-weight: 720;
            border-bottom: 1px solid transparent;
        }

        div[data-testid="stTabs"] button[aria-selected="true"] {
            color: #e0f2fe;
            border-bottom-color: var(--cyan);
        }

        div[data-testid="stMetric"] {
            border: 1px solid rgba(148, 163, 184, 0.14);
            border-radius: 8px;
            background: rgba(15, 23, 42, 0.46);
            padding: 10px;
        }

        div[data-testid="stExpander"] {
            border: 1px solid rgba(148, 163, 184, 0.16);
            border-radius: 8px;
            background: rgba(15, 23, 42, 0.50);
        }

        code, pre {
            color: #dbeafe !important;
        }

        @media (max-width: 980px) {
            .hero-grid, .mission-grid {
                grid-template-columns: 1fr;
            }
            .status-row {
                grid-template-columns: 1fr;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def h(value: Any) -> str:
    return html.escape("" if value is None else str(value))


def sanitize_filename(name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "_", name.strip())
    return cleaned or "uploaded_file"


def resolve_project_path(path_text: str) -> Path:
    path = Path(path_text.strip())
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path.resolve()


def save_uploaded_file(uploaded_file: Any, target_dir: Path) -> Path:
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = (target_dir / sanitize_filename(uploaded_file.name)).resolve()
    target_path.write_bytes(uploaded_file.getbuffer())
    return target_path


def save_data_uploads(uploaded_files: Iterable[Any], target_dir: Path) -> Path | None:
    files = list(uploaded_files or [])
    if not files:
        return None
    target_dir.mkdir(parents=True, exist_ok=True)
    for uploaded_file in files:
        save_uploaded_file(uploaded_file, target_dir)
    return target_dir


def make_llm_client(provider: str):
    if provider == "mock":
        return MockLLMClient(), "mock"
    if provider == "deepseek":
        return DeepSeekLLMClient(), "deepseek"
    if provider == "openai-compatible":
        return OpenAICompatibleLLMClient(
            base_url=os.environ.get("OPENAI_BASE_URL", ""),
            api_key_env="OPENAI_API_KEY",
            model=os.environ.get("OPENAI_MODEL", ""),
        ), "openai-compatible"
    if provider == "local-http":
        return LocalHTTPLLMClient(
            base_url=os.environ.get("LOCAL_LLM_BASE_URL", "http://localhost:8000/v1"),
            model=os.environ.get("LOCAL_LLM_MODEL", ""),
        ), "local-http"
    if os.environ.get("DEEPSEEK_API_KEY"):
        return DeepSeekLLMClient(), "deepseek"
    return MockLLMClient(), "mock"


def read_text(path: Path, limit: int | None = None) -> str:
    if not path.exists() or not path.is_file():
        return ""
    text = path.read_text(encoding="utf-8", errors="replace")
    return text if limit is None else text[:limit]


def load_json(path: Path, default: Any | None = None) -> Any:
    fallback = {} if default is None else default
    if not path.exists() or not path.is_file():
        return fallback
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        st.warning(f"JSON 解析失败：{path.name} ({exc.msg})")
        return fallback


def make_zip(paths: list[Path]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in paths:
            if not path.exists():
                continue
            if path.is_file():
                archive.write(path, path.relative_to(PROJECT_ROOT))
            elif path.is_dir():
                for file_path in path.rglob("*"):
                    if file_path.is_file():
                        archive.write(file_path, file_path.relative_to(PROJECT_ROOT))
    return buffer.getvalue()


def latest_log(pattern: str) -> dict[str, Any]:
    matches = sorted(LOGS_DIR.glob(pattern))
    if not matches:
        return {}
    data = load_json(matches[-1], {})
    return data if isinstance(data, dict) else {}


def state_to_dict(state: Any) -> dict[str, Any]:
    if state is None:
        return {}
    if isinstance(state, dict):
        return state
    if hasattr(state, "to_json_dict"):
        return state.to_json_dict()
    return {}


def get_runtime_state() -> dict[str, Any]:
    state = state_to_dict(st.session_state.get("last_state"))
    if state:
        return state
    disk_state = load_json(LOGS_DIR / "solver_state.json", {})
    return disk_state if isinstance(disk_state, dict) else {}


def get_output_path(state: dict[str, Any], key: str, fallback: Path) -> Path:
    value = state.get(key)
    return Path(value).resolve() if value else fallback


def get_section(state: dict[str, Any], state_key: str, fallback_log: str | None = None) -> Any:
    value = state.get(state_key)
    if value not in (None, {}, []):
        return value
    if fallback_log:
        return load_json(LOGS_DIR / fallback_log, {})
    return {}


def as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if value is None:
        return []
    return [value]


def compact_number(value: Any) -> str:
    if isinstance(value, bool):
        return "是" if value else "否"
    if isinstance(value, (int, float)):
        if isinstance(value, float):
            return f"{value:.3g}"
        return str(value)
    if value in (None, "", []):
        return "-"
    return str(value)


def pill(label: Any, tone: str = "neutral") -> str:
    tone_class = {
        "ok": "pill-ok",
        "info": "pill-info",
        "warn": "pill-warn",
        "danger": "pill-danger",
    }.get(tone, "")
    return f'<span class="pill {tone_class}">{h(label)}</span>'


def render_status_badge(label: Any, tone: str = "neutral") -> str:
    return pill(label, tone)


def render_section_header(kicker: str, title: str, caption: str = "") -> None:
    st.markdown(
        f"""
        <div style="margin: 10px 0 16px;">
            <div class="section-kicker">{h(kicker)}</div>
            <div class="section-title">{h(title)}</div>
            <div class="section-caption">{h(caption)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_metric_card(label: str, value: Any, caption: str = "", icon: str = "AI") -> None:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-icon">{h(icon)}</div>
            <div class="metric-label">{h(label)}</div>
            <div class="metric-value">{h(compact_number(value))}</div>
            <div class="metric-caption">{h(caption)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_empty_state(title: str, body: str) -> None:
    st.markdown(
        f"""
        <div class="empty-state">
            {pill("Awaiting Agent Run", "info")}
            <strong>{h(title)}</strong><br/>
            {h(body)}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_soft_card(title: str, body: str, tags: list[str] | None = None) -> None:
    tag_html = "".join(pill(tag, "info") for tag in (tags or []))
    st.markdown(
        f"""
        <div class="soft-card">
            <div class="card-title">{h(title)}</div>
            <div class="card-text">{h(body)}</div>
            <div style="margin-top:10px;">{tag_html}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_terminal_block(title: str, content: str, tone: str = "neutral", meta: str = "") -> None:
    tone_class = "terminal-ok" if tone == "ok" else "terminal-danger" if tone == "danger" else ""
    safe_content = h(content or "(empty)")
    st.markdown(
        f"""
        <div class="terminal-card {tone_class}">
            <div class="terminal-header">
                <span>{h(title)}</span>
                <span>{h(meta)}</span>
            </div>
            <div class="terminal-body">{safe_content}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_agent_pipeline() -> str:
    nodes = ["Parse", "Model", "Code", "Execute", "Reflect", "Report"]
    parts = ['<div class="agent-pipeline">']
    for index, node in enumerate(nodes):
        if index:
            parts.append('<span class="pipeline-arrow">→</span>')
        parts.append(f'<span class="pipeline-node">{h(node)}</span>')
    parts.append("</div>")
    return "".join(parts)


def render_download_button(label: str, path: Path, file_name: str | None = None) -> None:
    if path.exists() and path.is_file():
        st.download_button(
            label,
            data=path.read_bytes(),
            file_name=file_name or path.name,
            use_container_width=True,
        )


def sidebar_section(label: str) -> None:
    st.markdown(f'<div class="sidebar-section">{h(label)}</div>', unsafe_allow_html=True)


def render_hero(provider: str, use_rag: bool, enable_reflection: bool) -> None:
    report_ready = (REPORTS_DIR / "solution_report.md").exists()
    report_tone = "ok" if report_ready else "warn"
    st.markdown(
        f"""
        <div class="app-hero">
            <div class="hero-orb"></div>
            <div class="hero-grid">
                <div>
                    <div class="hero-kicker">CUMCM Autonomous Modeling Workbench</div>
                    <h1 class="hero-title">数学建模 Auto-Solver Agent</h1>
                    <div class="hero-subtitle">
                        从题面解析、模型选择、代码执行到论文生成的一体化 Agent 工作台。
                    </div>
                    <div class="hero-description">
                        面向往年赛题复现、教学研究和自动建模实验。当前页面仅负责交互与可视化，
                        后端求解流程仍由项目内 WorkflowRunner 和模块化 Agent 串联完成。
                    </div>
                    {render_agent_pipeline()}
                </div>
                <div class="status-row">
                    <div class="status-card">
                        <div class="status-label">LLM Provider</div>
                        <div class="status-value">{h(provider)}</div>
                        {render_status_badge("Mock" if provider == "mock" else "Active", "info")}
                    </div>
                    <div class="status-card">
                        <div class="status-label">RAG</div>
                        <div class="status-value">{h("Enabled" if use_rag else "Standby")}</div>
                        {render_status_badge("RAG ON" if use_rag else "RAG OFF", "ok" if use_rag else "warn")}
                    </div>
                    <div class="status-card">
                        <div class="status-label">Reflection</div>
                        <div class="status-value">{h("Enabled" if enable_reflection else "Disabled")}</div>
                        {render_status_badge("Reflect ON" if enable_reflection else "Reflect OFF", "ok" if enable_reflection else "warn")}
                    </div>
                    <div class="status-card">
                        <div class="status-label">Report Status</div>
                        <div class="status-value">{h("Generated" if report_ready else "Awaiting")}</div>
                        {render_status_badge("Completed" if report_ready else "Pending", report_tone)}
                    </div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar() -> dict[str, Any]:
    with st.sidebar:
        st.markdown(
            """
            <div class="sidebar-title">
                <div class="kicker">Mission Console</div>
                <div class="title">Agent Control</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        sidebar_section("01 / Runtime")
        provider = st.selectbox(
            "LLM Provider",
            ["auto", "mock", "deepseek", "openai-compatible", "local-http"],
            index=0,
            help="真实 API key 只从环境变量读取；未配置时建议使用 mock。",
        )
        use_rag = st.toggle("RAG Retrieval", value=False)
        enable_reflection = st.toggle("Reflection Loop", value=True)
        export_docx = st.toggle("Export Word", value=False)
        export_pdf = st.toggle("Export PDF", value=False)

        sidebar_section("02 / Inputs")
        input_mode = st.radio("题目来源", ["示例题", "本地路径", "上传文件"], index=0)
        problem_path: Path | None = None
        data_path: Path | None = None

        if "upload_session_id" not in st.session_state:
            st.session_state["upload_session_id"] = datetime.now().strftime("%Y%m%d_%H%M%S")
        upload_dir = UPLOAD_ROOT / st.session_state["upload_session_id"]

        if input_mode == "示例题":
            problem_path = DEFAULT_PROBLEM
            data_path = DEFAULT_DATA
            st.caption(DEFAULT_PROBLEM.relative_to(PROJECT_ROOT).as_posix())
            st.caption(DEFAULT_DATA.relative_to(PROJECT_ROOT).as_posix())
        elif input_mode == "本地路径":
            problem_text = st.text_input("题面文件", "examples/sample_problem/problem.txt")
            data_text = st.text_input("数据文件或目录", "examples/sample_problem/data")
            problem_path = resolve_project_path(problem_text) if problem_text.strip() else None
            data_path = resolve_project_path(data_text) if data_text.strip() else None
        else:
            problem_upload = st.file_uploader(
                "上传赛题文件",
                type=SUPPORTED_FILES,
                accept_multiple_files=False,
            )
            data_uploads = st.file_uploader(
                "上传数据文件",
                type=SUPPORTED_FILES,
                accept_multiple_files=True,
            )
            if problem_upload is not None:
                problem_path = save_uploaded_file(problem_upload, upload_dir / "problem")
                st.caption(f"题面：{problem_upload.name}")
            if data_uploads:
                data_path = save_data_uploads(data_uploads, upload_dir / "data")
                for uploaded in data_uploads:
                    st.caption(f"数据：{uploaded.name}")

        sidebar_section("03 / Execution")
        max_repairs = st.slider("自动修复次数", min_value=0, max_value=5, value=3)
        run_clicked = st.button("开始自动求解", type="primary", use_container_width=True)

        state = get_runtime_state()
        report_exists = (REPORTS_DIR / "solution_report.md").exists()
        run_status = "已有报告" if report_exists else "等待运行"
        if state.get("execution_result"):
            success = bool(state.get("execution_result", {}).get("success"))
            run_status = "最近运行成功" if success else "最近运行有错误"
        st.caption(f"当前状态：{run_status}")

        with st.expander("清空输出目录"):
            st.warning("为遵守项目规则，前端不会自动删除 outputs 中的用户文件。需要清理时请先备份，再手动处理。")
            if st.button("清空输出目录（保护模式）", use_container_width=True):
                st.info(f"请在确认备份后手动清理：{OUTPUT_DIR}")

        sidebar_section("04 / Artifacts")
        render_download_button("下载 Markdown 报告", REPORTS_DIR / "solution_report.md", "solution_report.md")
        render_download_button("下载 Word 报告", REPORTS_DIR / "solution_report.docx", "solution_report.docx")
        render_download_button("下载 PDF 报告", REPORTS_DIR / "solution_report.pdf", "solution_report.pdf")
        if CODE_DIR.exists():
            st.download_button("下载代码 zip", make_zip([CODE_DIR]), file_name="code.zip", use_container_width=True)
        if FIGURES_DIR.exists():
            st.download_button("下载图表 zip", make_zip([FIGURES_DIR]), file_name="figures.zip", use_container_width=True)
        if LOGS_DIR.exists():
            st.download_button("下载日志 zip", make_zip([LOGS_DIR]), file_name="logs.zip", use_container_width=True)

    return {
        "provider": provider,
        "use_rag": use_rag,
        "enable_reflection": enable_reflection,
        "export_docx": export_docx,
        "export_pdf": export_pdf,
        "input_mode": input_mode,
        "problem_path": problem_path,
        "data_path": data_path,
        "max_repairs": max_repairs,
        "run_clicked": run_clicked,
    }


def run_workflow(config: dict[str, Any]) -> None:
    problem_path = config["problem_path"]
    data_path = config["data_path"]
    if problem_path is None or not problem_path.exists():
        st.error("题面文件不存在，请检查输入。")
        st.stop()
    if data_path is not None and not data_path.exists():
        st.error("数据路径不存在，请检查输入。")
        st.stop()

    try:
        llm_client, effective_provider = make_llm_client(config["provider"])
    except Exception as exc:  # noqa: BLE001
        st.error(f"LLM 初始化失败：{type(exc).__name__}: {exc}")
        st.info("可以先选择 mock，或在系统环境变量中配置对应 API key。")
        st.stop()

    progress = st.progress(0)
    status = st.empty()
    status.info("正在准备输入文件和运行环境。")
    progress.progress(8)

    try:
        runner = WorkflowRunner(
            project_root=PROJECT_ROOT,
            llm_client=llm_client,
            output_dir=OUTPUT_DIR,
            max_repairs=int(config["max_repairs"]),
            use_rag=bool(config["use_rag"]),
            enable_reflection=bool(config["enable_reflection"]),
            export_docx=bool(config["export_docx"]),
            export_pdf=bool(config["export_pdf"]),
        )
        status.info("工作流运行中：题目解析、数据画像、策略生成、代码执行和报告生成会连续完成。")
        progress.progress(22)
        state = runner.run(problem_path, data_path)
        progress.progress(100)
        status.success("运行完成。")
        st.session_state["last_state"] = state
        st.session_state["effective_provider"] = effective_provider
    except Exception as exc:  # noqa: BLE001
        progress.progress(100)
        status.error(f"工作流运行失败：{type(exc).__name__}: {exc}")
        st.info(f"可查看日志目录：{LOGS_DIR}")
        st.stop()


def workflow_completion(state: dict[str, Any]) -> tuple[int, int]:
    done = 0
    for _, key, _ in WORKFLOW_STEPS:
        if key == "file_loader":
            done += 1 if state.get("raw_problem") else 0
        elif state.get(key) not in (None, {}, []):
            done += 1
    return done, len(WORKFLOW_STEPS)


def count_questions(parsed_problem: dict[str, Any]) -> int:
    questions = parsed_problem.get("questions") or parsed_problem.get("sub_questions") or []
    return len(questions) if isinstance(questions, list) else 0


def count_candidates(strategies: dict[str, Any]) -> int:
    return sum(len(item.get("candidates", [])) for item in strategies.get("strategies", []))


def list_figures(figures_dir: Path) -> list[Path]:
    if not figures_dir.exists():
        return []
    return sorted(
        path
        for path in figures_dir.rglob("*")
        if path.is_file() and path.suffix.lower() in {".svg", ".png", ".jpg", ".jpeg"}
    )


def render_progress_steps(state: dict[str, Any]) -> None:
    execution_result = state.get("execution_result") or {}
    parts = ['<div class="step-grid">']
    for label, key, short_label in WORKFLOW_STEPS:
        if key == "file_loader":
            complete = bool(state.get("raw_problem"))
            failed = False
        elif key == "execution_result" and execution_result:
            complete = True
            failed = not bool(execution_result.get("success", False))
        else:
            complete = state.get(key) not in (None, {}, [])
            failed = False
        css = "step-failed" if failed else "step-done" if complete else "step-pending"
        status = "Failed" if failed else "Completed" if complete else "Standby"
        parts.append(
            f"""
            <div class="step-item {css}">
                <div class="step-label">{h(short_label)}</div>
                <div class="step-status">{h(label)} · {h(status)}</div>
            </div>
            """
        )
    parts.append("</div>")
    st.markdown("".join(parts), unsafe_allow_html=True)


def render_dashboard(state: dict[str, Any]) -> None:
    render_section_header(
        "Agent Mission Control",
        "运行总览",
        "从输入、建模、执行到报告的实时控制台视图。",
    )
    if not state:
        render_empty_state(
            "尚未发现运行结果",
            "选择题目和数据后点击“开始自动求解”。如果已经用命令行跑过，页面会自动读取 outputs/logs/solver_state.json。",
        )
        st.code("python main.py --problem examples/sample_problem/problem.txt --data examples/sample_problem/data")
        return

    done, total = workflow_completion(state)
    st.progress(done / total if total else 0.0, text=f"工作流完成度：{done}/{total}")
    render_progress_steps(state)

    parsed_problem = get_section(state, "parsed_problem")
    data_profile = get_section(state, "data_profile", "data_profile.json")
    strategies = get_section(state, "candidate_strategies", "model_recommendations.json")
    execution_result = get_section(state, "execution_result")
    report_path = REPORTS_DIR / "solution_report.md"
    figures = list_figures(get_output_path(state, "figures_dir", FIGURES_DIR))

    cols = st.columns(6)
    with cols[0]:
        render_metric_card("小问数量", count_questions(parsed_problem), "来自题目解析", "Q")
    with cols[1]:
        render_metric_card("数据文件", data_profile.get("file_count", 0), "CSV / XLSX", "DATA")
    with cols[2]:
        render_metric_card("候选模型", count_candidates(strategies), "Model Zoo 推荐", "M")
    with cols[3]:
        render_metric_card("图表数量", len(figures), "含数据画像图", "FIG")
    with cols[4]:
        render_metric_card("代码执行", "成功" if execution_result.get("success") else "未成功", "最近一次执行", "EXE")
    with cols[5]:
        render_metric_card("报告", "已生成" if report_path.exists() else "未生成", "Markdown", "DOC")

    problem_name = Path(state.get("problem_path", "")).name if state.get("problem_path") else "未知题面"
    problem_type = parsed_problem.get("problem_type", "unknown")
    selected_model = get_section(state, "selected_model")
    selected_solution = selected_model.get("selected_solution", {})
    route = selected_solution.get("solution_name") or selected_model.get("overall_route", "尚未选择")
    data_used = data_profile.get("table_count", 0) > 0

    st.markdown(
        f"""
        <div class="mission-card">
            <div class="section-kicker">Latest Run Summary</div>
            <div class="card-title">最近运行摘要</div>
            <div class="mission-grid">
                <div class="mission-item">
                    <div class="mission-label">Problem File</div>
                    <div class="mission-value">{h(problem_name)}</div>
                </div>
                <div class="mission-item">
                    <div class="mission-label">Problem Type</div>
                    <div class="mission-value">{h(problem_type)}</div>
                </div>
                <div class="mission-item">
                    <div class="mission-label">Selected Route</div>
                    <div class="mission-value">{h(route)}</div>
                </div>
                <div class="mission-item">
                    <div class="mission-label">Data / Report</div>
                    <div class="mission-value">{h('数据可用' if data_used else '无结构化数据')} · {h('报告已生成' if report_path.exists() else '报告待生成')}</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_problem_tab(state: dict[str, Any]) -> None:
    parsed = get_section(state, "parsed_problem") or latest_log("*ProblemParserAgent*.json")
    if not parsed:
        render_empty_state("暂无题目解析", "运行工作流后会在这里展示背景、小问、关键词和题型判断。")
        return

    render_section_header("Problem Intelligence", "题目解析", "结构化展示赛题背景、数据说明和小问列表。")
    tags = []
    for key in ("problem_type", "difficulty"):
        if parsed.get(key):
            tags.append(pill(parsed[key], "info"))
    for keyword in as_list(parsed.get("keywords"))[:8]:
        tags.append(pill(keyword, "neutral"))
    if tags:
        st.markdown("".join(tags), unsafe_allow_html=True)

    cols = st.columns([1.2, 0.8])
    with cols[0]:
        render_soft_card("背景摘要", parsed.get("background", "暂无背景摘要。"))
    with cols[1]:
        render_soft_card("数据说明", parsed.get("data_description", "暂无数据说明。"))

    questions = as_list(parsed.get("questions"))
    render_section_header("Question Set", "小问列表", "")
    if not questions:
        render_empty_state("未识别到小问", "可以查看原始日志确认题面是否包含明确的问题编号。")
    for idx, question in enumerate(questions, start=1):
        if isinstance(question, dict):
            text = question.get("text") or question.get("description") or json.dumps(question, ensure_ascii=False)
            q_type = question.get("type") or question.get("task_type") or "question"
        else:
            text = str(question)
            q_type = "question"
        with st.expander(f"小问 {idx} · {q_type}", expanded=True):
            st.write(text)

    with st.expander("原始解析 JSON"):
        st.json(parsed)


def render_data_profile_tab(state: dict[str, Any]) -> None:
    profile = get_section(state, "data_profile", "data_profile.json")
    if not profile:
        render_empty_state("暂无数据画像", "没有数据文件或尚未运行工作流时，会跳过数据画像。")
        return

    render_section_header("Data Telemetry", "数据画像", "查看表结构、字段类型、缺失值和 EDA 图表。")
    for warning in profile.get("warnings", []):
        st.warning(warning)

    files = profile.get("files", [])
    if not files:
        render_empty_state("未检测到结构化数据", "系统会继续基于题面文本和默认假设生成建模流程。")
        with st.expander("数据画像 JSON"):
            st.json(profile)
        return

    cols = st.columns(4)
    with cols[0]:
        render_metric_card("数据文件", profile.get("file_count", 0), "原始文件数", "FILE")
    with cols[1]:
        render_metric_card("数据表", profile.get("table_count", 0), "CSV 或工作表", "TAB")
    with cols[2]:
        render_metric_card("数值字段", len(profile.get("summary", {}).get("numeric_columns", [])), "可用于建模", "NUM")
    with cols[3]:
        render_metric_card("类别字段", len(profile.get("summary", {}).get("categorical_columns", [])), "可用于分组", "CAT")

    for item in files:
        with st.expander(item.get("file_name", "data table"), expanded=True):
            shape = item.get("shape", {})
            left, right = st.columns([0.7, 1.3])
            with left:
                st.metric("行数", shape.get("rows", 0))
                st.metric("列数", shape.get("columns", 0))
                st.metric("重复行", item.get("duplicate_rows", 0))
            with right:
                st.write("字段类型")
                st.json(item.get("column_types", {}))
            missing = item.get("missing_values", {})
            if missing:
                missing_total = sum(int(value or 0) for value in missing.values())
                st.caption(f"缺失值总数：{missing_total}")
            steps = item.get("recommended_preprocessing_steps", [])
            if steps:
                st.write("建议预处理")
                for step in steps:
                    st.markdown(f"- {step}")
            figures = item.get("recommended_figures", [])
            if figures:
                st.write("推荐和已生成图表")
                for fig in figures:
                    fig_path = Path(fig.get("path", ""))
                    if fig_path.exists():
                        st.image(str(fig_path), caption=fig.get("caption", fig_path.name))
                    else:
                        st.caption(fig.get("caption", "figure"))

    with st.expander("数据画像 JSON"):
        st.json(profile)


def candidate_score(candidate: dict[str, Any]) -> int:
    scores = candidate.get("scores", {})
    if isinstance(scores, dict):
        return int(scores.get("total_score", candidate.get("total_score", 0)) or 0)
    return int(candidate.get("total_score", candidate.get("recommendation_score", 0)) or 0)


def render_candidate_card(candidate: dict[str, Any], selected: bool = False) -> None:
    card_class = "solution-card selected-card candidate-card" if selected else "solution-card candidate-card"
    risks = candidate.get("risks_and_limitations", [])[:3]
    reqs = candidate.get("input_data_requirements", [])[:2]
    score = candidate_score(candidate)
    risk_tags = "".join(pill(risk, "warn") for risk in risks[:2])
    st.markdown(
        f"""
        <div class="{card_class}">
            <div class="score-chip"><div class="num">{h(score)}</div><div class="txt">score</div></div>
            <div class="card-title">{h(candidate.get('name') or candidate.get('model_id') or 'candidate model')}</div>
            <div>
                {pill(candidate.get('category', 'model'), 'info')}
                {pill(candidate.get('implementation_difficulty', 'medium'), 'warn')}
                {pill('selected', 'ok') if selected else ''}
            </div>
            <div class="card-text" style="margin-top:8px;">{h(candidate.get('why_suitable', '暂无适配说明。'))}</div>
            <div class="muted-line" style="margin-top:9px;"><strong>Output</strong> · {h(candidate.get('expected_output', '-'))}</div>
            <div class="muted-line"><strong>Input</strong> · {h('; '.join(str(x) for x in reqs) or '-')}</div>
            <div style="margin-top:9px;">{risk_tags or pill('No major risk listed', 'ok')}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_strategy_tab(state: dict[str, Any]) -> None:
    strategies = get_section(state, "candidate_strategies", "model_recommendations.json")
    selected_model = get_section(state, "selected_model")
    selected_by_task = {
        item.get("task_id"): (item.get("selected") or {}).get("model_id")
        for item in selected_model.get("selected_strategies", [])
    }

    if not strategies:
        render_empty_state("暂无建模策略", "运行工作流后，Model Zoo 推荐和候选模型评分会显示在这里。")
        return

    render_section_header("Model Evaluation Matrix", "建模策略", "Model Zoo 推荐、候选模型评分与选中模型。")
    st.caption(f"推荐来源：{strategies.get('recommendation_source', 'unknown')}")
    for group in strategies.get("strategies", []):
        st.markdown(f"#### 任务 {group.get('task_id', '-')}: {group.get('task_description', '')}")
        candidates = group.get("candidates", [])
        if not candidates:
            render_empty_state("无候选模型", "当前任务没有匹配到模型库条目。")
            continue
        columns = st.columns(min(3, len(candidates)))
        selected_id = selected_by_task.get(group.get("task_id"))
        for idx, candidate in enumerate(candidates):
            with columns[idx % len(columns)]:
                render_candidate_card(candidate, selected=candidate.get("model_id") == selected_id)

    refs = strategies.get("retrieved_references", [])
    if refs:
        with st.expander("RAG 检索参考"):
            st.json(refs)
    with st.expander("模型推荐 JSON"):
        st.json(strategies)
    if selected_model:
        with st.expander("模型选择 JSON"):
            st.json(selected_model)


def render_solution_competition_tab(state: dict[str, Any]) -> None:
    competition = get_section(state, "solution_competition", "solution_competition.json")
    if not competition:
        render_empty_state("暂无多方案比较", "运行工作流后会展示 conservative / advanced / hybrid 三套完整方案。")
        return

    render_section_header("Solution Arena", "建模方案比较与选择", "比较保守、增强和混合方案，突出最终得分最高路线。")
    selected_name = (competition.get("selected_solution") or {}).get("solution_name")
    solutions = competition.get("candidate_solutions", [])
    columns = st.columns(min(3, max(1, len(solutions))))
    for idx, solution in enumerate(solutions):
        selected = solution.get("solution_name") == selected_name
        card_class = "solution-card selected-card candidate-card" if selected else "solution-card candidate-card"
        score = solution.get("score", {}).get("total_score", "-")
        risks = solution.get("risk_points", [])[:3]
        with columns[idx % len(columns)]:
            st.markdown(
                f"""
                <div class="{card_class}">
                    <div class="score-chip"><div class="num">{h(score)}</div><div class="txt">total</div></div>
                    <div class="card-title">{h(solution.get('solution_name'))}</div>
                    <div>{pill('selected', 'ok') if selected else pill('candidate', 'neutral')}{pill(solution.get('implementation_difficulty', '-'), 'warn')}</div>
                    <div class="card-text" style="margin-top:8px;">{h(solution.get('overall_idea', ''))}</div>
                    <div class="muted-line" style="margin-top:9px;"><strong>Narrative</strong> · {h(solution.get('paper_narrative', '-'))}</div>
                    <div style="margin-top:9px;">{''.join(pill(risk, 'warn') for risk in risks) or pill('No major risk listed', 'ok')}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            with st.expander("任务模型"):
                for item in solution.get("models_for_each_task", []):
                    model = item.get("selected_model") or {}
                    st.write(f"{item.get('task_id')}: {model.get('name') or model.get('model_id')}")
                st.json(solution.get("score", {}))

    with st.expander("方案竞争 JSON"):
        st.json(competition)


def render_formula_figure_tab(state: dict[str, Any]) -> None:
    formulas = get_section(state, "formulas", "formulas.json")
    figure_plan = get_section(state, "figure_plan", "figure_plan.json")
    figures_dir = get_output_path(state, "figures_dir", FIGURES_DIR)
    figures = list_figures(figures_dir)

    render_section_header("Formula And Figure Lab", "公式与图表", "符号说明、模型公式、图表规划和生成图像。")
    if not formulas and not figure_plan and not figures:
        render_empty_state("暂无公式与图表", "公式、图表规划和生成图片会在工作流完成后显示。")
        return

    left, right = st.columns([1, 1])
    with left:
        st.markdown("#### 符号说明")
        variables = formulas.get("variables", [])
        if variables:
            st.table(variables)
        else:
            st.caption("暂无符号表。")

        st.markdown("#### 核心公式")
        latex_blocks = formulas.get("latex_blocks", [])
        if latex_blocks:
            for block in latex_blocks:
                st.caption(f"{block.get('id', '')} · {block.get('model', '')}")
                if block.get("latex"):
                    st.latex(block["latex"])
                st.write(block.get("explanation", ""))
        else:
            st.caption("暂无公式块。")

    with right:
        st.markdown("#### 图表规划")
        plans = figure_plan.get("figure_plan", [])
        if plans:
            for fig in plans:
                with st.expander(f"{fig.get('figure_id')} · {fig.get('title')}", expanded=False):
                    st.write(fig.get("caption", ""))
                    st.write(f"论文用途：{fig.get('purpose_in_paper', '-')}")
                    st.json({k: fig.get(k) for k in ("figure_type", "required_data", "x_axis", "y_axis", "grouping", "priority")})
        else:
            st.caption("暂无图表规划。")

    st.markdown("#### 已生成图表")
    if figures:
        cols = st.columns(2)
        for idx, figure in enumerate(figures):
            with cols[idx % 2]:
                st.image(str(figure), caption=figure.relative_to(figures_dir).as_posix())
                st.download_button(
                    f"下载 {figure.name}",
                    figure.read_bytes(),
                    file_name=figure.name,
                    key=f"download-figure-{idx}-{figure.name}",
                    use_container_width=True,
                )
    else:
        render_empty_state("暂无图片文件", "当代码执行或数据画像生成图表后，会在这里展示缩略图。")

    with st.expander("公式 JSON"):
        st.json(formulas)
    with st.expander("图表规划 JSON"):
        st.json(figure_plan)


def render_code_execution_tab(state: dict[str, Any]) -> None:
    attempts = get_section(state, "execution_attempts", "execution_attempts.json")
    execution_result = get_section(state, "execution_result")
    code_dir = get_output_path(state, "code_dir", CODE_DIR)
    code_files = sorted(path for path in code_dir.rglob("*") if path.is_file()) if code_dir.exists() else []

    render_section_header("Execution Console", "代码执行", "查看执行状态、修复尝试、stdout / stderr 和生成文件。")
    if not attempts and not execution_result and not code_files:
        render_empty_state("暂无代码执行结果", "工作流执行后会展示 stdout、stderr、修复尝试和生成文件。")
        return

    attempt_list = attempts if isinstance(attempts, list) else as_list(attempts)
    success = bool(execution_result.get("success")) if isinstance(execution_result, dict) else False
    final_returncode = execution_result.get("returncode", "-") if isinstance(execution_result, dict) else "-"
    cols = st.columns(4)
    with cols[0]:
        render_metric_card("执行状态", "Success" if success else "Failed", "最终状态", "RUN")
    with cols[1]:
        render_metric_card("Attempts", len(attempt_list), "含初始执行", "TRY")
    with cols[2]:
        render_metric_card("Return Code", final_returncode, "最终返回码", "RC")
    with cols[3]:
        render_metric_card("Generated Files", len(code_files), "outputs/code", "OUT")

    if attempt_list:
        for attempt in attempt_list:
            if not isinstance(attempt, dict):
                continue
            ok = bool(attempt.get("success"))
            label = f"Attempt {attempt.get('attempt', '-')}: {'success' if ok else 'failed'}"
            with st.expander(label, expanded=not ok):
                repair = attempt.get("repair")
                if repair:
                    st.write("修复说明")
                    st.json(repair)
                render_terminal_block("stdout", attempt.get("stdout", "") or "(empty)", "ok" if ok else "neutral")
                render_terminal_block("stderr", attempt.get("stderr", "") or "(empty)", "danger" if not ok else "neutral")
                generated_files = attempt.get("generated_files", [])
                if generated_files:
                    st.write("生成文件")
                    st.json(generated_files)

    st.markdown("#### 代码与输出文件")
    if code_files:
        for idx, file_path in enumerate(code_files):
            rel = file_path.relative_to(code_dir).as_posix()
            st.markdown(f'<div class="code-list">{h(rel)}</div>', unsafe_allow_html=True)
            st.download_button(
                f"下载 {file_path.name}",
                file_path.read_bytes(),
                file_name=file_path.name,
                key=f"download-code-{idx}-{file_path.name}",
            )
            if file_path.suffix.lower() == ".py":
                with st.expander(f"查看 {file_path.name}"):
                    render_terminal_block(file_path.name, read_text(file_path, 40000), "neutral")
    else:
        st.caption("没有发现代码文件。")


def render_reflection_tab(state: dict[str, Any]) -> None:
    reflection = get_section(state, "reflection_report", "reflection_report.json")
    if not reflection:
        render_empty_state("暂无反思结果", "Reflection Loop 未启用或尚未运行时，这里会保持为空。")
        return

    render_section_header("Reflection Matrix", "反思与修订", "质量评分、检出问题和修订建议。")
    score_keys = [
        ("completeness_score", "完整性"),
        ("question_alignment_score", "题目贴合"),
        ("data_usage_score", "数据使用"),
        ("modeling_depth_score", "建模深度"),
        ("report_quality_score", "报告质量"),
    ]
    cols = st.columns(len(score_keys))
    for idx, (key, label) in enumerate(score_keys):
        value = reflection.get(key, 0)
        with cols[idx]:
            render_metric_card(label, value, "0-100 或 0-5 评分", f"S{idx + 1}")
            try:
                numeric = float(value)
                st.progress(min(numeric / 100 if numeric > 5 else numeric / 5, 1.0))
            except (TypeError, ValueError):
                pass

    st.markdown(
        pill("需要修订" if reflection.get("need_revision") else "无需修订", "warn" if reflection.get("need_revision") else "ok"),
        unsafe_allow_html=True,
    )

    left, right = st.columns(2)
    with left:
        st.markdown("#### 检出问题")
        problems = reflection.get("detected_problems", [])
        if problems:
            for problem in problems:
                st.markdown(f"- {problem}")
        else:
            st.caption("未检出明显问题。")
    with right:
        st.markdown("#### 修订建议")
        fixes = reflection.get("suggested_fixes", [])
        if fixes:
            for fix in fixes:
                st.markdown(f"- {fix}")
        else:
            st.caption("暂无修订建议。")

    if reflection.get("revision_plan"):
        with st.expander("修订计划"):
            st.json(reflection.get("revision_plan"))
    with st.expander("反思 JSON"):
        st.json(reflection)


def render_report_tab(state: dict[str, Any]) -> None:
    report_path = REPORTS_DIR / "solution_report.md"
    docx_path = REPORTS_DIR / "solution_report.docx"
    pdf_path = REPORTS_DIR / "solution_report.pdf"

    render_section_header("Paper Output", "论文报告", "Markdown 报告预览和导出入口。")
    if not report_path.exists():
        render_empty_state("暂无 Markdown 报告", "运行完整工作流后会生成 outputs/reports/solution_report.md。")
        return

    cols = st.columns(3)
    with cols[0]:
        render_download_button("下载 Markdown", report_path, "solution_report.md")
    with cols[1]:
        render_download_button("下载 Word", docx_path, "solution_report.docx")
    with cols[2]:
        render_download_button("下载 PDF", pdf_path, "solution_report.pdf")

    with st.expander("报告预览", expanded=True):
        st.markdown(read_text(report_path))


def render_logs_tab(_: dict[str, Any]) -> None:
    render_section_header("Log Observatory", "运行日志", "左侧选择日志文件，右侧查看结构化内容。")
    if not LOGS_DIR.exists():
        render_empty_state("暂无日志目录", "运行后日志会保存在 outputs/logs。")
        return

    log_files = sorted(path for path in LOGS_DIR.glob("*") if path.is_file())
    if not log_files:
        render_empty_state("暂无日志文件", "运行后会展示 JSON、JSONL 等日志文件。")
        return

    col1, col2 = st.columns([0.38, 0.62])
    with col1:
        selected_name = st.selectbox("日志文件", [path.name for path in log_files])
        selected_path = LOGS_DIR / selected_name
        modified = datetime.fromtimestamp(selected_path.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        st.markdown(
            f"""
            <div class="glass-card" style="padding:14px;">
                <div class="card-title">{h(selected_name)}</div>
                {pill(str(selected_path.stat().st_size) + " bytes", "info")}
                {pill(modified, "neutral")}
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.download_button(
            f"下载 {selected_name}",
            selected_path.read_bytes(),
            file_name=selected_name,
            use_container_width=True,
        )
    with col2:
        st.markdown(
            f"""
            <div class="glass-card" style="padding:14px; margin-bottom:10px;">
                <div class="section-kicker">Log Payload</div>
                <div class="card-title">{h(selected_name)}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if selected_path.suffix == ".json":
            st.json(load_json(selected_path, {}))
        elif selected_path.suffix == ".jsonl":
            text = read_text(selected_path, 60000)
            lines = [line for line in text.splitlines() if line.strip()]
            preview = []
            for line in lines[-20:]:
                try:
                    preview.append(json.loads(line))
                except json.JSONDecodeError:
                    preview.append({"raw": line})
            st.json(preview)
        else:
            render_terminal_block(selected_name, read_text(selected_path, 60000), "neutral")


def main() -> None:
    inject_css()
    config = render_sidebar()
    provider_preview = st.session_state.get("effective_provider", config["provider"])
    render_hero(provider_preview, bool(config["use_rag"]), bool(config["enable_reflection"]))

    if config["run_clicked"]:
        run_workflow(config)

    state = get_runtime_state()

    tabs = st.tabs(
        [
            "总览 Dashboard",
            "题目解析",
            "数据画像",
            "建模策略",
            "方案比较",
            "公式与图表",
            "代码执行",
            "反思与修订",
            "论文报告",
            "运行日志",
        ]
    )
    with tabs[0]:
        render_dashboard(state)
    with tabs[1]:
        render_problem_tab(state)
    with tabs[2]:
        render_data_profile_tab(state)
    with tabs[3]:
        render_strategy_tab(state)
    with tabs[4]:
        render_solution_competition_tab(state)
    with tabs[5]:
        render_formula_figure_tab(state)
    with tabs[6]:
        render_code_execution_tab(state)
    with tabs[7]:
        render_reflection_tab(state)
    with tabs[8]:
        render_report_tab(state)
    with tabs[9]:
        render_logs_tab(state)


if __name__ == "__main__":
    main()
