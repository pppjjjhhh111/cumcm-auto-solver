from pathlib import Path
from uuid import uuid4

from src.tools.report_exporter import ReportExporter


def test_report_exporter_docx_and_pdf_degrade_gracefully() -> None:
    root = Path(__file__).resolve().parents[1]
    reports_dir = root / "outputs" / "test_runs" / f"report_export_{uuid4().hex}" / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    md_path = reports_dir / "solution_report.md"
    md_path.write_text("# Title\n\n## Section\n\nBody text.", encoding="utf-8")

    result = ReportExporter(reports_dir).export_all(md_path, export_docx=True, export_pdf=True)

    assert result["docx"]["success"] is True or result["docx"].get("warning")
    assert result["pdf"]["success"] is True or result["pdf"].get("warning")
