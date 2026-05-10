from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.errors import api_error
from app.api.main import app
from app.db.session import get_db_session
from app.services.storage import StorageService


def _local_semantic_settings(*, enabled: bool) -> SimpleNamespace:
    return SimpleNamespace(
        api_mode="local",
        api_host="127.0.0.1",
        api_port=8000,
        api_key=None,
        api_credentials_json=None,
        remote_api_capabilities=None,
        semantics_enabled=enabled,
    )


def _remote_semantic_settings(*, enabled: bool, capabilities: str | None = None) -> SimpleNamespace:
    return SimpleNamespace(
        api_mode="remote",
        api_host="0.0.0.0",
        api_port=8000,
        api_key="operator-secret",
        api_credentials_json=None,
        remote_api_capabilities=capabilities,
        semantics_enabled=enabled,
    )


def test_semantic_artifact_routes_return_404_for_missing_storage_owned_paths(
    monkeypatch, tmp_path: Path
) -> None:
    storage_service = StorageService(storage_root=tmp_path / "storage")
    document_id = uuid4()
    run_id = uuid4()

    semantic_pass = SimpleNamespace(
        run_id=run_id,
        artifact_schema_version="2.1",
        artifact_json_path=str(tmp_path / "missing-semantic.json"),
        artifact_yaml_path=str(tmp_path / "missing-semantic.yaml"),
    )

    class FakeSession:
        def close(self) -> None:
            return None

    monkeypatch.setattr(
        "app.api.routers.semantics.get_active_semantic_pass_row",
        lambda session, requested_document_id: semantic_pass,
    )
    monkeypatch.setattr("app.api.deps.get_settings", lambda: _local_semantic_settings(enabled=True))
    monkeypatch.setattr("app.api.deps.get_storage_service", lambda: storage_service)
    monkeypatch.setattr("app.api.routers.semantics.get_storage_service", lambda: storage_service)

    app.dependency_overrides[get_db_session] = lambda: FakeSession()
    try:
        client = TestClient(app)
        semantic_json = client.get(f"/documents/{document_id}/semantics/latest/artifacts/json")
        semantic_yaml = client.get(f"/documents/{document_id}/semantics/latest/artifacts/yaml")
    finally:
        app.dependency_overrides.clear()

    assert semantic_json.status_code == 404
    assert semantic_json.json()["error_code"] == "semantic_artifact_not_found"
    assert semantic_yaml.status_code == 404
    assert semantic_yaml.json()["error_code"] == "semantic_artifact_not_found"


def test_semantic_read_routes_return_conflict_when_feature_disabled(monkeypatch) -> None:
    document_id = uuid4()

    monkeypatch.setattr(
        "app.api.deps.get_settings", lambda: _local_semantic_settings(enabled=False)
    )
    monkeypatch.setattr(
        "app.api.routers.semantics.get_active_semantic_pass_detail",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("semantic detail lookup should stay disabled")
        ),
    )
    monkeypatch.setattr(
        "app.api.routers.semantics.get_active_semantic_continuity",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("semantic continuity lookup should stay disabled")
        ),
    )
    monkeypatch.setattr(
        "app.api.routers.semantics.get_active_semantic_pass_row",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("semantic artifact lookup should stay disabled")
        ),
    )

    client = TestClient(app)
    detail_response = client.get(f"/documents/{document_id}/semantics/latest")
    continuity_response = client.get(f"/documents/{document_id}/semantics/latest/continuity")
    artifact_json_response = client.get(f"/documents/{document_id}/semantics/latest/artifacts/json")
    artifact_yaml_response = client.get(f"/documents/{document_id}/semantics/latest/artifacts/yaml")

    assert detail_response.status_code == 409
    assert detail_response.json()["error_code"] == "semantics_disabled"
    assert continuity_response.status_code == 409
    assert continuity_response.json()["error_code"] == "semantics_disabled"
    assert artifact_json_response.status_code == 409
    assert artifact_json_response.json()["error_code"] == "semantics_disabled"
    assert artifact_yaml_response.status_code == 409
    assert artifact_yaml_response.json()["error_code"] == "semantics_disabled"


def test_latest_semantics_route_returns_machine_readable_error_when_pass_missing(
    monkeypatch,
) -> None:
    document_id = uuid4()
    monkeypatch.setattr("app.api.deps.get_settings", lambda: _local_semantic_settings(enabled=True))

    monkeypatch.setattr(
        "app.api.routers.semantics.get_active_semantic_pass_detail",
        lambda session, requested_document_id: (_ for _ in ()).throw(
            api_error(
                404,
                "semantic_pass_not_found",
                "Semantic pass not found.",
                document_id=str(requested_document_id),
            )
        ),
    )

    client = TestClient(app)
    response = client.get(f"/documents/{document_id}/semantics/latest")

    assert response.status_code == 404
    assert response.json()["error_code"] == "semantic_pass_not_found"


def test_latest_semantic_continuity_route_returns_machine_readable_error_when_pass_missing(
    monkeypatch,
) -> None:
    document_id = uuid4()
    monkeypatch.setattr("app.api.deps.get_settings", lambda: _local_semantic_settings(enabled=True))

    monkeypatch.setattr(
        "app.api.routers.semantics.get_active_semantic_continuity",
        lambda session, requested_document_id: (_ for _ in ()).throw(
            api_error(
                404,
                "semantic_pass_not_found",
                "Semantic pass not found.",
                document_id=str(requested_document_id),
            )
        ),
    )

    client = TestClient(app)
    response = client.get(f"/documents/{document_id}/semantics/latest/continuity")

    assert response.status_code == 404
    assert response.json()["error_code"] == "semantic_pass_not_found"


def test_latest_semantic_continuity_route_requires_inspect_capability_in_remote_mode(
    monkeypatch,
) -> None:
    document_id = uuid4()
    monkeypatch.setattr(
        "app.api.deps.get_settings",
        lambda: _remote_semantic_settings(enabled=True),
    )
    monkeypatch.setattr(
        "app.api.routers.semantics.get_active_semantic_continuity",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("remote capability gate should block before semantic continuity runs")
        ),
    )

    client = TestClient(app)
    response = client.get(
        f"/documents/{document_id}/semantics/latest/continuity",
        headers={"X-API-Key": "operator-secret"},
    )

    assert response.status_code == 403
    assert response.json()["error_code"] == "capability_not_allowed"


def test_semantic_assertion_review_route_returns_machine_readable_error_when_target_missing(
    monkeypatch,
) -> None:
    document_id = uuid4()
    assertion_id = uuid4()
    monkeypatch.setattr("app.api.deps.get_settings", lambda: _local_semantic_settings(enabled=True))

    monkeypatch.setattr(
        "app.api.routers.semantics.review_active_semantic_assertion",
        lambda session, requested_document_id, requested_assertion_id, **kwargs: (
            _ for _ in ()
        ).throw(
            api_error(
                404,
                "semantic_assertion_not_found",
                "Semantic assertion not found.",
                document_id=str(requested_document_id),
                assertion_id=str(requested_assertion_id),
            )
        ),
    )

    client = TestClient(app)
    response = client.post(
        f"/documents/{document_id}/semantics/latest/assertions/{assertion_id}/review",
        json={"review_status": "approved", "review_note": "missing", "reviewed_by": "tester"},
    )

    assert response.status_code == 404
    assert response.json()["error_code"] == "semantic_assertion_not_found"


def test_semantic_assertion_review_route_requires_remote_review_capability(monkeypatch) -> None:
    document_id = uuid4()
    assertion_id = uuid4()

    monkeypatch.setattr(
        "app.api.deps.get_settings",
        lambda: _remote_semantic_settings(enabled=True),
    )
    monkeypatch.setattr(
        "app.api.routers.semantics.review_active_semantic_assertion",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("remote capability gate should block before semantic assertion review")
        ),
    )

    client = TestClient(app)
    response = client.post(
        f"/documents/{document_id}/semantics/latest/assertions/{assertion_id}/review",
        headers={"X-API-Key": "operator-secret"},
        json={"review_status": "approved", "review_note": "missing", "reviewed_by": "tester"},
    )

    assert response.status_code == 403
    assert response.json()["error_code"] == "capability_not_allowed"


def test_semantic_category_binding_review_route_errors_when_target_missing(
    monkeypatch,
) -> None:
    document_id = uuid4()
    binding_id = uuid4()
    monkeypatch.setattr("app.api.deps.get_settings", lambda: _local_semantic_settings(enabled=True))

    monkeypatch.setattr(
        "app.api.routers.semantics.review_active_semantic_assertion_category_binding",
        lambda session, requested_document_id, requested_binding_id, **kwargs: (
            _ for _ in ()
        ).throw(
            api_error(
                404,
                "semantic_assertion_category_binding_not_found",
                "Semantic assertion category binding not found.",
                document_id=str(requested_document_id),
                binding_id=str(requested_binding_id),
            )
        ),
    )

    client = TestClient(app)
    response = client.post(
        f"/documents/{document_id}/semantics/latest/assertion-category-bindings/{binding_id}/review",
        json={"review_status": "approved", "review_note": "missing", "reviewed_by": "tester"},
    )

    assert response.status_code == 404
    assert response.json()["error_code"] == "semantic_assertion_category_binding_not_found"


def test_semantic_assertion_category_binding_review_route_requires_remote_review_capability(
    monkeypatch,
) -> None:
    document_id = uuid4()
    binding_id = uuid4()

    monkeypatch.setattr(
        "app.api.deps.get_settings",
        lambda: _remote_semantic_settings(enabled=True),
    )
    monkeypatch.setattr(
        "app.api.routers.semantics.review_active_semantic_assertion_category_binding",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError(
                "remote capability gate should block before semantic category binding review"
            )
        ),
    )

    client = TestClient(app)
    response = client.post(
        f"/documents/{document_id}/semantics/latest/assertion-category-bindings/{binding_id}/review",
        headers={"X-API-Key": "operator-secret"},
        json={"review_status": "approved", "review_note": "missing", "reviewed_by": "tester"},
    )

    assert response.status_code == 403
    assert response.json()["error_code"] == "capability_not_allowed"


def test_semantic_review_routes_return_conflict_when_feature_disabled(monkeypatch) -> None:
    document_id = uuid4()
    assertion_id = uuid4()
    binding_id = uuid4()

    monkeypatch.setattr(
        "app.api.deps.get_settings", lambda: _local_semantic_settings(enabled=False)
    )
    monkeypatch.setattr(
        "app.api.routers.semantics.review_active_semantic_assertion",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("semantic assertion review should stay disabled")
        ),
    )
    monkeypatch.setattr(
        "app.api.routers.semantics.review_active_semantic_assertion_category_binding",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("semantic category binding review should stay disabled")
        ),
    )

    client = TestClient(app)
    assertion_response = client.post(
        f"/documents/{document_id}/semantics/latest/assertions/{assertion_id}/review",
        json={"review_status": "approved", "review_note": "disabled", "reviewed_by": "tester"},
    )
    binding_response = client.post(
        f"/documents/{document_id}/semantics/latest/assertion-category-bindings/{binding_id}/review",
        json={"review_status": "approved", "review_note": "disabled", "reviewed_by": "tester"},
    )

    assert assertion_response.status_code == 409
    assert assertion_response.json()["error_code"] == "semantics_disabled"
    assert binding_response.status_code == 409
    assert binding_response.json()["error_code"] == "semantics_disabled"


def test_semantic_artifact_routes_prefer_storage_owned_paths(monkeypatch, tmp_path: Path) -> None:
    storage_service = StorageService(storage_root=tmp_path / "storage")
    document_id = uuid4()
    run_id = uuid4()

    storage_service.get_semantic_json_path(document_id, run_id, "2.1").write_text(
        '{"kind":"semantic"}'
    )
    storage_service.get_semantic_yaml_path(document_id, run_id, "2.1").write_text(
        "kind: semantic\n"
    )

    semantic_pass = SimpleNamespace(
        run_id=run_id,
        artifact_schema_version="2.1",
        artifact_json_path="/tmp/ignored-semantic.json",
        artifact_yaml_path="/tmp/ignored-semantic.yaml",
    )

    class FakeSession:
        def close(self) -> None:
            return None

    monkeypatch.setattr(
        "app.api.routers.semantics.get_active_semantic_pass_row",
        lambda session, requested_document_id: semantic_pass,
    )
    monkeypatch.setattr("app.api.deps.get_settings", lambda: _local_semantic_settings(enabled=True))
    monkeypatch.setattr("app.api.deps.get_storage_service", lambda: storage_service)
    monkeypatch.setattr("app.api.routers.semantics.get_storage_service", lambda: storage_service)

    app.dependency_overrides[get_db_session] = lambda: FakeSession()
    try:
        client = TestClient(app)
        assert client.get(f"/documents/{document_id}/semantics/latest/artifacts/json").json() == {
            "kind": "semantic"
        }
        assert (
            "kind: semantic"
            in client.get(f"/documents/{document_id}/semantics/latest/artifacts/yaml").text
        )
    finally:
        app.dependency_overrides.clear()
