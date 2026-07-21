from __future__ import annotations

import io
import time
from pathlib import Path

from docx import Document
from fastapi.testclient import TestClient

from typofix_cn.api.app import create_app
from typofix_cn.config import Settings
from typofix_cn.correctors.base import CorrectionResult


class StubCorrector:
    def correct(self, inputs, **kwargs):
        return [CorrectionResult(key=item.key, source=item.text, findings=[]) for item in inputs]

    def correct_raw(self, texts, **kwargs):
        return [{"source": text, "target": text, "errors": [], "decisions": []} for text in texts]


def _docx_bytes() -> bytes:
    document = Document()
    document.add_paragraph("今天新情很好")
    stream = io.BytesIO()
    document.save(stream)
    return stream.getvalue()


def test_full_job_reuses_the_api_macbert_corrector(monkeypatch, tmp_path: Path) -> None:
    instances: list[StubCorrector] = []

    def factory(*args, **kwargs):
        instance = StubCorrector()
        instances.append(instance)
        return instance

    monkeypatch.setattr("typofix_cn.api.app.MacBertCorrector", factory)
    settings = Settings(data_dir=tmp_path / "data")

    with TestClient(create_app(settings)) as client:
        response = client.post(
            "/api/v1/jobs",
            files={"files": ("sample.docx", _docx_bytes(), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
            data={"mode": "full"},
        )
        assert response.status_code == 202
        job_id = response.json()["job_id"]
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            status = client.get(f"/api/v1/jobs/{job_id}").json()["status"]
            if status.startswith("completed") or status == "failed":
                break
            time.sleep(0.05)

    assert status.startswith("completed")
    assert len(instances) == 1
