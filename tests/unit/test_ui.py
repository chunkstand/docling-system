from fastapi.testclient import TestClient

from app.api.main import app


def test_index_serves_ui() -> None:
    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 200
    assert "Docling System" in response.text
    assert "Grounded Answer Workspace" in response.text
    assert "Live ingestion and telemetry" in response.text
    assert "Corpus quality state" in response.text
    assert "Logical tables" in response.text
    assert "Recent processing attempts" in response.text
    assert "Failed runs by stage will appear here." in response.text
    assert "Mined evaluation candidates will appear here." in response.text
    assert "Search and feedback trends will appear here." in response.text
    assert "Replay suite runs will appear here." in response.text
    assert "Harness" in response.text
    assert "Run replay" in response.text
    assert "Compare runs" in response.text
    assert "Replay comparison will appear here." in response.text
    assert "Replay drilldown will appear here." in response.text
    assert "Clear selection" in response.text
    assert "/ui/app.js" in response.text
