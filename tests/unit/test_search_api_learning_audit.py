from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.errors import api_error
from app.api.main import app


def test_retrieval_learning_candidate_detail_route_returns_machine_readable_error(
    monkeypatch,
) -> None:
    candidate_evaluation_id = uuid4()
    monkeypatch.setattr(
        "app.api.routers.search.get_retrieval_learning_candidate_evaluation_detail",
        lambda session, lookup_candidate_id: (_ for _ in ()).throw(
            api_error(
                404,
                "retrieval_learning_candidate_evaluation_not_found",
                "Retrieval learning candidate evaluation not found.",
                candidate_evaluation_id=str(lookup_candidate_id),
            )
        ),
    )

    client = TestClient(app)
    response = client.get(
        f"/search/retrieval-learning/candidate-evaluations/{candidate_evaluation_id}"
    )

    assert response.status_code == 404
    assert response.json()["error_code"] == "retrieval_learning_candidate_evaluation_not_found"
    assert response.json()["error_context"]["candidate_evaluation_id"] == str(
        candidate_evaluation_id
    )


def test_retrieval_reranker_artifact_detail_route_returns_machine_readable_error(
    monkeypatch,
) -> None:
    artifact_id = uuid4()
    monkeypatch.setattr(
        "app.api.routers.search.get_retrieval_reranker_artifact_detail",
        lambda session, lookup_artifact_id: (_ for _ in ()).throw(
            api_error(
                404,
                "retrieval_reranker_artifact_not_found",
                "Retrieval reranker artifact not found.",
                artifact_id=str(lookup_artifact_id),
            )
        ),
    )

    client = TestClient(app)
    response = client.get(f"/search/retrieval-learning/reranker-artifacts/{artifact_id}")

    assert response.status_code == 404
    assert response.json()["error_code"] == "retrieval_reranker_artifact_not_found"
    assert response.json()["error_context"]["artifact_id"] == str(artifact_id)


def test_search_audit_bundle_detail_route_returns_machine_readable_error(
    monkeypatch,
) -> None:
    bundle_id = uuid4()
    monkeypatch.setattr(
        "app.api.routers.search.get_audit_bundle_export",
        lambda session, lookup_bundle_id, *, storage_service: (_ for _ in ()).throw(
            api_error(
                404,
                "audit_bundle_export_not_found",
                "Audit bundle export not found.",
                bundle_id=str(lookup_bundle_id),
            )
        ),
    )

    client = TestClient(app)
    response = client.get(f"/search/audit-bundles/{bundle_id}")

    assert response.status_code == 404
    assert response.json()["error_code"] == "audit_bundle_export_not_found"
    assert response.json()["error_context"]["bundle_id"] == str(bundle_id)


def test_search_audit_bundle_create_route_returns_machine_readable_signing_key_error(
    monkeypatch,
) -> None:
    release_id = uuid4()

    def raise_signing_key_missing(session, lookup_release_id, payload, *, storage_service):
        raise api_error(
            409,
            "audit_bundle_signing_key_missing",
            "DOCLING_SYSTEM_AUDIT_BUNDLE_SIGNING_KEY is required to export signed audit bundles.",
            release_id=str(lookup_release_id),
        )

    monkeypatch.setattr(
        "app.api.routers.search.create_search_harness_release_audit_bundle",
        raise_signing_key_missing,
    )

    client = TestClient(app)
    response = client.post(
        f"/search/harness-releases/{release_id}/audit-bundles",
        json={"created_by": "operator"},
    )

    assert response.status_code == 409
    assert response.json()["error_code"] == "audit_bundle_signing_key_missing"
    assert response.json()["error_context"]["release_id"] == str(release_id)


def test_search_audit_bundle_validation_receipt_latest_route_returns_machine_readable_error(
    monkeypatch,
) -> None:
    bundle_id = uuid4()
    monkeypatch.setattr(
        "app.api.routers.search.get_latest_audit_bundle_validation_receipt",
        lambda session, lookup_bundle_id, *, storage_service: (_ for _ in ()).throw(
            api_error(
                404,
                "audit_bundle_validation_receipt_not_found",
                "Audit bundle validation receipt not found.",
                bundle_id=str(lookup_bundle_id),
            )
        ),
    )

    client = TestClient(app)
    response = client.get(f"/search/audit-bundles/{bundle_id}/validation-receipts/latest")

    assert response.status_code == 404
    assert response.json()["error_code"] == "audit_bundle_validation_receipt_not_found"
    assert response.json()["error_context"]["bundle_id"] == str(bundle_id)


def test_search_audit_bundle_validation_receipt_detail_route_returns_machine_readable_error(
    monkeypatch,
) -> None:
    bundle_id = uuid4()
    receipt_id = uuid4()
    monkeypatch.setattr(
        "app.api.routers.search.get_audit_bundle_validation_receipt",
        lambda session, lookup_bundle_id, lookup_receipt_id, *, storage_service: (
            _ for _ in ()
        ).throw(
            api_error(
                404,
                "audit_bundle_validation_receipt_not_found",
                "Audit bundle validation receipt not found.",
                bundle_id=str(lookup_bundle_id),
                receipt_id=str(lookup_receipt_id),
            )
        ),
    )

    client = TestClient(app)
    response = client.get(
        f"/search/audit-bundles/{bundle_id}/validation-receipts/{receipt_id}"
    )

    assert response.status_code == 404
    assert response.json()["error_code"] == "audit_bundle_validation_receipt_not_found"
    assert response.json()["error_context"]["bundle_id"] == str(bundle_id)
    assert response.json()["error_context"]["receipt_id"] == str(receipt_id)


def test_retrieval_training_audit_bundle_latest_route_returns_machine_readable_error(
    monkeypatch,
) -> None:
    training_run_id = uuid4()
    monkeypatch.setattr(
        "app.api.routers.search.get_latest_retrieval_training_run_audit_bundle",
        lambda session, lookup_training_run_id, *, storage_service: (_ for _ in ()).throw(
            api_error(
                404,
                "retrieval_training_run_audit_bundle_not_found",
                "Retrieval training run audit bundle not found.",
                retrieval_training_run_id=str(lookup_training_run_id),
            )
        ),
    )

    client = TestClient(app)
    response = client.get(
        f"/search/retrieval-training-runs/{training_run_id}/audit-bundles/latest"
    )

    assert response.status_code == 404
    assert response.json()["error_code"] == "retrieval_training_run_audit_bundle_not_found"
    assert response.json()["error_context"]["retrieval_training_run_id"] == str(
        training_run_id
    )


def test_retrieval_training_audit_bundle_create_route_returns_machine_readable_error(
    monkeypatch,
) -> None:
    training_run_id = uuid4()
    monkeypatch.setattr(
        "app.api.routers.search.create_retrieval_training_run_audit_bundle",
        lambda session, lookup_training_run_id, payload, *, storage_service: (
            _ for _ in ()
        ).throw(
            api_error(
                409,
                "retrieval_training_run_not_completed",
                "Retrieval training run must be completed before exporting an audit bundle.",
                retrieval_training_run_id=str(lookup_training_run_id),
                status="failed",
            )
        ),
    )

    client = TestClient(app)
    response = client.post(
        f"/search/retrieval-training-runs/{training_run_id}/audit-bundles",
        json={"created_by": "operator"},
    )

    assert response.status_code == 409
    assert response.json()["error_code"] == "retrieval_training_run_not_completed"
    assert response.json()["error_context"]["retrieval_training_run_id"] == str(
        training_run_id
    )
