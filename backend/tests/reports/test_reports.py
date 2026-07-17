import json

from typofix_cn.domain.enums import IssueCategory, IssueSource, Severity
from typofix_cn.domain.issues import Issue
from typofix_cn.domain.locations import TextLocation
from typofix_cn.domain.reports import AnalysisReport, DocumentResult, summarize
from typofix_cn.reports.html_report import HtmlReportWriter
from typofix_cn.reports.json_report import JsonReportWriter


def report() -> AnalysisReport:
    issue = Issue.create(
        source=IssueSource.RULE,
        category=IssueCategory.TEXT_CORRECTION,
        type_code="REPEATED_WORD",
        severity=Severity.WARNING,
        location=TextLocation(document_path="论文.docx", region="body", paragraph_index=0, sentence_index=0, start_offset=0, end_offset=1),
        original="<script>alert(1)</script>",
        suggestion=None,
        message="原文包含脚本片段",
        context="<script>alert(1)</script>",
    )
    return AnalysisReport(job_id="job-1", mode="rules_only", documents=[DocumentResult(document_path="论文.docx", status="completed", issue_ids=[issue.issue_id])], issues=[issue], summary=summarize([issue]))


def test_report_outputs_versioned_json_and_safe_offline_html(tmp_path) -> None:
    JsonReportWriter().write(report(), tmp_path / "report.json")
    HtmlReportWriter().write(report(), tmp_path / "report.html")
    payload = json.loads((tmp_path / "report.json").read_text("utf-8"))
    html = (tmp_path / "report.html").read_text("utf-8")
    assert payload["schema_version"] == 1
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
    assert "fetch(" not in html
