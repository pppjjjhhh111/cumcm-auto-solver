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
    ("文件读取", "file_loader"),
    ("题目解析", "parsed_problem"),
    ("数据画像", "data_profile"),
    ("策略生成", "candidate_strategies"),
    ("方案竞争", "solution_competition"),
    ("公式生成", "formulas"),
    ("图表规划", "figure_plan"),
    ("代码执行", "execution_result"),
    ("结果分析", "result_analysis"),
    ("反思修订", "reflection_report"),
    ("报告生成", "paper"),
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
            --bg: #f7f8fa;
            --panel: #ffffff;
            --border: #e5e7eb;
            --border-strong: #d1d5db;
            --text: #111827;
            --muted: #6b7280;
            --accent: #2563eb;
            --accent-soft: #eff6ff;
            --teal: #0f766e;
            --teal-soft: #ecfdf5;
            --amber: #a16207;
            --amber-soft: #fffbeb;
            --danger: #b91c1c;
            --danger-soft: #fef2f2;
            --shadow: 0 1px 2px rgba(15, 23, 42, 0.06), 0 8px 24px rgba(15, 23, 42, 0.04);
        }

        .stApp {
            background: var(--bg);
            color: var(--text);
        }

        .block-container {
            padding-top: 1.6rem;
            padding-bottom: 3rem;
            max-width: 1440px;
        }

        [data-testid="stSidebar"] {
            background: #ffffff;
            border-right: 1px solid var(--border);
        }

        div[data-testid="stButton"] > button {
            border-radius: 6px;
            border: 1px solid var(--border-strong);
            box-shadow: none;
            font-weight: 600;
        }

        .app-hero {
            border: 1px solid var(--border);
            border-radius: 8px;
            background:
                linear-gradient(135deg, rgba(255,255,255,0.98), rgba(247,250,252,0.96)),
                linear-gradient(135deg, rgba(37,99,235,0.08), rgba(15,118,110,0.07));
            box-shadow: var(--shadow);
            padding: 28px 30px;
            margin-bottom: 18px;
        }

        .hero-kicker {
            color: var(--muted);
            font-size: 13px;
            font-weight: 700;
            letter-spacing: 0.03em;
            text-transform: uppercase;
            margin-bottom: 8px;
        }

        .hero-title {
            color: var(--text);
            font-size: 34px;
            line-height: 1.12;
            font-weight: 760;
            letter-spacing: 0;
            margin: 0;
        }

        .hero-subtitle {
            color: #374151;
            font-size: 17px;
            line-height: 1.55;
            max-width: 840px;
            margin: 12px 0 0;
        }

        .hero-description {
            color: var(--muted);
            font-size: 14px;
            line-height: 1.6;
            max-width: 900px;
            margin-top: 8px;
        }

        .status-row {
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            margin-top: 20px;
        }

        .status-card {
            min-width: 170px;
            border: 1px solid var(--border);
            border-radius: 6px;
            background: rgba(255,255,255,0.78);
            padding: 12px 14px;
        }

        .status-label {
            color: var(--muted);
            font-size: 12px;
            line-height: 1.2;
        }

        .status-value {
            color: var(--text);
            font-size: 16px;
            font-weight: 720;
            line-height: 1.4;
            margin-top: 4px;
        }

        .metric-card, .soft-card, .solution-card {
            border: 1px solid var(--border);
            border-radius: 6px;
            background: var(--panel);
            box-shadow: var(--shadow);
            padding: 16px;
            height: 100%;
        }

        .metric-label {
            color: var(--muted);
            font-size: 12px;
            font-weight: 650;
            line-height: 1.2;
        }

        .metric-value {
            color: var(--text);
            font-size: 24px;
            font-weight: 760;
            line-height: 1.2;
            margin-top: 8px;
            word-break: break-word;
        }

        .metric-caption {
            color: var(--muted);
            font-size: 12px;
            line-height: 1.45;
            margin-top: 8px;
        }

        .section-title {
            color: var(--text);
            font-size: 18px;
            font-weight: 760;
            letter-spacing: 0;
            margin: 8px 0 12px;
        }

        .selected-card {
            border-color: rgba(37, 99, 235, 0.45);
            box-shadow: 0 0 0 1px rgba(37, 99, 235, 0.12), var(--shadow);
            background: linear-gradient(180deg, #ffffff, #f8fbff);
        }

        .card-title {
            color: var(--text);
            font-size: 15px;
            font-weight: 730;
            line-height: 1.35;
            margin-bottom: 6px;
        }

        .card-text {
            color: #374151;
            font-size: 13px;
            line-height: 1.58;
        }

        .pill {
            display: inline-flex;
            align-items: center;
            border-radius: 999px;
            padding: 4px 9px;
            font-size: 12px;
            font-weight: 650;
            border: 1px solid var(--border);
            background: #f9fafb;
            color: #374151;
            margin: 0 6px 6px 0;
            white-space: nowrap;
        }

        .pill-ok {
            background: var(--teal-soft);
            color: var(--teal);
            border-color: #bbf7d0;
        }

        .pill-info {
            background: var(--accent-soft);
            color: var(--accent);
            border-color: #bfdbfe;
        }

        .pill-warn {
            background: var(--amber-soft);
            color: var(--amber);
            border-color: #fde68a;
        }

        .pill-danger {
            background: var(--danger-soft);
            color: var(--danger);
            border-color: #fecaca;
        }

        .step-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(132px, 1fr));
            gap: 8px;
            margin: 8px 0 18px;
        }

        .step-item {
            border: 1px solid var(--border);
            border-radius: 6px;
            background: #ffffff;
            padding: 10px 11px;
            min-height: 58px;
        }

        .step-done {
            border-color: #bbf7d0;
            background: #f8fffb;
        }

        .step-label {
            color: var(--text);
            font-size: 13px;
            font-weight: 700;
        }

        .step-status {
            color: var(--muted);
            font-size: 12px;
            margin-top: 5px;
        }

        .empty-state {
            border: 1px dashed var(--border-strong);
            border-radius: 6px;
            background: #ffffff;
            padding: 22px;
            color: var(--muted);
            line-height: 1.65;
        }

        .code-list {
            border: 1px solid var(--border);
            border-radius: 6px;
            background: #ffffff;
            padding: 10px 12px;
            margin-bottom: 8px;
        }

        .small-divider {
            height: 1px;
            background: var(--border);
            margin: 18px 0;
        }

        div[data-testid="stTabs"] button {
            font-weight: 650;
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
    except json.JSONDecodeError:
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


def render_metric_card(label: str, value: Any, caption: str = "") -> None:
    st.markdown(
        f"""
        <div class="metric-card">
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


def render_hero(provider: str, use_rag: bool, enable_reflection: bool) -> None:
    st.markdown(
        f"""
        <div class="app-hero">
            <div class="hero-kicker">CUMCM Auto-Solver Workbench</div>
            <h1 class="hero-title">数学建模 Auto-Solver Agent</h1>
            <div class="hero-subtitle">自动读题、建模、写代码、跑实验、生成报告。</div>
            <div class="hero-description">
                面向往年赛题复现、教学研究和 Agent 自动解题实验。页面只负责上传、配置、运行和查看中间产物，
                核心求解仍由当前项目的 WorkflowRunner 串联完成。
            </div>
            <div class="status-row">
                <div class="status-card">
                    <div class="status-label">LLM Provider</div>
                    <div class="status-value">{h(provider)}</div>
                </div>
                <div class="status-card">
                    <div class="status-label">RAG</div>
                    <div class="status-value">{h('已启用' if use_rag else '未启用')}</div>
                </div>
                <div class="status-card">
                    <div class="status-label">Reflection Loop</div>
                    <div class="status-value">{h('已启用' if enable_reflection else '未启用')}</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_download_button(label: str, path: Path, file_name: str | None = None) -> None:
    if path.exists() and path.is_file():
        st.download_button(
            label,
            data=path.read_bytes(),
            file_name=file_name or path.name,
            use_container_width=True,
        )


def render_sidebar() -> dict[str, Any]:
    with st.sidebar:
        st.markdown("## 项目设置")
        provider = st.selectbox(
            "LLM Provider",
            ["auto", "mock", "deepseek", "openai-compatible", "local-http"],
            index=0,
            help="真实 API key 只从环境变量读取；未配置时建议使用 mock。",
        )
        use_rag = st.toggle("启用 RAG", value=False)
        enable_reflection = st.toggle("启用 Reflection Loop", value=True)
        export_docx = st.toggle("导出 Word", value=False)
        export_pdf = st.toggle("尝试导出 PDF", value=False)

        st.markdown("## 文件上传")
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

        st.markdown("## 运行控制")
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

        st.markdown("## 下载")
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
    for _, key in WORKFLOW_STEPS:
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
    parts = ['<div class="step-grid">']
    for label, key in WORKFLOW_STEPS:
        if key == "file_loader":
            complete = bool(state.get("raw_problem"))
        else:
            complete = state.get(key) not in (None, {}, [])
        css = "step-done" if complete else "step-pending"
        status = "完成" if complete else "等待"
        parts.append(
            f"""
            <div class="step-item {css}">
                <div class="step-label">{h(label)}</div>
                <div class="step-status">{h(status)}</div>
            </div>
            """
        )
    parts.append("</div>")
    st.markdown("".join(parts), unsafe_allow_html=True)


def render_dashboard(state: dict[str, Any]) -> None:
    st.markdown('<div class="section-title">运行总览</div>', unsafe_allow_html=True)
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
        render_metric_card("小问数量", count_questions(parsed_problem), "来自题目解析")
    with cols[1]:
        render_metric_card("数据文件", data_profile.get("file_count", 0), "CSV / XLSX")
    with cols[2]:
        render_metric_card("候选模型", count_candidates(strategies), "Model Zoo 推荐")
    with cols[3]:
        render_metric_card("图表数量", len(figures), "含数据画像图")
    with cols[4]:
        render_metric_card("代码执行", "成功" if execution_result.get("success") else "未成功", "最近一次执行")
    with cols[5]:
        render_metric_card("报告", "已生成" if report_path.exists() else "未生成", "Markdown")

    st.markdown('<div class="small-divider"></div>', unsafe_allow_html=True)
    problem_name = Path(state.get("problem_path", "")).name if state.get("problem_path") else "未知题面"
    problem_type = parsed_problem.get("problem_type", "unknown")
    selected_model = get_section(state, "selected_model")
    selected_solution = selected_model.get("selected_solution", {})
    route = selected_solution.get("solution_name") or selected_model.get("overall_route", "尚未选择")
    data_used = data_profile.get("table_count", 0) > 0
    cols = st.columns(4)
    with cols[0]:
        render_soft_card("题面文件", problem_name, [problem_type])
    with cols[1]:
        render_soft_card("最终路线", str(route), ["selected"])
    with cols[2]:
        render_soft_card("数据使用", "检测到结构化数据" if data_used else "未检测到结构化数据", ["data"])
    with cols[3]:
        render_soft_card("报告状态", "可在论文报告 Tab 查看和下载" if report_path.exists() else "尚未生成报告", ["report"])


def render_problem_tab(state: dict[str, Any]) -> None:
    parsed = get_section(state, "parsed_problem") or latest_log("*ProblemParserAgent*.json")
    if not parsed:
        render_empty_state("暂无题目解析", "运行工作流后会在这里展示背景、小问、关键词和题型判断。")
        return

    st.markdown('<div class="section-title">题目解析</div>', unsafe_allow_html=True)
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
    st.markdown('<div class="section-title">小问列表</div>', unsafe_allow_html=True)
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

    st.markdown('<div class="section-title">数据画像</div>', unsafe_allow_html=True)
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
        render_metric_card("数据文件", profile.get("file_count", 0), "原始文件数")
    with cols[1]:
        render_metric_card("数据表", profile.get("table_count", 0), "CSV 或工作表")
    with cols[2]:
        render_metric_card("数值字段", len(profile.get("summary", {}).get("numeric_columns", [])), "可用于建模")
    with cols[3]:
        render_metric_card("类别字段", len(profile.get("summary", {}).get("categorical_columns", [])), "可用于分组")

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
    card_class = "solution-card selected-card" if selected else "solution-card"
    risks = candidate.get("risks_and_limitations", [])[:3]
    reqs = candidate.get("input_data_requirements", [])[:3]
    score = candidate_score(candidate)
    st.markdown(
        f"""
        <div class="{card_class}">
            <div class="card-title">{h(candidate.get('name') or candidate.get('model_id') or 'candidate model')}</div>
            <div>{pill(candidate.get('category', 'model'), 'info')}{pill(candidate.get('implementation_difficulty', 'medium'), 'warn')}{pill('score ' + str(score), 'ok' if selected else 'neutral')}</div>
            <div class="card-text" style="margin-top:8px;">{h(candidate.get('why_suitable', '暂无适配说明。'))}</div>
            <div class="card-text" style="margin-top:8px;"><strong>预期输出：</strong>{h(candidate.get('expected_output', '-'))}</div>
            <div class="card-text"><strong>论文表达：</strong>{h(candidate.get('paper_expression_advantage', '-'))}</div>
            <div class="card-text"><strong>输入要求：</strong>{h('; '.join(str(x) for x in reqs) or '-')}</div>
            <div class="card-text"><strong>风险限制：</strong>{h('; '.join(str(x) for x in risks) or '-')}</div>
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

    st.markdown('<div class="section-title">建模策略</div>', unsafe_allow_html=True)
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

    st.markdown('<div class="section-title">建模方案比较与选择</div>', unsafe_allow_html=True)
    selected_name = (competition.get("selected_solution") or {}).get("solution_name")
    solutions = competition.get("candidate_solutions", [])
    columns = st.columns(min(3, max(1, len(solutions))))
    for idx, solution in enumerate(solutions):
        selected = solution.get("solution_name") == selected_name
        card_class = "solution-card selected-card" if selected else "solution-card"
        score = solution.get("score", {}).get("total_score", "-")
        with columns[idx % len(columns)]:
            st.markdown(
                f"""
                <div class="{card_class}">
                    <div class="card-title">{h(solution.get('solution_name'))}</div>
                    <div>{pill('selected', 'ok') if selected else pill('candidate', 'neutral')}{pill('score ' + str(score), 'info')}</div>
                    <div class="card-text" style="margin-top:8px;">{h(solution.get('overall_idea', ''))}</div>
                    <div class="card-text" style="margin-top:8px;"><strong>难度：</strong>{h(solution.get('implementation_difficulty', '-'))}</div>
                    <div class="card-text"><strong>论文叙事：</strong>{h(solution.get('paper_narrative', '-'))}</div>
                    <div class="card-text"><strong>主要风险：</strong>{h('; '.join(solution.get('risk_points', [])[:3]) or '-')}</div>
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

    st.markdown('<div class="section-title">公式与图表</div>', unsafe_allow_html=True)
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

    st.markdown('<div class="section-title">代码执行</div>', unsafe_allow_html=True)
    if not attempts and not execution_result and not code_files:
        render_empty_state("暂无代码执行结果", "工作流执行后会展示 stdout、stderr、修复尝试和生成文件。")
        return

    attempt_list = attempts if isinstance(attempts, list) else as_list(attempts)
    success = bool(execution_result.get("success")) if isinstance(execution_result, dict) else False
    final_returncode = execution_result.get("returncode", "-") if isinstance(execution_result, dict) else "-"
    cols = st.columns(4)
    with cols[0]:
        render_metric_card("执行状态", "成功" if success else "失败或未完成", "最终状态")
    with cols[1]:
        render_metric_card("尝试次数", len(attempt_list), "含初始执行")
    with cols[2]:
        render_metric_card("Return code", final_returncode, "最终返回码")
    with cols[3]:
        render_metric_card("代码文件", len(code_files), "outputs/code")

    if attempt_list:
        for attempt in attempt_list:
            if not isinstance(attempt, dict):
                continue
            label = f"Attempt {attempt.get('attempt', '-')}: {'success' if attempt.get('success') else 'failed'}"
            with st.expander(label, expanded=not attempt.get("success")):
                repair = attempt.get("repair")
                if repair:
                    st.write("修复说明")
                    st.json(repair)
                st.write("stdout")
                st.code(attempt.get("stdout", "") or "(empty)", language="text")
                st.write("stderr")
                st.code(attempt.get("stderr", "") or "(empty)", language="text")
                generated_files = attempt.get("generated_files", [])
                if generated_files:
                    st.write("生成文件")
                    st.json(generated_files)

    st.markdown("#### 代码与输出文件")
    if code_files:
        for idx, file_path in enumerate(code_files):
            rel = file_path.relative_to(code_dir).as_posix()
            st.markdown(f'<div class="code-list"><strong>{h(rel)}</strong></div>', unsafe_allow_html=True)
            st.download_button(
                f"下载 {file_path.name}",
                file_path.read_bytes(),
                file_name=file_path.name,
                key=f"download-code-{idx}-{file_path.name}",
            )
            if file_path.suffix.lower() == ".py":
                with st.expander(f"查看 {file_path.name}"):
                    st.code(read_text(file_path, 40000), language="python")
    else:
        st.caption("没有发现代码文件。")


def render_reflection_tab(state: dict[str, Any]) -> None:
    reflection = get_section(state, "reflection_report", "reflection_report.json")
    if not reflection:
        render_empty_state("暂无反思结果", "Reflection Loop 未启用或尚未运行时，这里会保持为空。")
        return

    st.markdown('<div class="section-title">反思与修订</div>', unsafe_allow_html=True)
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
            render_metric_card(label, value, "0-100 或 0-5 评分")
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

    st.markdown('<div class="section-title">论文报告</div>', unsafe_allow_html=True)
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
    st.markdown('<div class="section-title">运行日志</div>', unsafe_allow_html=True)
    if not LOGS_DIR.exists():
        render_empty_state("暂无日志目录", "运行后日志会保存在 outputs/logs。")
        return

    log_files = sorted(path for path in LOGS_DIR.glob("*") if path.is_file())
    if not log_files:
        render_empty_state("暂无日志文件", "运行后会展示 JSON、JSONL 等日志文件。")
        return

    col1, col2 = st.columns([0.45, 0.55])
    with col1:
        selected_name = st.selectbox("日志文件", [path.name for path in log_files])
        selected_path = LOGS_DIR / selected_name
        st.download_button(
            f"下载 {selected_name}",
            selected_path.read_bytes(),
            file_name=selected_name,
            use_container_width=True,
        )
        st.caption(f"文件大小：{selected_path.stat().st_size} bytes")
    with col2:
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
            st.code(read_text(selected_path, 60000), language="text")


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
