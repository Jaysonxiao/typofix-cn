import time

from docx import Document
from docx.shared import Pt
from fastapi.testclient import TestClient

from typofix_cn.api.app import create_app
from typofix_cn.config import Settings


def make_docx(tmp_path):
    path = tmp_path / "论文.docx"
    document = Document()
    paragraph = document.add_paragraph("正文内容。")
    paragraph.paragraph_format.first_line_indent = Pt(24)
    document.save(path)
    return path


def test_create_rules_only_job_and_poll_to_completion(tmp_path) -> None:
    path = make_docx(tmp_path)
    with TestClient(create_app(Settings(data_dir=tmp_path / "data"))) as client:
        with path.open("rb") as stream:
            response = client.post(
                "/api/v1/jobs",
                data={"mode": "rules_only", "term_libraries": "default"},
                files=[("files", ("论文.docx", stream, "application/vnd.openxmlformats-officedocument.wordprocessingml.document"))],
            )
        assert response.status_code == 202
        job_id = response.json()["job_id"]
        deadline = time.time() + 5
        while time.time() < deadline:
            payload = client.get(f"/api/v1/jobs/{job_id}").json()
            if payload["status"] in {"completed", "completed_with_document_failures", "failed"}:
                break
            time.sleep(0.05)
        assert payload["status"] == "completed"
        report = client.get(f"/api/v1/jobs/{job_id}/report.json")
        assert report.status_code == 200
        assert report.json()["schema_version"] == 1


def test_invalid_upload_is_rejected(tmp_path) -> None:
    with TestClient(create_app(Settings(data_dir=tmp_path / "data"))) as client:
        response = client.post("/api/v1/jobs", data={"mode": "rules_only"}, files=[("files", ("note.txt", b"text", "text/plain"))])
    assert response.status_code == 422
