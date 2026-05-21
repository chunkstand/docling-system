from __future__ import annotations

import json
import sys
from types import SimpleNamespace
from uuid import uuid4

from app.cli_commands import search_harness_audit as audit_commands


def test_search_harness_release_audit_bundle_cli_prints_bundle(monkeypatch, capsys) -> None:
    class FakeSession:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def commit(self):
            return None

    class FakeStorageService:
        pass

    release_id = uuid4()
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "docling-system-search-harness-release-audit-bundle",
            str(release_id),
            "--created-by",
            "tester",
        ],
    )

    def fake_create(session, requested_release_id, request, *, storage_service):
        assert requested_release_id == release_id
        assert request.created_by == "tester"
        assert isinstance(storage_service, FakeStorageService)
        return SimpleNamespace(
            model_dump=lambda mode="json": {
                "release_id": str(requested_release_id),
                "created_by": request.created_by,
            }
        )

    audit_commands.run_search_harness_release_audit_bundle(
        session_factory_func=lambda: lambda: FakeSession(),
        storage_service_factory=FakeStorageService,
        create_search_harness_release_audit_bundle_func=fake_create,
    )

    output = json.loads(capsys.readouterr().out.strip())
    assert output["release_id"] == str(release_id)
    assert output["created_by"] == "tester"


def test_retrieval_training_run_audit_bundle_cli_prints_bundle(monkeypatch, capsys) -> None:
    class FakeSession:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def commit(self):
            return None

    class FakeStorageService:
        pass

    training_run_id = uuid4()
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "docling-system-retrieval-training-run-audit-bundle",
            str(training_run_id),
            "--created-by",
            "tester",
        ],
    )

    def fake_create(session, requested_training_run_id, request, *, storage_service):
        assert requested_training_run_id == training_run_id
        assert request.created_by == "tester"
        assert isinstance(storage_service, FakeStorageService)
        return SimpleNamespace(
            model_dump=lambda mode="json": {
                "training_run_id": str(requested_training_run_id),
                "created_by": request.created_by,
            }
        )

    audit_commands.run_retrieval_training_run_audit_bundle(
        session_factory_func=lambda: lambda: FakeSession(),
        storage_service_factory=FakeStorageService,
        create_retrieval_training_run_audit_bundle_func=fake_create,
    )

    output = json.loads(capsys.readouterr().out.strip())
    assert output["training_run_id"] == str(training_run_id)
    assert output["created_by"] == "tester"


def test_audit_bundle_validation_receipt_cli_prints_receipt(monkeypatch, capsys) -> None:
    class FakeSession:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def commit(self):
            return None

    class FakeStorageService:
        pass

    bundle_id = uuid4()
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "docling-system-audit-bundle-validation-receipt",
            str(bundle_id),
            "--created-by",
            "tester",
        ],
    )

    def fake_create(session, requested_bundle_id, request, *, storage_service):
        assert requested_bundle_id == bundle_id
        assert request.created_by == "tester"
        assert isinstance(storage_service, FakeStorageService)
        return SimpleNamespace(
            model_dump=lambda mode="json": {
                "bundle_id": str(requested_bundle_id),
                "created_by": request.created_by,
            }
        )

    audit_commands.run_audit_bundle_validation_receipt(
        session_factory_func=lambda: lambda: FakeSession(),
        storage_service_factory=FakeStorageService,
        create_audit_bundle_validation_receipt_func=fake_create,
    )

    output = json.loads(capsys.readouterr().out.strip())
    assert output["bundle_id"] == str(bundle_id)
    assert output["created_by"] == "tester"
