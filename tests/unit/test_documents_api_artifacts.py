from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.main import app
from app.db.public.ingest import DocumentRun
from app.db.session import get_db_session
from app.services.storage import StorageService


def test_run_failure_artifact_route_serves_json(monkeypatch, tmp_path: Path) -> None:
    storage_service = StorageService(storage_root=tmp_path / "storage")
    document_id = uuid4()
    run_id = uuid4()
    artifact_path = storage_service.get_failure_artifact_path(document_id, run_id)
    artifact_path.write_text('{"error":"boom"}')

    class FakeSession:
        def get(self, model, key):
            if model is DocumentRun and key == run_id:
                return SimpleNamespace(
                    id=run_id,
                    document_id=document_id,
                    failure_artifact_path="/tmp/ignored.json",
                )
            return None

        def close(self) -> None:
            return None

    monkeypatch.setattr("app.api.deps.get_storage_service", lambda: storage_service)
    monkeypatch.setattr("app.api.routers.documents.get_storage_service", lambda: storage_service)
    app.dependency_overrides[get_db_session] = lambda: FakeSession()
    try:
        client = TestClient(app)
        response = client.get(f"/runs/{run_id}/failure-artifact")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"error": "boom"}


def test_document_artifact_routes_return_404_for_missing_storage_owned_paths(
    monkeypatch, tmp_path: Path
) -> None:
    storage_service = StorageService(storage_root=tmp_path / "storage")
    document_id = uuid4()
    run_id = uuid4()
    table_id = uuid4()
    figure_id = uuid4()

    stale_run = SimpleNamespace(
        id=run_id,
        docling_json_path=str(tmp_path / "missing-docling.json"),
        yaml_path=str(tmp_path / "missing-document.yaml"),
    )
    stale_table = SimpleNamespace(
        id=table_id,
        run_id=run_id,
        document_id=document_id,
        table_index=0,
        json_path=str(tmp_path / "missing-table.json"),
        yaml_path=str(tmp_path / "missing-table.yaml"),
    )
    stale_figure = SimpleNamespace(
        id=figure_id,
        run_id=run_id,
        document_id=document_id,
        figure_index=0,
        json_path=str(tmp_path / "missing-figure.json"),
        yaml_path=str(tmp_path / "missing-figure.yaml"),
    )

    class FakeSession:
        def get(self, model, key):
            if model is DocumentRun and key == run_id:
                return stale_run
            if key == table_id:
                return stale_table
            if key == figure_id:
                return stale_figure
            return None

        def close(self) -> None:
            return None

    monkeypatch.setattr(
        "app.api.routers.documents.get_document_detail",
        lambda session, requested_document_id: SimpleNamespace(
            id=requested_document_id,
            active_run_id=run_id,
            has_json_artifact=True,
            has_yaml_artifact=True,
        ),
    )
    monkeypatch.setattr(
        "app.api.routers.documents.get_active_table_row",
        lambda session, requested_document_id, requested_table_id: stale_table
        if requested_document_id == document_id and requested_table_id == table_id
        else None,
    )
    monkeypatch.setattr(
        "app.api.routers.documents.get_active_figure_row",
        lambda session, requested_document_id, requested_figure_id: stale_figure
        if requested_document_id == document_id and requested_figure_id == figure_id
        else None,
    )
    monkeypatch.setattr("app.api.deps.get_storage_service", lambda: storage_service)
    monkeypatch.setattr("app.api.routers.documents.get_storage_service", lambda: storage_service)

    app.dependency_overrides[get_db_session] = lambda: FakeSession()
    try:
        client = TestClient(app)
        document_json = client.get(f"/documents/{document_id}/artifacts/json")
        document_yaml = client.get(f"/documents/{document_id}/artifacts/yaml")
        table_json = client.get(f"/documents/{document_id}/tables/{table_id}/artifacts/json")
        table_yaml = client.get(f"/documents/{document_id}/tables/{table_id}/artifacts/yaml")
        figure_json = client.get(f"/documents/{document_id}/figures/{figure_id}/artifacts/json")
        figure_yaml = client.get(f"/documents/{document_id}/figures/{figure_id}/artifacts/yaml")
    finally:
        app.dependency_overrides.clear()

    assert document_json.status_code == 404
    assert document_json.json()["error_code"] == "document_artifact_not_found"
    assert document_yaml.status_code == 404
    assert document_yaml.json()["error_code"] == "document_artifact_not_found"
    assert table_json.status_code == 404
    assert table_json.json()["error_code"] == "table_artifact_not_found"
    assert table_yaml.status_code == 404
    assert table_yaml.json()["error_code"] == "table_artifact_not_found"
    assert figure_json.status_code == 404
    assert figure_json.json()["error_code"] == "figure_artifact_not_found"
    assert figure_yaml.status_code == 404
    assert figure_yaml.json()["error_code"] == "figure_artifact_not_found"


def test_run_failure_artifact_route_returns_machine_readable_error_when_run_missing() -> None:
    run_id = uuid4()

    class FakeSession:
        def get(self, _model, _key):
            return None

        def close(self) -> None:
            return None

    app.dependency_overrides[get_db_session] = lambda: FakeSession()
    try:
        client = TestClient(app)
        response = client.get(f"/runs/{run_id}/failure-artifact")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json()["error_code"] == "document_run_not_found"


def test_run_failure_artifact_route_returns_machine_readable_error_when_artifact_missing(
    monkeypatch, tmp_path: Path
) -> None:
    storage_service = StorageService(storage_root=tmp_path / "storage")
    document_id = uuid4()
    run_id = uuid4()

    class FakeSession:
        def get(self, model, key):
            if model is DocumentRun and key == run_id:
                return SimpleNamespace(id=run_id, document_id=document_id)
            return None

        def close(self) -> None:
            return None

    monkeypatch.setattr("app.api.deps.get_storage_service", lambda: storage_service)
    monkeypatch.setattr("app.api.routers.documents.get_storage_service", lambda: storage_service)
    app.dependency_overrides[get_db_session] = lambda: FakeSession()
    try:
        client = TestClient(app)
        response = client.get(f"/runs/{run_id}/failure-artifact")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json()["error_code"] == "run_failure_artifact_not_found"


def test_document_artifact_routes_prefer_storage_owned_paths(monkeypatch, tmp_path: Path) -> None:
    storage_service = StorageService(storage_root=tmp_path / "storage")
    document_id = uuid4()
    run_id = uuid4()
    table_id = uuid4()
    figure_id = uuid4()

    storage_service.get_docling_json_path(document_id, run_id).write_text('{"kind":"document"}')
    storage_service.get_yaml_path(document_id, run_id).write_text("kind: document\n")
    storage_service.get_table_json_path(document_id, run_id, 0).write_text('{"kind":"table"}')
    storage_service.get_table_yaml_path(document_id, run_id, 0).write_text("kind: table\n")
    storage_service.get_figure_json_path(document_id, run_id, 0).write_text('{"kind":"figure"}')
    storage_service.get_figure_yaml_path(document_id, run_id, 0).write_text("kind: figure\n")

    run = SimpleNamespace(
        id=run_id,
        document_id=document_id,
        docling_json_path="/tmp/ignored-docling.json",
        yaml_path="/tmp/ignored-document.yaml",
    )
    table = SimpleNamespace(
        id=table_id,
        run_id=run_id,
        document_id=document_id,
        table_index=0,
        json_path="/tmp/ignored-table.json",
        yaml_path="/tmp/ignored-table.yaml",
    )
    figure = SimpleNamespace(
        id=figure_id,
        run_id=run_id,
        document_id=document_id,
        figure_index=0,
        json_path="/tmp/ignored-figure.json",
        yaml_path="/tmp/ignored-figure.yaml",
    )

    class FakeSession:
        def get(self, model, key):
            if model is DocumentRun and key == run_id:
                return run
            if key == table_id:
                return table
            if key == figure_id:
                return figure
            return None

        def close(self) -> None:
            return None

    monkeypatch.setattr(
        "app.api.routers.documents.get_document_detail",
        lambda session, requested_document_id: SimpleNamespace(
            id=requested_document_id,
            active_run_id=run_id,
            has_json_artifact=True,
            has_yaml_artifact=True,
        ),
    )
    monkeypatch.setattr(
        "app.api.routers.documents.get_active_table_row",
        lambda session, requested_document_id, requested_table_id: table
        if requested_document_id == document_id and requested_table_id == table_id
        else None,
    )
    monkeypatch.setattr(
        "app.api.routers.documents.get_active_figure_row",
        lambda session, requested_document_id, requested_figure_id: figure
        if requested_document_id == document_id and requested_figure_id == figure_id
        else None,
    )
    monkeypatch.setattr("app.api.deps.get_storage_service", lambda: storage_service)
    monkeypatch.setattr("app.api.routers.documents.get_storage_service", lambda: storage_service)

    app.dependency_overrides[get_db_session] = lambda: FakeSession()
    try:
        client = TestClient(app)
        assert client.get(f"/documents/{document_id}/artifacts/json").json() == {"kind": "document"}
        assert "kind: document" in client.get(f"/documents/{document_id}/artifacts/yaml").text
        assert client.get(f"/documents/{document_id}/tables/{table_id}/artifacts/json").json() == {
            "kind": "table"
        }
        assert (
            "kind: table"
            in client.get(f"/documents/{document_id}/tables/{table_id}/artifacts/yaml").text
        )
        assert client.get(
            f"/documents/{document_id}/figures/{figure_id}/artifacts/json"
        ).json() == {"kind": "figure"}
        assert (
            "kind: figure"
            in client.get(f"/documents/{document_id}/figures/{figure_id}/artifacts/yaml").text
        )
    finally:
        app.dependency_overrides.clear()
