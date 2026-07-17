from fastapi.testclient import TestClient

from typofix_cn.api.app import create_app
from typofix_cn.config import Settings


def test_serves_built_frontend_when_configured(tmp_path) -> None:
    frontend = tmp_path / "frontend"
    (frontend / "assets").mkdir(parents=True)
    (frontend / "index.html").write_text("<!doctype html><div id='root'>Typofix</div>", encoding="utf-8")
    (frontend / "assets" / "app.js").write_text("console.log('ok')", encoding="utf-8")
    with TestClient(create_app(Settings(data_dir=tmp_path / "data", frontend_dir=frontend))) as client:
        assert client.get("/").status_code == 200
        assert "Typofix" in client.get("/history").text
        assert client.get("/assets/app.js").status_code == 200
        assert client.get("/api/v1/unknown").status_code == 404
