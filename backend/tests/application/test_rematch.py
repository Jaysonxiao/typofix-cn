from typofix_cn.domain.enums import IssueCategory, IssueSource, Severity
from typofix_cn.domain.issues import Issue
from typofix_cn.domain.locations import TextLocation
from typofix_cn.domain.reports import AnalysisReport, DocumentResult, summarize
from typofix_cn.reports.html_report import HtmlReportWriter
from typofix_cn.reports.json_report import JsonReportWriter
from typofix_cn.application.rematch import RematchService


def test_rematch_suppresses_model_issue_without_new_model_call(tmp_path) -> None:
    issue = Issue.create(
        source=IssueSource.MODEL,
        category=IssueCategory.TEXT_CORRECTION,
        type_code="SPELLING_TYPO",
        severity=Severity.ERROR,
        location=TextLocation(document_path="论文.docx", region="body", paragraph_index=0, sentence_index=0, start_offset=2, end_offset=3),
        original="做",
        suggestion="作",
        message="建议修改",
        context="支持麒麟操做系统。",
    )
    report = AnalysisReport(job_id="job-1", mode="full", documents=[DocumentResult(document_path="论文.docx", status="completed")], issues=[issue], summary=summarize([issue]))
    json_path = tmp_path / "report.json"
    html_path = tmp_path / "report.html"
    JsonReportWriter().write(report, json_path)
    HtmlReportWriter().write(report, html_path)

    result = RematchService().rematch(json_path, html_path, {"default": ["麒麟操做系统"]})

    assert result.issues[0].status == "term_suppressed"
    assert result.issues[0].issue_id == issue.issue_id
