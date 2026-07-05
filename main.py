from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from src.core.llm_client import (
    DeepSeekLLMClient,
    LLMClient,
)
from src.core.workflow import WorkflowRunner
from src.evaluation.batch_runner import BatchRunner
from src.rag.vector_store import KeywordVectorStore


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="CUMCM auto-solver research prototype.")
    parser.add_argument("--problem", default=None, help="Path to problem file: pdf, docx, txt, csv, or xlsx.")
    parser.add_argument("--data", default=None, help="Path to a data file or data directory.")
    parser.add_argument("--output-dir", default="outputs", help="Directory for logs, code, figures, and reports.")
    parser.add_argument("--max-repairs", type=int, default=3, help="Maximum automatic code repair attempts.")
    parser.add_argument("--llm", default="deepseek", help=argparse.SUPPRESS)
    parser.add_argument("--llm-config", default=None, help=argparse.SUPPRESS)
    parser.add_argument("--deepseek-model", default=None, help="DeepSeek model name.")
    parser.add_argument("--deepseek-base-url", default=None, help="DeepSeek OpenAI-compatible base URL.")
    parser.add_argument("--llm-strict", action="store_true", help="Fail workflow if a real LLM call fails.")
    parser.add_argument("--use-rag", action="store_true", help="Use local knowledge_base retrieval during strategy generation.")
    parser.add_argument("--kb-dir", default="knowledge_base", help="Local knowledge base directory.")
    parser.add_argument("--build-kb", default=None, help="Build a local RAG index for the given knowledge base directory.")
    parser.add_argument("--benchmark", default=None, help="Run benchmark tasks from a yaml/json config.")
    parser.add_argument("--export-docx", action="store_true", help="Export outputs/reports/solution_report.docx.")
    parser.add_argument("--export-pdf", action="store_true", help="Try to export outputs/reports/solution_report.pdf.")
    parser.add_argument("--disable-reflection", action="store_true", help="Skip ReflectionAgent and revision pass.")
    return parser


def build_llm_client(args: argparse.Namespace, project_root: Path) -> LLMClient:
    if not os.environ.get("DEEPSEEK_API_KEY"):
        raise RuntimeError("DEEPSEEK_API_KEY is required. Please set it before running the solver.")
    return DeepSeekLLMClient(
        model=args.deepseek_model,
        base_url=args.deepseek_base_url,
        strict=args.llm_strict,
    )


def build_kb(project_root: Path, kb_dir: Path) -> int:
    if not kb_dir.is_absolute():
        kb_dir = project_root / kb_dir
    store = KeywordVectorStore(kb_dir)
    summary = store.build_index()
    index_path = store.save_index()
    print(f"Knowledge base indexed: {summary['document_count']} chunks, {summary['term_count']} terms.")
    print(f"Index: {index_path}")
    return 0


def main() -> int:
    args = build_parser().parse_args()
    project_root = Path(__file__).resolve().parent

    if args.build_kb:
        return build_kb(project_root, Path(args.build_kb))

    try:
        llm_client = build_llm_client(args, project_root)
    except (ValueError, RuntimeError) as exc:
        print(f"LLM backend error: {exc}", file=sys.stderr)
        return 2

    if args.benchmark:
        result = BatchRunner(project_root=project_root, llm_client=llm_client).run(project_root / args.benchmark)
        print("Benchmark finished.")
        print(f"Summary: {result.get('summary_csv')}")
        print(f"Report: {result.get('benchmark_report')}")
        return 0

    if not args.problem:
        print("--problem is required unless --build-kb or --benchmark is used.", file=sys.stderr)
        return 2

    runner = WorkflowRunner(
        project_root=project_root,
        llm_client=llm_client,
        output_dir=project_root / args.output_dir,
        max_repairs=args.max_repairs,
        use_rag=args.use_rag,
        kb_dir=project_root / args.kb_dir,
        enable_reflection=not args.disable_reflection,
        export_docx=args.export_docx,
        export_pdf=args.export_pdf,
    )
    try:
        state = runner.run(Path(args.problem), Path(args.data) if args.data else None)
    except (NotImplementedError, RuntimeError, ValueError) as exc:
        print(f"Workflow error: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2

    print("Workflow finished.")
    print("LLM backend: deepseek")
    print(f"Report: {state.paper.get('report_path')}")
    print(f"Code dir: {state.code_dir}")
    print(f"Figures dir: {state.figures_dir}")
    print(f"Logs dir: {state.logs_dir}")
    print(f"Execution success: {state.execution_result.get('success')}")
    if state.exports:
        print(f"Exports: {state.exports}")
    return 0 if state.paper.get("report_path") else 1


if __name__ == "__main__":
    raise SystemExit(main())
