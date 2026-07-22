from pathlib import Path

from typofix_cn.domain.reports import AnalysisReport, summarize
from typofix_cn.reports.html_report import HtmlReportWriter
from typofix_cn.reports.json_report import JsonReportWriter
from typofix_cn.terms.matcher import TermMatcher


class RematchService:
    def rematch(self, json_path: Path, html_path: Path, libraries: dict[str, list[str]]) -> AnalysisReport:
        report = AnalysisReport.model_validate_json(json_path.read_text(encoding="utf-8"))
        reset = [issue.model_copy(update={"status": "actionable", "term_hits": []}) for issue in report.issues]
        updated_issues = TermMatcher(libraries).apply(reset)
        updated = report.model_copy(update={"issues": updated_issues, "summary": summarize(updated_issues)})
        JsonReportWriter().write(updated, json_path)
        HtmlReportWriter().write(updated, html_path)
        return updated
