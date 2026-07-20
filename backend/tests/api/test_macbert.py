from fastapi.testclient import TestClient

from typofix_cn.api.app import create_app
from typofix_cn.config import Settings


class StubRawCorrector:
    def correct_raw(self, texts):
        return [{"source": texts[0], "target": "今天心情很好", "errors": [["新", "心", 2]]}]


def test_macbert_text_test_returns_raw_model_output(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr("typofix_cn.api.app.MacBertCorrector", lambda _: StubRawCorrector())

    with TestClient(create_app(Settings(data_dir=tmp_path / "data"))) as client:
        response = client.post("/api/v1/macbert/test", json={"text": "今天新情很好"})

    assert response.status_code == 200
    assert response.json() == {
        "source": "今天新情很好",
        "target": "今天心情很好",
        "errors": [["新", "心", 2]],
    }


def test_macbert_text_test_rejects_blank_text(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr("typofix_cn.api.app.MacBertCorrector", lambda _: StubRawCorrector())

    with TestClient(create_app(Settings(data_dir=tmp_path / "data"))) as client:
        response = client.post("/api/v1/macbert/test", json={"text": "   "})

    assert response.status_code == 422
    assert response.json()["detail"]["message"] == "请输入要测试的文本"
