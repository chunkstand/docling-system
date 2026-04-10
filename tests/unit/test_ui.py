from fastapi.testclient import TestClient

from app.api.main import app


def test_index_serves_ui() -> None:
    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 200
    assert "docling-system-ingest-file" in response.text
    assert "Active run tables" in response.text
    assert "/ui/app.js" in response.text
