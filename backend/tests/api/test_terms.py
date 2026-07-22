from fastapi.testclient import TestClient

from typofix_cn.api.app import create_app
from typofix_cn.domain.enums import IssueCategory, IssueSource, Severity
from typofix_cn.domain.issues import Issue
from typofix_cn.domain.locations import TextLocation
from typofix_cn.domain.reports import AnalysisReport, DocumentResult, summarize
from typofix_cn.reports.html_report import HtmlReportWriter
from typofix_cn.reports.json_report import JsonReportWriter
from typofix_cn.config import Settings


def test_term_library_crud(tmp_path) -> None:
    with TestClient(create_app(Settings(data_dir=tmp_path / "data"))) as client:
        libraries = client.get("/api/v1/term-libraries").json()
        assert libraries[0]["name"] == "default"
        created = client.post("/api/v1/term-libraries", json={"name": "computer-science"})
        assert created.status_code == 201
        added = client.post("/api/v1/term-libraries/computer-science/terms", json={"term": "MacBERT"})
        assert added.status_code == 200
        assert added.json()["terms"] == ["MacBERT"]
        deleted = client.request("DELETE", "/api/v1/term-libraries/computer-science/terms", json={"term": "MacBERT"})
        assert deleted.status_code == 200
        assert deleted.json()["terms"] == []


def test_rematch_includes_library_added_from_report(tmp_path) -> None:
    with TestClient(create_app(Settings(data_dir=tmp_path / "data"))) as client:
        app = client.app
        manifest = app.state.jobs.create(["paper.docx"], mode="full", libraries=[])
        issue = Issue.create(
            source=IssueSource.MODEL,
            category=IssueCategory.TEXT_CORRECTION,
            type_code="SPELLING_TYPO",
            severity=Severity.ERROR,
            location=TextLocation(document_path="paper.docx", region="body", paragraph_index=0, sentence_index=0, start_offset=2, end_offset=3),
            original="做",
            suggestion="作",
            message="建议修改",
            context="麒麟操做系统",
        )
        report = AnalysisReport(job_id=manifest.job_id, mode="full", documents=[DocumentResult(document_path="paper.docx", status="completed")], issues=[issue], summary=summarize([issue]))
        JsonReportWriter().write(report, app.state.jobs.job_dir(manifest.job_id) / "report.json")
        HtmlReportWriter().write(report, app.state.jobs.job_dir(manifest.job_id) / "report.html")
        client.post("/api/v1/term-libraries/default/terms", json={"term": "麒麟操做系统"})

        response = client.post(f"/api/v1/jobs/{manifest.job_id}/rematch", json={"library": "default"})

        assert response.status_code == 200
        assert response.json()["summary"]["term_suppressed"] == 1
        assert app.state.jobs.get(manifest.job_id).selected_libraries == ["default"]
