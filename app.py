
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

from src.core.llm_client import DeepSeekLLMClient
from src.core.workflow import WorkflowRunner


PROJECT_ROOT = Path(__file__).resolve().parent
UPLOAD_ROOT = PROJECT_ROOT / "outputs" / "uploads"
OUTPUT_DIR = PROJECT_ROOT / "outputs"
LOGS_DIR = OUTPUT_DIR / "logs"
CODE_DIR = OUTPUT_DIR / "code"
FIGURES_DIR = OUTPUT_DIR / "figures"
REPORTS_DIR = OUTPUT_DIR / "reports"
SUPPORTED_FILES = ["pdf", "docx", "txt", "csv", "xlsx"]
LEGACY_SAMPLE_MARKERS = (
    "examples/" + "sample" + "_problem",
    "examples\\" + "sample" + "_problem",
)

WORKFLOW_STEPS = [
    ("文件读取", "file_loader", "Input"),
    ("题目解析", "parsed_problem", "Parse"),
    ("数据画像", "data_profile", "Profile"),
    ("策略生成", "candidate_strategies", "Strategy"),
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
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ---------------------------------------------------------------------
# Styling
# ---------------------------------------------------------------------
def inject_css() -> None:
    st.markdown(
        """
        <style>
        :root {
            --bg: #020617;
            --panel: rgba(15, 23, 42, 0.72);
            --panel-strong: rgba(15, 23, 42, 0.92);
            --panel-soft: rgba(30, 41, 59, 0.54);
            --border: rgba(148, 163, 184, 0.18);
            --border-strong: rgba(34, 211, 238, 0.42);
            --text: #e5edf8;
            --muted: #94a3b8;
            --muted2: #64748b;
            --cyan: #22d3ee;
            --blue: #60a5fa;
            --violet: #a78bfa;
            --green: #34d399;
            --amber: #fbbf24;
            --red: #fb7185;
            --shadow: 0 22px 80px rgba(0, 0, 0, .36);
            --glow: 0 0 0 1px rgba(34, 211, 238, .36), 0 0 42px rgba(34, 211, 238, .16);
        }

        .stApp {
            background:
                radial-gradient(circle at 78% -6%, rgba(124, 58, 237, .30), transparent 32rem),
                radial-gradient(circle at 8% 8%, rgba(34, 211, 238, .18), transparent 28rem),
                linear-gradient(135deg, #020617 0%, #07111f 44%, #0f172a 100%);
            color: var(--text);
        }

        .stApp::before {
            content: "";
            position: fixed;
            inset: 0;
            pointer-events: none;
            z-index: 0;
            background-image:
                linear-gradient(rgba(148, 163, 184, .055) 1px, transparent 1px),
                linear-gradient(90deg, rgba(148, 163, 184, .055) 1px, transparent 1px);
            background-size: 42px 42px;
            mask-image: linear-gradient(to bottom, rgba(0,0,0,.85), rgba(0,0,0,.15) 62%, transparent);
        }

        .block-container {
            position: relative;
            z-index: 1;
            max-width: 1460px;
            padding-top: 1.55rem;
            padding-bottom: 3rem;
        }

        [data-testid="stSidebar"] {
            background:
                linear-gradient(180deg, rgba(2, 6, 23, .96), rgba(15, 23, 42, .88)),
                radial-gradient(circle at 30% 0%, rgba(34, 211, 238, .11), transparent 18rem);
            border-right: 1px solid rgba(34, 211, 238, .18);
            box-shadow: 18px 0 54px rgba(0, 0, 0, .28);
        }

        [data-testid="stSidebar"] * { color: var(--text); }
        [data-testid="stSidebar"] .stCaptionContainer,
        [data-testid="stSidebar"] p { color: var(--muted); }

        div[data-testid="stButton"] > button,
        div[data-testid="stDownloadButton"] > button {
            border-radius: 12px;
            border: 1px solid rgba(148, 163, 184, .25);
            background: rgba(15, 23, 42, .74);
            color: #e2e8f0;
            font-weight: 750;
            transition: transform 160ms ease, border-color 160ms ease, box-shadow 160ms ease, background 160ms ease;
        }

        div[data-testid="stButton"] > button:hover,
        div[data-testid="stDownloadButton"] > button:hover {
            transform: translateY(-1px);
            border-color: rgba(34, 211, 238, .55);
            box-shadow: 0 0 30px rgba(34, 211, 238, .14);
            background: rgba(30, 41, 59, .9);
        }

        div[data-testid="stButton"] > button[kind="primary"] {
            border: 1px solid rgba(96, 165, 250, .72);
            background: linear-gradient(135deg, #2563eb, #7c3aed 55%, #0891b2);
            box-shadow: 0 0 40px rgba(96, 165, 250, .28);
        }

        .hero {
            position: relative;
            overflow: hidden;
            border-radius: 24px;
            border: 1px solid rgba(148, 163, 184, .18);
            background:
                linear-gradient(135deg, rgba(15, 23, 42, .86), rgba(2, 6, 23, .88)),
                radial-gradient(circle at 78% 18%, rgba(34, 211, 238, .20), transparent 20rem),
                radial-gradient(circle at 58% -24%, rgba(124, 58, 237, .26), transparent 24rem);
            box-shadow: var(--shadow);
            padding: 30px;
            margin-bottom: 18px;
        }

        .hero::before {
            content: "";
            position: absolute;
            inset: 0;
            pointer-events: none;
            background-image:
                linear-gradient(rgba(34, 211, 238, .07) 1px, transparent 1px),
                linear-gradient(90deg, rgba(34, 211, 238, .07) 1px, transparent 1px);
            background-size: 36px 36px;
            mask-image: linear-gradient(110deg, rgba(0,0,0,.75), transparent 72%);
        }

        .hero-grid {
            position: relative;
            z-index: 1;
            display: grid;
            grid-template-columns: minmax(0, 1.4fr) minmax(300px, .6fr);
            gap: 24px;
            align-items: stretch;
        }

        .kicker {
            color: var(--cyan);
            font-size: 12px;
            font-weight: 850;
            letter-spacing: .08em;
            text-transform: uppercase;
        }

        .hero-title {
            color: #f8fafc;
            font-size: clamp(34px, 4vw, 56px);
            line-height: 1.04;
            font-weight: 850;
            margin: 10px 0 0;
        }

        .hero-subtitle {
            color: #cbd5e1;
            font-size: 17px;
            line-height: 1.68;
            max-width: 880px;
            margin-top: 14px;
        }

        .glass,
        .metric-card,
        .soft-card,
        .solution-card,
        .timeline-card,
        .artifact-card,
        .file-card,
        .terminal-card,
        .report-reader,
        .launch-card {
            border: 1px solid rgba(148, 163, 184, .18);
            border-radius: 18px;
            background: rgba(15, 23, 42, .72);
            backdrop-filter: blur(16px);
            box-shadow: var(--shadow);
        }

        .glass { padding: 16px; }
        .launch-card { padding: 18px; margin-bottom: 18px; }
        .soft-card, .solution-card, .metric-card { padding: 16px; height: 100%; }
        .metric-card { position: relative; min-height: 122px; }
        .metric-icon {
            position: absolute; top: 14px; right: 14px;
            min-width: 36px; height: 30px; display: inline-flex; align-items: center; justify-content: center;
            border-radius: 11px;
            border: 1px solid rgba(34, 211, 238, .22);
            background: rgba(14, 165, 233, .10);
            color: var(--cyan);
            font-size: 13px;
            font-weight: 900;
        }

        .metric-label { color: #94a3b8; font-size: 12px; font-weight: 780; text-transform: uppercase; }
        .metric-value { color: #f8fafc; font-size: 30px; font-weight: 850; line-height: 1.1; margin-top: 12px; word-break: break-word; }
        .metric-caption { color: #94a3b8; font-size: 12px; line-height: 1.5; margin-top: 9px; }

        .section-wrap { margin: 10px 0 16px; }
        .section-title { color: #f8fafc; font-size: 22px; font-weight: 830; margin: 7px 0 4px; }
        .section-caption { color: var(--muted); font-size: 13px; margin: 0 0 14px; }

        .card-title { color: #f8fafc; font-size: 16px; font-weight: 800; line-height: 1.35; margin-bottom: 6px; }
        .card-text { color: #cbd5e1; font-size: 13px; line-height: 1.62; }
        .muted { color: var(--muted); font-size: 12px; line-height: 1.5; }

        .pill {
            display: inline-flex; align-items: center;
            border-radius: 999px; padding: 4px 9px;
            font-size: 11px; font-weight: 780;
            border: 1px solid rgba(148, 163, 184, .18);
            background: rgba(15, 23, 42, .82);
            color: #cbd5e1;
            margin: 0 6px 6px 0;
            white-space: nowrap;
            text-transform: uppercase;
        }
        .pill-ok { color:#bbf7d0; border-color:rgba(52,211,153,.45); background:rgba(6,78,59,.42); box-shadow:0 0 18px rgba(52,211,153,.11); }
        .pill-info { color:#bae6fd; border-color:rgba(34,211,238,.45); background:rgba(8,47,73,.46); box-shadow:0 0 18px rgba(34,211,238,.12); }
        .pill-warn { color:#fde68a; border-color:rgba(251,191,36,.46); background:rgba(113,63,18,.38); }
        .pill-danger { color:#fecdd3; border-color:rgba(251,113,133,.48); background:rgba(127,29,29,.38); box-shadow:0 0 18px rgba(251,113,133,.10); }

        .sidebar-title {
            padding: 14px 14px 12px;
            border: 1px solid rgba(34, 211, 238, .22);
            border-radius: 16px;
            background: rgba(15, 23, 42, .62);
            box-shadow: var(--shadow);
            margin-bottom: 12px;
        }
        .sidebar-title .title { color:#f8fafc; font-size:20px; font-weight:850; margin-top:4px; }
        .sidebar-section {
            margin: 16px 0 8px;
            padding: 9px 11px;
            border: 1px solid rgba(148, 163, 184, .16);
            border-radius: 12px;
            background: rgba(15, 23, 42, .50);
            color: #cbd5e1;
            font-size: 12px;
            font-weight: 800;
            text-transform: uppercase;
        }

        .pipeline { display:flex; flex-wrap:wrap; gap:8px; margin-top:20px; align-items:center; }
        .pipeline-node {
            padding: 7px 10px; border-radius:999px;
            border: 1px solid rgba(34,211,238,.24);
            background: rgba(8,47,73,.34);
            color: #dff9ff; font-size:12px; font-weight:780;
            box-shadow: 0 0 24px rgba(34,211,238,.08);
        }
        .pipeline-arrow { color: rgba(148,163,184,.72); font-size:12px; }

        .timeline-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(176px,1fr)); gap:10px; margin:14px 0 18px; }
        .timeline-card { padding:13px; position:relative; overflow:hidden; }
        .timeline-card.completed { border-color:rgba(34,211,238,.38); box-shadow:0 0 28px rgba(34,211,238,.12); }
        .timeline-card.pending { opacity:.58; }
        .timeline-card.failed { border-color:rgba(251,113,133,.48); box-shadow:0 0 28px rgba(251,113,133,.14); }
        .timeline-card.running::after {
            content:""; position:absolute; inset:-1px; border-radius:18px;
            border:1px solid rgba(34,211,238,.65);
            animation:pulse-ring 1.4s infinite; pointer-events:none;
        }
        @keyframes pulse-ring {
            0% { opacity:.28; transform:scale(.99); }
            50% { opacity:.9; transform:scale(1.01); }
            100% { opacity:.28; transform:scale(.99); }
        }

        .file-card, .artifact-card { padding:14px; margin:8px 0; transition: transform 160ms ease, border-color 160ms ease, box-shadow 160ms ease; }
        .file-card:hover, .artifact-card:hover, .solution-card:hover {
            transform: translateY(-1px);
            border-color: rgba(34,211,238,.36);
            box-shadow: 0 16px 48px rgba(8,145,178,.14);
        }
        .file-row, .artifact-row { display:flex; align-items:center; justify-content:space-between; gap:12px; }
        .file-icon {
            width:40px; height:40px; border-radius:12px; display:grid; place-items:center;
            background:rgba(34,211,238,.12); border:1px solid rgba(34,211,238,.22);
            color:#a5f3fc; font-weight:900; flex:0 0 auto;
        }

        .selected-card { border-color: rgba(34,211,238,.58); box-shadow: var(--glow), var(--shadow); background:linear-gradient(180deg,rgba(15,23,42,.86),rgba(8,47,73,.44)); }
        .candidate-card { position:relative; padding-right:86px; }
        .score-chip {
            position:absolute; top:14px; right:14px; min-width:58px;
            padding:7px 8px; border-radius:14px;
            border:1px solid rgba(34,211,238,.36);
            background:rgba(8,47,73,.58);
            color:#e0f2fe; text-align:center;
            box-shadow:0 0 22px rgba(34,211,238,.12);
        }
        .score-chip .num { font-size:21px; line-height:1; font-weight:900; }
        .score-chip .txt { color:var(--muted); font-size:10px; text-transform:uppercase; margin-top:3px; }

        .score-bar { margin-top:9px; }
        .score-line { display:flex; justify-content:space-between; color:#cbd5e1; font-size:12px; margin-bottom:4px; }
        .score-track { height:7px; border-radius:999px; overflow:hidden; background:rgba(51,65,85,.78); }
        .score-fill { height:100%; border-radius:999px; background:linear-gradient(90deg,#22d3ee,#60a5fa,#a78bfa); box-shadow:0 0 18px rgba(34,211,238,.30); }

        .empty-state {
            border:1px dashed rgba(34,211,238,.28);
            border-radius:18px;
            background:rgba(15,23,42,.58);
            padding:22px;
            color:#94a3b8;
            line-height:1.65;
        }
        .empty-state strong { color:#e2e8f0; }

        .terminal-card { padding:0; overflow:hidden; margin:10px 0; }
        .terminal-header {
            display:flex; justify-content:space-between; align-items:center;
            padding:10px 13px; border-bottom:1px solid rgba(148,163,184,.14);
            background:rgba(2,6,23,.66); color:#cbd5e1; font-size:12px; font-weight:780;
        }
        .terminal-body {
            max-height:340px; overflow:auto; padding:13px;
            background:rgba(2,6,23,.82); color:#dbeafe;
            font-family:ui-monospace, SFMono-Regular, Menlo, Consolas, "Liberation Mono", monospace;
            font-size:12px; line-height:1.55; white-space:pre-wrap;
            border-left:3px solid rgba(34,211,238,.42);
        }
        .terminal-danger .terminal-body { border-left-color:rgba(251,113,133,.78); color:#fecdd3; }
        .terminal-ok .terminal-body { border-left-color:rgba(52,211,153,.78); color:#dcfce7; }
        .terminal-dots span { display:inline-block; width:9px; height:9px; border-radius:50%; margin-right:5px; }
        .dot-red { background:#fb7185; } .dot-yellow { background:#fbbf24; } .dot-green { background:#34d399; }

        .report-reader { padding:20px; }
        .report-reader h1, .report-reader h2, .report-reader h3 { color:#e0f2fe; }
        .report-reader table { color:#dbeafe; border-color:rgba(148,163,184,.28); }
        .report-toc { position: sticky; top: 1rem; }

        div[data-testid="stTabs"] button {
            color:#94a3b8;
            font-weight:760;
            border-bottom:1px solid transparent;
        }
        div[data-testid="stTabs"] button[aria-selected="true"] {
            color:#e0f2fe;
            border-bottom-color:var(--cyan);
        }
        div[data-testid="stMetric"] {
            border:1px solid rgba(148,163,184,.14);
            border-radius:14px;
            background:rgba(15,23,42,.46);
            padding:10px;
        }
        div[data-testid="stExpander"] {
            border:1px solid rgba(148,163,184,.16);
            border-radius:14px;
            background:rgba(15,23,42,.50);
        }
        code, pre { color:#dbeafe !important; }

        @media (max-width: 980px) {
            .hero-grid { grid-template-columns:1fr; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------
def h(value: Any) -> str:
    return html.escape("" if value is None else str(value))


def sanitize_filename(name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "_", name.strip())
    return cleaned or "uploaded_file"


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


def make_llm_client():
    if not os.environ.get("DEEPSEEK_API_KEY"):
        raise RuntimeError("未检测到 DEEPSEEK_API_KEY。请先在环境变量中配置 DeepSeek API Key。")
    return DeepSeekLLMClient(), "deepseek"


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
        if st.session_state.get("expert_mode", False):
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
    if contains_legacy_sample_reference(disk_state):
        return {}
    return disk_state if isinstance(disk_state, dict) else {}


def get_output_path(state: dict[str, Any], key: str, fallback: Path) -> Path:
    value = state.get(key)
    return Path(value).resolve() if value else fallback


def get_section(state: dict[str, Any], state_key: str, fallback_log: str | None = None) -> Any:
    value = state.get(state_key)
    if value not in (None, {}, []):
        return value
    if fallback_log and state and not contains_legacy_sample_reference(state):
        fallback = LOGS_DIR / fallback_log
        if not is_legacy_sample_artifact(fallback):
            return load_json(fallback, {})
    return {}


def contains_legacy_sample_reference(value: Any) -> bool:
    if isinstance(value, dict):
        return any(contains_legacy_sample_reference(item) for item in value.values())
    if isinstance(value, (list, tuple, set)):
        return any(contains_legacy_sample_reference(item) for item in value)
    if isinstance(value, Path):
        text = str(value)
    elif isinstance(value, str):
        text = value
    else:
        return False
    normalized = text.replace("\\", "/").lower()
    return any(marker.replace("\\", "/").lower() in normalized for marker in LEGACY_SAMPLE_MARKERS)


def is_legacy_sample_artifact(path: Path) -> bool:
    if not path.exists() or not path.is_file():
        return False
    if contains_legacy_sample_reference(str(path)):
        return True
    try:
        return contains_legacy_sample_reference(path.read_text(encoding="utf-8", errors="replace")[:2_000_000])
    except OSError:
        return False


def visible_artifact_files(paths: Iterable[Path]) -> list[Path]:
    return [path for path in paths if not is_legacy_sample_artifact(path)]


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
        return f"{value:.3g}" if isinstance(value, float) else str(value)
    if value in (None, "", []):
        return "-"
    return str(value)


def file_size(path: Path) -> str:
    if not path.exists():
        return "-"
    value = float(path.stat().st_size)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024 or unit == "GB":
            return f"{int(value)} B" if unit == "B" else f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} GB"


def safe_rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return path.name


def list_files(root: Path, suffixes: set[str] | None = None) -> list[Path]:
    if not root.exists():
        return []
    files = [p for p in root.rglob("*") if p.is_file()]
    if suffixes:
        files = [p for p in files if p.suffix.lower() in suffixes]
    return sorted(files)


def list_figures(root: Path) -> list[Path]:
    return list_files(root, {".png", ".jpg", ".jpeg", ".svg"})


def markdown_headings(markdown: str) -> list[tuple[int, str]]:
    headings = []
    for line in markdown.splitlines():
        match = re.match(r"^(#{1,3})\s+(.+)$", line.strip())
        if match:
            headings.append((len(match.group(1)), match.group(2).strip()))
    return headings[:28]


def count_questions(parsed_problem: dict[str, Any]) -> int:
    questions = parsed_problem.get("questions") or parsed_problem.get("sub_questions") or []
    return len(questions) if isinstance(questions, list) else 0


def count_candidates(strategies: dict[str, Any]) -> int:
    total = 0
    for item in as_list(strategies.get("strategies")):
        if isinstance(item, dict):
            total += len(as_list(item.get("candidates")))
    return total


def workflow_completion(state: dict[str, Any]) -> tuple[int, int]:
    done = 0
    for _, key, _ in WORKFLOW_STEPS:
        if key == "file_loader":
            done += 1 if state.get("raw_problem") or state.get("problem_path") else 0
        elif state.get(key) not in (None, {}, []):
            done += 1
    return done, len(WORKFLOW_STEPS)


def normalize_score(value: Any) -> tuple[float, str]:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return 0.0, "-"
    scale = 100.0
    if numeric <= 5:
        scale = 5.0
    elif numeric <= 10:
        scale = 10.0
    return max(0.0, min(numeric / scale * 100, 100.0)), compact_number(value)


# ---------------------------------------------------------------------
# UI components
# ---------------------------------------------------------------------
def pill(label: Any, tone: str = "neutral") -> str:
    tone_class = {
        "ok": "pill-ok",
        "info": "pill-info",
        "warn": "pill-warn",
        "danger": "pill-danger",
    }.get(tone, "")
    return f'<span class="pill {tone_class}">{h(label)}</span>'


def section(kicker: str, title: str, caption: str = "") -> None:
    st.markdown(
        f"""
        <div class="section-wrap">
            <div class="kicker">{h(kicker)}</div>
            <div class="section-title">{h(title)}</div>
            <div class="section-caption">{h(caption)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def metric_card(label: str, value: Any, caption: str = "", icon: str = "AI") -> None:
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


def empty_state(title: str, body: str, action: str | None = None) -> None:
    action_html = f'<div style="margin-top:10px;">{pill(action, "info")}</div>' if action else ""
    st.markdown(
        f"""
        <div class="empty-state">
            {pill("Awaiting Agent Run", "info")}
            <strong>{h(title)}</strong><br/>
            {h(body)}
            {action_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def error_state(title: str, error: str, hint: str | None = None) -> None:
    hint_html = f'<div class="muted" style="margin-top:8px;">{h(hint)}</div>' if hint else ""
    st.markdown(
        f"""
        <div class="empty-state" style="border-color:rgba(251,113,133,.48); background:rgba(127,29,29,.24);">
            {pill("Action Required", "danger")}
            <strong>{h(title)}</strong><br/>
            {h(error)}
            {hint_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def soft_card(title: str, body: str, tags: list[str] | None = None) -> None:
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


def score_bar(label: str, value: Any) -> None:
    pct, shown = normalize_score(value)
    if shown == "-":
        return
    st.markdown(
        f"""
        <div class="score-bar">
            <div class="score-line"><span>{h(label)}</span><span>{h(shown)}</span></div>
            <div class="score-track"><div class="score-fill" style="width:{pct:.1f}%"></div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def file_card(path: Path, label: str = "Uploaded") -> None:
    suffix = path.suffix.lower().lstrip(".").upper() or "FILE"
    modified = datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S") if path.exists() else "-"
    expert = f'<div class="muted">{h(safe_rel(path))}</div>' if st.session_state.get("expert_mode") else ""
    st.markdown(
        f"""
        <div class="file-card">
            <div class="file-row">
                <div style="display:flex;align-items:center;gap:12px;min-width:0;">
                    <div class="file-icon">{h(suffix[:4])}</div>
                    <div style="min-width:0;">
                        <div class="card-title">{h(path.name)}</div>
                        <div class="muted">{h(label)} · {h(path.suffix or "-")} · {h(file_size(path))} · {h(modified)}</div>
                        {expert}
                    </div>
                </div>
                {pill("Ready", "ok")}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def terminal_block(title: str, content: str, tone: str = "neutral", meta: str = "") -> None:
    tone_class = "terminal-ok" if tone == "ok" else "terminal-danger" if tone == "danger" else ""
    st.markdown(
        f"""
        <div class="terminal-card {tone_class}">
            <div class="terminal-header">
                <span class="terminal-dots"><span class="dot-red"></span><span class="dot-yellow"></span><span class="dot-green"></span></span>
                <span>{h(title)}</span>
                <span>{h(meta)}</span>
            </div>
            <div class="terminal-body">{h(content or "(empty)")}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def hero(provider: str, use_rag: bool, enable_reflection: bool) -> None:
    report_status = "Ready" if (REPORTS_DIR / "solution_report.md").exists() else "Pending"
    nodes = ["Parse", "Model", "Code", "Execute", "Reflect", "Report"]
    pipeline = ['<div class="pipeline">']
    for i, node in enumerate(nodes):
        if i:
            pipeline.append('<span class="pipeline-arrow">→</span>')
        pipeline.append(f'<span class="pipeline-node">{h(node)}</span>')
    pipeline.append("</div>")

    st.markdown(
        f"""
        <div class="hero">
            <div class="hero-grid">
                <div>
                    <div class="kicker">CUMCM Autonomous Modeling Workbench</div>
                    <div class="hero-title">数学建模 Auto-Solver Agent</div>
                    <div class="hero-subtitle">
                        从题面解析、模型选择、代码执行到论文生成的一体化 Agent 工作台。
                        上传题面与数据后，系统将自动完成建模流程并生成可审阅产物。
                    </div>
                    {''.join(pipeline)}
                </div>
                <div class="glass">
                    <div class="card-title">Runtime Status</div>
                    <div style="margin-top:12px;">{pill("DeepSeek", "ok")}{pill("RAG ON" if use_rag else "RAG OFF", "info" if use_rag else "neutral")}{pill("Reflection ON" if enable_reflection else "Reflection OFF", "info" if enable_reflection else "neutral")}{pill("Report " + report_status, "ok" if report_status == "Ready" else "warn")}</div>
                    <div class="muted" style="margin-top:12px;">
                        固定 DeepSeek 后端。未配置 DEEPSEEK_API_KEY 时仍可浏览历史产物，但不能启动新任务。
                    </div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def artifact_card(title: str, count: Any, caption: str, tone: str = "info") -> None:
    st.markdown(
        f"""
        <div class="artifact-card">
            <div class="artifact-row">
                <div>
                    <div class="card-title">{h(title)}</div>
                    <div class="muted">{h(caption)}</div>
                </div>
                <div>{pill(count, tone)}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def agent_timeline(state: dict[str, Any], running: bool = False) -> None:
    parts = ['<div class="timeline-grid">']
    for idx, (label, key, short) in enumerate(WORKFLOW_STEPS):
        done = bool(state.get("raw_problem") or state.get("problem_path")) if key == "file_loader" else state.get(key) not in (None, {}, [])
        failed = key == "execution_result" and isinstance(state.get(key), dict) and state.get(key).get("success") is False
        status = "completed" if done else "pending"
        if failed:
            status = "failed"
        if running and not done and status == "pending":
            status = "running"
            running = False
        status_label = {"completed": "Completed", "pending": "Pending", "failed": "Failed", "running": "Running"}.get(status, status)
        tone = "ok" if status == "completed" else "danger" if status == "failed" else "info" if status == "running" else "neutral"
        parts.append(
            f"""
            <div class="timeline-card {status}">
                <div class="muted">Step {idx + 1:02d} · {h(short)}</div>
                <div class="card-title">{h(label)}</div>
                <div>{pill(status_label, tone)}</div>
            </div>
            """
        )
    parts.append("</div>")
    st.markdown("".join(parts), unsafe_allow_html=True)


# ---------------------------------------------------------------------
# Sidebar and workflow
# ---------------------------------------------------------------------
def render_download_button(label: str, path: Path, file_name: str | None = None) -> None:
    if path.exists() and path.is_file():
        st.download_button(label, data=path.read_bytes(), file_name=file_name or path.name, use_container_width=True)


def render_sidebar() -> dict[str, Any]:
    with st.sidebar:
        st.markdown(
            """
            <div class="sidebar-title">
                <div class="kicker">Agent Control</div>
                <div class="title">Mission Console</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown('<div class="sidebar-section">01 · Runtime</div>', unsafe_allow_html=True)
        st.success("LLM Provider：DeepSeek")
        st.session_state["expert_mode"] = st.toggle("Expert Mode", value=st.session_state.get("expert_mode", False))
        use_rag = st.toggle("启用 RAG", value=False)
        enable_reflection = st.toggle("启用 Reflection Loop", value=True)
        export_docx = st.toggle("导出 Word", value=True)
        export_pdf = st.toggle("尝试导出 PDF", value=False)

        st.markdown('<div class="sidebar-section">02 · Inputs</div>', unsafe_allow_html=True)
        if "upload_session_id" not in st.session_state:
            st.session_state["upload_session_id"] = datetime.now().strftime("%Y%m%d_%H%M%S")
        upload_dir = UPLOAD_ROOT / st.session_state["upload_session_id"]

        problem_path: Path | None = None
        data_path: Path | None = None
        problem_upload = st.file_uploader("上传赛题文件", type=SUPPORTED_FILES, accept_multiple_files=False)
        data_uploads = st.file_uploader("上传数据文件", type=SUPPORTED_FILES, accept_multiple_files=True)

        if problem_upload is not None:
            problem_path = save_uploaded_file(problem_upload, upload_dir / "problem")
            file_card(problem_path, "Problem")
        if data_uploads:
            data_path = save_data_uploads(data_uploads, upload_dir / "data")
            for data_file in sorted((data_path or Path()).glob("*")):
                if data_file.is_file():
                    file_card(data_file, "Data")

        st.markdown('<div class="sidebar-section">03 · Execution</div>', unsafe_allow_html=True)
        max_repairs = st.slider("自动修复次数", min_value=0, max_value=5, value=3)
        run_clicked = st.button("启动自动建模", type="primary", use_container_width=True)

        if not os.environ.get("DEEPSEEK_API_KEY"):
            st.error("DEEPSEEK_API_KEY 未配置")
        elif problem_path:
            st.caption("Ready to launch.")
        else:
            st.caption("请先上传赛题文件。")

        st.markdown('<div class="sidebar-section">04 · Artifacts</div>', unsafe_allow_html=True)
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
        "provider": "deepseek",
        "use_rag": use_rag,
        "enable_reflection": enable_reflection,
        "export_docx": export_docx,
        "export_pdf": export_pdf,
        "problem_path": problem_path,
        "data_path": data_path,
        "max_repairs": max_repairs,
        "run_clicked": run_clicked,
    }


def run_workflow(config: dict[str, Any]) -> None:
    problem_path = config["problem_path"]
    data_path = config["data_path"]

    if problem_path is None or not problem_path.exists():
        error_state("缺少赛题文件", "请先上传赛题 PDF、Word 或 TXT 文件。")
        st.stop()

    if not os.environ.get("DEEPSEEK_API_KEY"):
        error_state(
            "DeepSeek API Key 未配置",
            "未检测到 DEEPSEEK_API_KEY，无法启动新任务。",
            "macOS/Linux: export DEEPSEEK_API_KEY=你的key；Windows PowerShell: $env:DEEPSEEK_API_KEY='你的key'",
        )
        st.stop()

    stage_box = st.container()
    progress = st.progress(0, text="Agent is preparing...")
    log_preview = st.empty()

    simulated_stages = [
        (8, "Input validation", "正在校验题面与数据文件。"),
        (18, "DeepSeek connected", "正在初始化 DeepSeek LLM。"),
        (32, "Problem parsing", "正在解析题面、小问和建模目标。"),
        (46, "Data profiling", "正在分析数据结构与字段。"),
        (60, "Strategy generation", "正在生成建模路线与候选模型。"),
        (72, "Code execution", "正在生成并执行代码。"),
        (86, "Reflection", "正在检查结果完整性。"),
        (95, "Report writing", "正在生成论文报告与导出文件。"),
    ]

    try:
        llm_client, effective_provider = make_llm_client()
        with stage_box:
            section("LIVE RUN", "Agent is working...", "DeepSeek connected. WorkflowRunner 正在连续执行完整建模流程。")
            for pct, title, msg in simulated_stages[:2]:
                progress.progress(pct, text=title)
                log_preview.info(msg)

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

        for pct, title, msg in simulated_stages[2:5]:
            progress.progress(pct, text=title)
            log_preview.info(msg)

        state = runner.run(problem_path, data_path)

        for pct, title, msg in simulated_stages[5:]:
            progress.progress(pct, text=title)
            log_preview.info(msg)

        progress.progress(100, text="Agent run completed.")
        st.session_state["last_state"] = state
        st.session_state["effective_provider"] = effective_provider

        state_dict = state_to_dict(state)
        figure_count = len(list_figures(get_output_path(state_dict, "figures_dir", FIGURES_DIR)))
        code_count = len(list_files(get_output_path(state_dict, "code_dir", CODE_DIR), {".py"}))
        log_count = len(list_files(LOGS_DIR, {".json", ".jsonl"}))
        st.success("运行完成。")
        cols = st.columns(4)
        with cols[0]:
            metric_card("报告", "Ready" if (REPORTS_DIR / "solution_report.md").exists() else "Pending", "outputs/reports", "📄")
        with cols[1]:
            metric_card("图表", figure_count, "figures", "📈")
        with cols[2]:
            metric_card("代码", code_count, "code files", "⚙️")
        with cols[3]:
            metric_card("日志", log_count, "logs", "🧾")
    except Exception as exc:  # noqa: BLE001
        progress.progress(100, text="Agent run failed.")
        error_state("工作流运行失败", f"{type(exc).__name__}: {exc}", f"日志目录：{LOGS_DIR}")
        st.stop()


# ---------------------------------------------------------------------
# Page sections
# ---------------------------------------------------------------------
def launch_panel(config: dict[str, Any], state: dict[str, Any]) -> None:
    section("NEW MODELING RUN", "新任务启动台", "上传赛题与数据后启动 Agent。历史运行结果会保留在下方工作台。")
    st.markdown('<div class="launch-card">', unsafe_allow_html=True)
    left, right = st.columns([1.1, .9])
    with left:
        st.markdown("#### 输入状态")
        problem_path = config.get("problem_path")
        data_path = config.get("data_path")
        if problem_path:
            file_card(problem_path, "Problem")
        else:
            empty_state("等待赛题文件", "请在左侧上传赛题文件。", "Required")
        if data_path and Path(data_path).exists():
            for data_file in sorted(Path(data_path).glob("*")):
                if data_file.is_file():
                    file_card(data_file, "Data")
        else:
            empty_state("暂无数据文件", "可以不上传数据，系统将仅基于题面文本建模。", "Optional")
    with right:
        st.markdown("#### Runtime")
        key_ok = bool(os.environ.get("DEEPSEEK_API_KEY"))
        if key_ok:
            soft_card("DeepSeek 已连接", "环境变量 DEEPSEEK_API_KEY 已配置，可以启动新任务。", ["DeepSeek", "Ready"])
        else:
            error_state(
                "DeepSeek API Key 未配置",
                "当前只能查看历史 outputs，不能启动新任务。",
                "macOS/Linux: export DEEPSEEK_API_KEY=你的key；Windows PowerShell: $env:DEEPSEEK_API_KEY='你的key'",
            )
        cols = st.columns(2)
        with cols[0]:
            metric_card("RAG", "ON" if config["use_rag"] else "OFF", "知识库检索", "🔎")
        with cols[1]:
            metric_card("Reflection", "ON" if config["enable_reflection"] else "OFF", "自动反思", "🪞")

    if config["run_clicked"]:
        run_workflow(config)
    st.markdown("</div>", unsafe_allow_html=True)


def artifact_overview(state: dict[str, Any]) -> None:
    section("ARTIFACTS", "产物概览", "当前 outputs 目录下可查看和下载的结果。")
    reports = [REPORTS_DIR / "solution_report.md", REPORTS_DIR / "solution_report.docx", REPORTS_DIR / "solution_report.pdf"]
    figures = list_figures(FIGURES_DIR)
    code_files = list_files(CODE_DIR, {".py"})
    logs = visible_artifact_files(list_files(LOGS_DIR, {".json", ".jsonl"}))
    cols = st.columns(4)
    with cols[0]:
        artifact_card("Reports", sum(p.exists() for p in reports), "Markdown / Word / PDF", "ok" if any(p.exists() for p in reports) else "warn")
    with cols[1]:
        artifact_card("Figures", len(figures), "Generated images", "ok" if figures else "warn")
    with cols[2]:
        artifact_card("Code", len(code_files), "Python scripts", "ok" if code_files else "warn")
    with cols[3]:
        artifact_card("Logs", len(logs), "JSON / JSONL traces", "ok" if logs else "warn")


def render_dashboard(state: dict[str, Any], config: dict[str, Any]) -> None:
    launch_panel(config, state)

    section("MISSION CONTROL", "运行总览", "查看 Agent 工作流完成度、关键指标和产物状态。")
    if not state:
        empty_state("尚未发现运行结果", "上传赛题文件后启动自动建模。也可以查看已有 outputs 中的报告、图表和日志。")
        artifact_overview(state)
        return

    done, total = workflow_completion(state)
    st.progress(done / total if total else 0, text=f"工作流完成度：{done}/{total}")
    agent_timeline(state)

    parsed_problem = get_section(state, "parsed_problem")
    data_profile = get_section(state, "data_profile", "data_profile.json")
    strategies = get_section(state, "candidate_strategies", "model_recommendations.json")
    execution_result = get_section(state, "execution_result")
    figures = list_figures(get_output_path(state, "figures_dir", FIGURES_DIR))

    cols = st.columns(6)
    with cols[0]:
        metric_card("小问数量", count_questions(parsed_problem), "题目解析", "🧩")
    with cols[1]:
        metric_card("数据文件", data_profile.get("file_count", 0), "CSV / XLSX", "📊")
    with cols[2]:
        metric_card("候选模型", count_candidates(strategies), "Model Zoo", "🧠")
    with cols[3]:
        metric_card("图表数量", len(figures), "含数据画像", "📈")
    with cols[4]:
        metric_card("代码执行", "成功" if execution_result.get("success") else "未成功", "最近执行", "⚙️")
    with cols[5]:
        metric_card("报告", "已生成" if (REPORTS_DIR / "solution_report.md").exists() else "未生成", "Markdown", "📄")

    selected_model = get_section(state, "selected_model")
    selected_solution = selected_model.get("selected_solution", {}) if isinstance(selected_model, dict) else {}
    route = selected_solution.get("solution_name") or selected_model.get("overall_route", "尚未选择") if isinstance(selected_model, dict) else "尚未选择"
    st.markdown('<div class="glass" style="margin-top:14px;">', unsafe_allow_html=True)
    cols = st.columns(4)
    with cols[0]:
        soft_card("题面文件", Path(state.get("problem_path", "")).name if state.get("problem_path") else "未知", [parsed_problem.get("problem_type", "unknown")])
    with cols[1]:
        soft_card("最终路线", str(route), ["selected"])
    with cols[2]:
        soft_card("数据使用", "检测到结构化数据" if data_profile.get("table_count", 0) else "未检测到结构化数据", ["data"])
    with cols[3]:
        soft_card("报告状态", "可在论文报告 Tab 查看" if (REPORTS_DIR / "solution_report.md").exists() else "尚未生成", ["report"])
    st.markdown("</div>", unsafe_allow_html=True)
    artifact_overview(state)


def maybe_json(label: str, data: Any) -> None:
    if st.session_state.get("expert_mode", False):
        with st.expander(label):
            st.json(data)


def render_problem_tab(state: dict[str, Any]) -> None:
    parsed = get_section(state, "parsed_problem")
    if not parsed:
        empty_state("等待题面解析", "运行工作流后，这里会展示背景、小问、关键词和题型判断。")
        return
    section("PROBLEM", "题目解析", "结构化展示题面背景、小问目标和关键词。")
    tag_html = ""
    for key in ("problem_type", "difficulty"):
        if parsed.get(key):
            tag_html += pill(parsed[key], "info")
    for keyword in as_list(parsed.get("keywords"))[:10]:
        tag_html += pill(keyword)
    if tag_html:
        st.markdown(tag_html, unsafe_allow_html=True)

    cols = st.columns([1.2, .8])
    with cols[0]:
        soft_card("背景摘要", parsed.get("background", "暂无背景摘要。"))
    with cols[1]:
        soft_card("数据说明", parsed.get("data_description", "暂无数据说明。"))

    st.markdown("#### 小问列表")
    questions = as_list(parsed.get("questions"))
    if not questions:
        empty_state("未识别到小问", "可以开启 Expert Mode 查看原始 JSON。")
    for idx, question in enumerate(questions, start=1):
        if isinstance(question, dict):
            text = question.get("text") or question.get("description") or json.dumps(question, ensure_ascii=False)
            q_type = question.get("type") or question.get("task_type") or question.get("problem_type") or "question"
            required = question.get("required_output") or question.get("output") or "-"
        else:
            text = str(question)
            q_type = "question"
            required = "-"
        with st.expander(f"小问 {idx} · {q_type}", expanded=True):
            st.write(text)
            st.caption(f"输出目标：{required}")
    maybe_json("原始题目解析 JSON", parsed)


def render_data_profile_tab(state: dict[str, Any]) -> None:
    profile = get_section(state, "data_profile", "data_profile.json")
    if not profile:
        empty_state("暂无结构化数据画像", "没有数据文件或尚未运行数据画像时，这里会保持为空。")
        return

    section("DATA PROFILE", "数据画像", "查看表结构、字段类型、缺失值、预处理建议和数据画像图。")
    for warning in profile.get("warnings", []):
        st.warning(warning)

    files = as_list(profile.get("files"))
    if not files:
        empty_state("未检测到结构化数据", "系统会继续基于题面文本生成建模流程。")
        maybe_json("数据画像 JSON", profile)
        return

    cols = st.columns(4)
    with cols[0]:
        metric_card("数据文件", profile.get("file_count", len(files)), "原始文件数", "📁")
    with cols[1]:
        metric_card("数据表", profile.get("table_count", len(files)), "CSV / Sheet", "📊")
    with cols[2]:
        metric_card("数值字段", len(profile.get("summary", {}).get("numeric_columns", [])), "可建模", "123")
    with cols[3]:
        metric_card("类别字段", len(profile.get("summary", {}).get("categorical_columns", [])), "可分组", "ABC")

    for item in files:
        if not isinstance(item, dict):
            continue
        with st.expander(item.get("file_name", "data table"), expanded=True):
            shape = item.get("shape", {})
            c1, c2, c3 = st.columns(3)
            c1.metric("行数", shape.get("rows", 0))
            c2.metric("列数", shape.get("columns", 0))
            c3.metric("重复行", item.get("duplicate_rows", 0))
            steps = as_list(item.get("recommended_preprocessing_steps"))
            if steps:
                st.markdown("**建议预处理**")
                for step in steps:
                    st.markdown(f"- {step}")
            if st.session_state.get("expert_mode", False):
                st.markdown("**字段类型**")
                st.json(item.get("column_types", {}))

    figs = list_figures(FIGURES_DIR / "data_profile")
    if figs:
        st.markdown("#### 数据画像图")
        cols = st.columns(3)
        for i, fig in enumerate(figs):
            with cols[i % 3]:
                st.image(str(fig), caption=fig.name)
                st.download_button(f"下载 {fig.name}", fig.read_bytes(), file_name=fig.name, key=f"dp-{i}", use_container_width=True)
    maybe_json("数据画像 JSON", profile)


def candidate_score(candidate: dict[str, Any]) -> int:
    scores = candidate.get("scores", {})
    if isinstance(scores, dict):
        return int(scores.get("total_score", candidate.get("total_score", 0)) or 0)
    return int(candidate.get("total_score", candidate.get("recommendation_score", 0)) or 0)


def render_candidate_card(candidate: dict[str, Any], selected: bool = False) -> None:
    card_class = "solution-card candidate-card selected-card" if selected else "solution-card candidate-card"
    score = candidate_score(candidate)
    risks = as_list(candidate.get("risks_and_limitations"))[:3]
    reqs = as_list(candidate.get("input_data_requirements"))[:3]
    st.markdown(
        f"""
        <div class="{card_class}">
            <div class="score-chip"><div class="num">{h(score)}</div><div class="txt">Score</div></div>
            <div class="card-title">{h(candidate.get('name') or candidate.get('model_id') or 'candidate model')}</div>
            <div>{pill('SELECTED', 'ok') if selected else pill('Candidate')}{pill(candidate.get('category', 'model'), 'info')}{pill(candidate.get('implementation_difficulty', 'medium'), 'warn')}</div>
            <div class="card-text" style="margin-top:8px;">{h(candidate.get('why_suitable', '暂无适配说明。'))}</div>
            <div class="card-text" style="margin-top:8px;"><strong>预期输出：</strong>{h(candidate.get('expected_output', '-'))}</div>
            <div class="card-text"><strong>输入要求：</strong>{h('; '.join(str(x) for x in reqs) or '-')}</div>
            <div class="card-text"><strong>风险：</strong>{h('; '.join(str(x) for x in risks) or '-')}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    scores = candidate.get("scores", {})
    if isinstance(scores, dict):
        for key in ("data_fit_score", "implementation_score", "interpretability_score", "stability_score", "reportability_score"):
            score_bar(key.replace("_", " "), scores.get(key))


def render_strategy_tab(state: dict[str, Any]) -> None:
    strategies = get_section(state, "candidate_strategies", "model_recommendations.json")
    selected_model = get_section(state, "selected_model")
    if not strategies:
        empty_state("等待建模策略", "运行后这里会展示候选模型、评分和最终选择。")
        return
    section("STRATEGY", "建模策略", "以模型卡形式展示每个小问的候选模型和选择依据。")

    selected_by_task = {}
    if isinstance(selected_model, dict):
        for item in as_list(selected_model.get("selected_strategies")):
            if isinstance(item, dict):
                selected_by_task[item.get("task_id")] = (item.get("selected") or {}).get("model_id")

    for group in as_list(strategies.get("strategies")):
        if not isinstance(group, dict):
            continue
        st.markdown(f"#### 任务 {group.get('task_id', '-')} · {group.get('task_description', '')}")
        candidates = as_list(group.get("candidates"))
        if not candidates:
            empty_state("无候选模型", "当前任务没有匹配到模型库条目。")
            continue
        cols = st.columns(min(3, len(candidates)))
        selected_id = selected_by_task.get(group.get("task_id"))
        for idx, candidate in enumerate(candidates):
            if isinstance(candidate, dict):
                with cols[idx % len(cols)]:
                    render_candidate_card(candidate, selected=candidate.get("model_id") == selected_id)

    maybe_json("模型推荐 JSON", strategies)
    maybe_json("模型选择 JSON", selected_model)


def render_solution_tab(state: dict[str, Any]) -> None:
    competition = get_section(state, "solution_competition", "solution_competition.json")
    if not competition:
        empty_state("等待方案比较", "运行后会展示 conservative / advanced / hybrid 等完整方案。")
        return
    section("SOLUTION COMPETITION", "方案比较", "比较多套建模方案的可行性、风险和论文表达质量。")
    selected_name = (competition.get("selected_solution") or {}).get("solution_name")
    solutions = as_list(competition.get("candidate_solutions"))
    cols = st.columns(min(3, max(1, len(solutions))))
    for idx, solution in enumerate(solutions):
        if not isinstance(solution, dict):
            continue
        selected = solution.get("solution_name") == selected_name
        card_class = "solution-card selected-card" if selected else "solution-card"
        score = (solution.get("score") or {}).get("total_score", "-")
        with cols[idx % len(cols)]:
            st.markdown(
                f"""
                <div class="{card_class}">
                    <div class="card-title">{h(solution.get('solution_name', 'solution'))}</div>
                    <div>{pill('SELECTED', 'ok') if selected else pill('Candidate')}{pill('score ' + str(score), 'info')}</div>
                    <div class="card-text" style="margin-top:8px;">{h(solution.get('overall_idea', ''))}</div>
                    <div class="card-text"><strong>难度：</strong>{h(solution.get('implementation_difficulty', '-'))}</div>
                    <div class="card-text"><strong>论文叙事：</strong>{h(solution.get('paper_narrative', '-'))}</div>
                    <div class="card-text"><strong>风险：</strong>{h('; '.join(as_list(solution.get('risk_points'))[:3]) or '-')}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            scores = solution.get("score", {})
            if isinstance(scores, dict):
                for k, v in scores.items():
                    if k != "total_score":
                        score_bar(k.replace("_", " "), v)
    maybe_json("方案竞争 JSON", competition)


def render_formula_figure_tab(state: dict[str, Any]) -> None:
    formulas = get_section(state, "formulas", "formulas.json")
    figure_plan = get_section(state, "figure_plan", "figure_plan.json")
    figures = list_figures(get_output_path(state, "figures_dir", FIGURES_DIR))
    if not formulas and not figure_plan and not figures:
        empty_state("等待公式与图表", "运行后会展示 LaTeX 公式、图表规划和生成图片。")
        return
    section("FORMULA & FIGURES", "公式与图表", "左侧为数学表达，右侧为图表规划，下方为图表 Gallery。")
    left, right = st.columns([1, 1])
    with left:
        st.markdown("#### 符号说明")
        variables = as_list(formulas.get("variables")) if isinstance(formulas, dict) else []
        if variables:
            st.table(variables)
        else:
            st.caption("暂无符号表。")
        st.markdown("#### 核心公式")
        for block in as_list(formulas.get("latex_blocks")) if isinstance(formulas, dict) else []:
            if isinstance(block, dict):
                st.caption(f"{block.get('id', '')} · {block.get('model', '')}")
                if block.get("latex"):
                    st.latex(block["latex"])
                st.write(block.get("explanation", ""))
    with right:
        st.markdown("#### 图表规划")
        plans = as_list(figure_plan.get("figure_plan")) if isinstance(figure_plan, dict) else []
        if plans:
            for fig in plans[:10]:
                if isinstance(fig, dict):
                    with st.expander(f"{fig.get('figure_id', '')} · {fig.get('title', 'Figure')}", expanded=False):
                        st.write(fig.get("caption", ""))
                        st.caption(f"用途：{fig.get('purpose_in_paper', '-')}")
                        if st.session_state.get("expert_mode"):
                            st.json(fig)
        else:
            st.caption("暂无图表规划。")

    st.markdown("#### 图表 Gallery")
    if figures:
        filter_choice = st.radio("图表来源", ["All", "Data Profile", "Model Output", "Sensitivity"], horizontal=True)
        filtered = []
        for fig in figures:
            low = fig.as_posix().lower()
            if filter_choice == "Data Profile" and "data_profile" not in low:
                continue
            if filter_choice == "Sensitivity" and "sens" not in low and "灵敏" not in fig.name:
                continue
            if filter_choice == "Model Output" and "data_profile" in low:
                continue
            filtered.append(fig)
        cols = st.columns(3)
        for idx, fig in enumerate(filtered):
            with cols[idx % 3]:
                st.markdown('<div class="glass">', unsafe_allow_html=True)
                st.image(str(fig), caption=fig.name)
                st.caption(f"{fig.suffix.upper()} · {file_size(fig)}")
                st.download_button("下载图表", fig.read_bytes(), file_name=fig.name, key=f"fig-{idx}-{fig.name}", use_container_width=True)
                st.markdown("</div>", unsafe_allow_html=True)
    else:
        empty_state("暂无图表文件", "当数据画像或代码执行生成图片后，会在这里显示。")
    maybe_json("公式 JSON", formulas)
    maybe_json("图表规划 JSON", figure_plan)


def render_execution_tab(state: dict[str, Any]) -> None:
    attempts = get_section(state, "execution_attempts", "execution_attempts.json")
    execution_result = get_section(state, "execution_result")
    code_dir = get_output_path(state, "code_dir", CODE_DIR)
    code_files = list_files(code_dir)
    if not attempts and not execution_result and not code_files:
        empty_state("等待代码执行", "运行后会展示执行状态、修复过程、stdout/stderr 和代码文件。")
        return
    section("EXECUTION CONSOLE", "代码执行", "查看自动生成代码、执行结果和修复时间线。")
    attempt_list = attempts if isinstance(attempts, list) else as_list(attempts)
    success = bool(execution_result.get("success")) if isinstance(execution_result, dict) else False
    cols = st.columns(4)
    with cols[0]:
        metric_card("Execution", "Success" if success else "Failed / Pending", "最终状态", "⚙️")
    with cols[1]:
        metric_card("Attempts", len(attempt_list), "含修复", "🔁")
    with cols[2]:
        metric_card("Return Code", execution_result.get("returncode", "-") if isinstance(execution_result, dict) else "-", "最终返回码", "CLI")
    with cols[3]:
        metric_card("Files", len(code_files), "outputs/code", "PY")

    st.markdown("#### Repair Timeline")
    if attempt_list:
        for attempt in attempt_list:
            if isinstance(attempt, dict):
                status = "success" if attempt.get("success") else "failed"
                with st.expander(f"Attempt {attempt.get('attempt', '-')} · {status}", expanded=not attempt.get("success")):
                    if attempt.get("repair"):
                        st.json(attempt.get("repair"))
                    if st.session_state.get("expert_mode"):
                        terminal_block("stdout", attempt.get("stdout", ""), "ok")
                        terminal_block("stderr", attempt.get("stderr", ""), "danger" if attempt.get("stderr") else "neutral")
                    else:
                        stderr = attempt.get("stderr", "")
                        if stderr:
                            terminal_block("stderr summary", stderr[:1600], "danger")
                        else:
                            st.success("无错误输出。")
    else:
        empty_state("暂无执行尝试", "没有找到 execution_attempts.json。")

    st.markdown("#### Code Files")
    if code_files:
        for idx, file_path in enumerate(code_files):
            st.markdown(
                f"""
                <div class="file-card">
                    <div class="file-row">
                        <div><div class="card-title">{h(file_path.name)}</div><div class="muted">{h(safe_rel(file_path))} · {h(file_size(file_path))}</div></div>
                        {pill(file_path.suffix.upper() or "FILE", "info")}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            st.download_button(f"下载 {file_path.name}", file_path.read_bytes(), file_name=file_path.name, key=f"code-{idx}", use_container_width=True)
            if file_path.suffix.lower() == ".py" and st.session_state.get("expert_mode"):
                with st.expander(f"查看 {file_path.name}"):
                    st.code(read_text(file_path, 50000), language="python")
    maybe_json("执行结果 JSON", execution_result)


def render_reflection_tab(state: dict[str, Any]) -> None:
    reflection = get_section(state, "reflection_report", "reflection_report.json")
    if not reflection:
        empty_state("等待反思结果", "Reflection Loop 未启用或尚未运行时，这里会保持为空。")
        return
    section("QUALITY REVIEW", "反思与修订", "查看完整性、题目贴合度、数据使用、建模深度和报告质量。")
    score_keys = [
        ("completeness_score", "完整性"),
        ("question_alignment_score", "题目贴合"),
        ("data_usage_score", "数据使用"),
        ("modeling_depth_score", "建模深度"),
        ("report_quality_score", "报告质量"),
    ]
    values = []
    for key, _ in score_keys:
        try:
            values.append(float(reflection.get(key, 0)))
        except (TypeError, ValueError):
            values.append(0.0)
    overall = sum(values) / len(values) if values else 0
    metric_card("Overall Quality", overall, "平均评分", "QA")
    for key, label in score_keys:
        score_bar(label, reflection.get(key, 0))

    st.markdown(pill("需要修订" if reflection.get("need_revision") else "质量检查通过", "warn" if reflection.get("need_revision") else "ok"), unsafe_allow_html=True)
    left, right = st.columns(2)
    with left:
        st.markdown("#### 检出问题")
        problems = as_list(reflection.get("detected_problems"))
        if problems:
            for problem in problems:
                st.warning(str(problem))
        else:
            st.success("未检出明显问题。")
    with right:
        st.markdown("#### 修订建议")
        fixes = as_list(reflection.get("suggested_fixes"))
        if fixes:
            for fix in fixes:
                st.info(str(fix))
        else:
            st.caption("暂无修订建议。")
    maybe_json("反思 JSON", reflection)


def render_report_tab(state: dict[str, Any]) -> None:
    report_path = REPORTS_DIR / "solution_report.md"
    if not report_path.exists():
        empty_state("报告尚未生成", "运行完整工作流后会生成 outputs/reports/solution_report.md。")
        return
    section("REPORT READER", "论文报告", "以阅读器形式预览 Markdown 报告，并下载 Markdown / Word / PDF。")
    markdown = read_text(report_path)
    left, right = st.columns([.28, .72])
    with left:
        st.markdown('<div class="glass report-toc">', unsafe_allow_html=True)
        st.markdown("#### 报告目录")
        headings = markdown_headings(markdown)
        if headings:
            for level, title in headings:
                indent = "　" * (level - 1)
                st.caption(f"{indent}{title}")
        else:
            st.caption("未识别到标题目录。")
        st.markdown("#### 下载")
        render_download_button("Markdown", report_path, "solution_report.md")
        render_download_button("Word", REPORTS_DIR / "solution_report.docx", "solution_report.docx")
        render_download_button("PDF", REPORTS_DIR / "solution_report.pdf", "solution_report.pdf")
        st.caption(f"更新时间：{datetime.fromtimestamp(report_path.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')}")
        st.markdown("</div>", unsafe_allow_html=True)
    with right:
        full = st.toggle("展开完整报告", value=st.session_state.get("expert_mode", False))
        preview = markdown if full else markdown[:12000] + ("\n\n> 已截断预览，打开“展开完整报告”查看全文。" if len(markdown) > 12000 else "")
        st.markdown('<div class="report-reader">', unsafe_allow_html=True)
        st.markdown(preview)
        st.markdown("</div>", unsafe_allow_html=True)


def render_logs_tab(state: dict[str, Any]) -> None:
    section("LOGS", "运行日志", "选择日志文件查看结构化跟踪信息。Expert Mode 下可查看更多细节。")
    if not LOGS_DIR.exists():
        empty_state("暂无日志目录", "运行后日志会保存在 outputs/logs。")
        return
    log_files = visible_artifact_files(list_files(LOGS_DIR))
    if not log_files:
        empty_state("暂无日志文件", "运行后会展示 JSON、JSONL 等日志文件。")
        return
    col1, col2 = st.columns([.36, .64])
    with col1:
        selected_name = st.selectbox("日志文件", [p.name for p in log_files])
        selected_path = LOGS_DIR / selected_name
        file_card(selected_path, "Log")
        st.download_button(f"下载 {selected_name}", selected_path.read_bytes(), file_name=selected_name, use_container_width=True)
    with col2:
        if selected_path.suffix == ".json":
            st.json(load_json(selected_path, {}))
        elif selected_path.suffix == ".jsonl":
            lines = [line for line in read_text(selected_path, 120000).splitlines() if line.strip()]
            preview = []
            for line in lines[-20:]:
                try:
                    preview.append(json.loads(line))
                except json.JSONDecodeError:
                    preview.append({"raw": line})
            st.json(preview)
        else:
            terminal_block(selected_name, read_text(selected_path, 80000), "neutral", file_size(selected_path))


def main() -> None:
    inject_css()
    config = render_sidebar()
    hero("deepseek", bool(config["use_rag"]), bool(config["enable_reflection"]))
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
        render_dashboard(state, config)
    with tabs[1]:
        render_problem_tab(state)
    with tabs[2]:
        render_data_profile_tab(state)
    with tabs[3]:
        render_strategy_tab(state)
    with tabs[4]:
        render_solution_tab(state)
    with tabs[5]:
        render_formula_figure_tab(state)
    with tabs[6]:
        render_execution_tab(state)
    with tabs[7]:
        render_reflection_tab(state)
    with tabs[8]:
        render_report_tab(state)
    with tabs[9]:
        render_logs_tab(state)


if __name__ == "__main__":
    main()
