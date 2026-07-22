from fastapi.testclient import TestClient

from typofix_cn.api.app import create_app
from typofix_cn.config import Settings


class StubRawCorrector:
    def __init__(self) -> None:
        self.calls = []

    def correct_raw(self, texts, *, detection_threshold=0.5, correction_threshold=0.3):
        self.calls.append((list(texts), detection_threshold, correction_threshold))
        return [{"source": texts[0], "target": "今天心情很好", "errors": [["新", "心", 2]], "decisions": []}]


def test_macbert_text_test_returns_raw_model_output(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr("typofix_cn.api.app.MacBertCorrector", lambda _, **kwargs: StubRawCorrector())

    with TestClient(create_app(Settings(data_dir=tmp_path / "data"))) as client:
        response = client.post("/api/v1/macbert/test", json={"text": "今天新情很好"})

    assert response.status_code == 200
    assert response.json() == {
        "source": "今天新情很好",
        "target": "今天心情很好",
        "errors": [["新", "心", 2]],
        "decisions": [],
    }


def test_macbert_text_test_rejects_blank_text(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr("typofix_cn.api.app.MacBertCorrector", lambda _, **kwargs: StubRawCorrector())

    with TestClient(create_app(Settings(data_dir=tmp_path / "data"))) as client:
        response = client.post("/api/v1/macbert/test", json={"text": "   "})

    assert response.status_code == 422
    assert response.json()["detail"]["message"] == "请输入要测试的文本"


def test_macbert_text_test_forwards_thresholds(monkeypatch, tmp_path) -> None:
    corrector = StubRawCorrector()
    monkeypatch.setattr("typofix_cn.api.app.MacBertCorrector", lambda _, **kwargs: corrector)

    with TestClient(create_app(Settings(data_dir=tmp_path / "data"))) as client:
        response = client.post(
            "/api/v1/macbert/test",
            json={"text": "今天新情很好", "detection_threshold": 0.45, "correction_threshold": 0.35},
        )

    assert response.status_code == 200
    assert corrector.calls == [(["今天新情很好"], 0.45, 0.35)]


def test_macbert_text_test_rejects_threshold_outside_range(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr("typofix_cn.api.app.MacBertCorrector", lambda _, **kwargs: StubRawCorrector())

    with TestClient(create_app(Settings(data_dir=tmp_path / "data"))) as client:
        response = client.post(
            "/api/v1/macbert/test",
            json={"text": "今天新情很好", "detection_threshold": 1.1},
        )

    assert response.status_code == 422
