from __future__ import annotations

from contextlib import contextmanager
from types import SimpleNamespace

from fastapi import HTTPException

from app.services.idempotency import get_idempotent_response, store_idempotent_response


class FakeExecuteResult:
    def __init__(self, row) -> None:
        self.row = row

    def scalar_one_or_none(self):
        return self.row


class FakeSession:
    def __init__(self, row=None) -> None:
        self.row = row
        self.pending_row = None

    def execute(self, _statement):
        return FakeExecuteResult(self.row)

    @contextmanager
    def begin_nested(self):
        yield

    def add(self, row) -> None:
        self.pending_row = row

    def flush(self) -> None:
        if self.pending_row is not None:
            self.row = self.pending_row
            self.pending_row = None


def test_get_idempotent_response_returns_stored_payload() -> None:
    session = FakeSession(
        row=SimpleNamespace(
            scope="documents.create",
            idempotency_key="doc-create-1",
            request_fingerprint="sha256:abc",
            status_code=202,
            response_json={"document_id": "doc-1", "status": "queued"},
        )
    )

    stored = get_idempotent_response(
        session,
        scope="documents.create",
        idempotency_key="doc-create-1",
        request_fingerprint="sha256:abc",
    )

    assert stored == ({"document_id": "doc-1", "status": "queued"}, 202)


def test_get_idempotent_response_rejects_reused_key_for_different_request() -> None:
    session = FakeSession(
        row=SimpleNamespace(
            scope="documents.create",
            idempotency_key="doc-create-1",
            request_fingerprint="sha256:abc",
            status_code=202,
            response_json={"document_id": "doc-1", "status": "queued"},
        )
    )

    try:
        get_idempotent_response(
            session,
            scope="documents.create",
            idempotency_key="doc-create-1",
            request_fingerprint="sha256:def",
        )
    except HTTPException as exc:
        assert exc.status_code == 409
        assert exc.detail["code"] == "idempotency_key_reused"
    else:
        raise AssertionError("Expected mismatched fingerprints to reject the reused key")


def test_store_idempotent_response_updates_existing_row() -> None:
    row = SimpleNamespace(
        scope="documents.reprocess",
        idempotency_key="doc-reprocess-1",
        request_fingerprint="document:doc-1",
        status_code=202,
        response_json={"run_id": "old-run"},
    )
    session = FakeSession(row=row)

    store_idempotent_response(
        session,
        scope="documents.reprocess",
        idempotency_key="doc-reprocess-1",
        request_fingerprint="document:doc-1",
        response_payload={"run_id": "new-run"},
        status_code=202,
    )

    assert row.response_json == {"run_id": "new-run"}


def test_store_idempotent_response_inserts_new_row() -> None:
    session = FakeSession()

    store_idempotent_response(
        session,
        scope="documents.create",
        idempotency_key="doc-create-1",
        request_fingerprint="sha256:abc",
        response_payload={"document_id": "doc-1"},
        status_code=202,
    )

    assert session.row is not None
    assert session.row.scope == "documents.create"
    assert session.row.idempotency_key == "doc-create-1"
    assert session.row.response_json == {"document_id": "doc-1"}
