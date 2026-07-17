from fastapi.testclient import TestClient

from typofix_cn.api.app import create_app
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
