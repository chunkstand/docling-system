from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.db.models import SemanticGovernanceEventKind
from app.services import retrieval_learning_datasets


class FakeSession:
    def __init__(self) -> None:
        self.added: list[object] = []
        self.added_batches: list[list[object]] = []
        self.flush_count = 0

    def add(self, row: object) -> None:
        self.added.append(row)

    def add_all(self, rows) -> None:
        self.added_batches.append(list(rows))

    def flush(self) -> None:
        self.flush_count += 1


def test_normalize_retrieval_learning_source_types_defaults_and_deduplicates() -> None:
    assert retrieval_learning_datasets.normalize_retrieval_learning_source_types(None) == [
        "feedback",
        "replay",
    ]
    assert retrieval_learning_datasets.normalize_retrieval_learning_source_types(
        ["feedback", "replay", "feedback"]
    ) == ["feedback", "replay"]


def test_normalize_retrieval_learning_source_types_rejects_unknown_values() -> None:
    with pytest.raises(ValueError, match="Unsupported retrieval learning source_type"):
        retrieval_learning_datasets.normalize_retrieval_learning_source_types(["unknown"])


def test_materialize_retrieval_learning_dataset_records_release_scoped_governance_event(
    monkeypatch,
) -> None:
    session = FakeSession()
    now = datetime(2026, 5, 11, 12, 0, tzinfo=UTC)
    release_id = uuid4()
    evaluation_id = uuid4()
    governance_event_id = uuid4()
    recorded: dict[str, object] = {}

    monkeypatch.setattr(retrieval_learning_datasets, "utcnow", lambda: now)
    monkeypatch.setattr(
        retrieval_learning_datasets,
        "_collect_feedback_sources",
        lambda *_args, **_kwargs: ([], []),
    )

    def fake_record_semantic_governance_event(_session, **kwargs):
        recorded.update(kwargs)
        return SimpleNamespace(id=governance_event_id)

    monkeypatch.setattr(
        retrieval_learning_datasets,
        "record_semantic_governance_event",
        fake_record_semantic_governance_event,
    )

    response = retrieval_learning_datasets.materialize_retrieval_learning_dataset(
        session,
        limit=5,
        source_types=["feedback"],
        set_name="unit-fixture",
        created_by="unit-test",
        search_harness_evaluation_id=evaluation_id,
        search_harness_release_id=release_id,
    )

    assert response["source_types"] == ["feedback"]
    assert response["set_name"] == "unit-fixture"
    assert recorded["event_kind"] == (
        SemanticGovernanceEventKind.RETRIEVAL_TRAINING_RUN_MATERIALIZED.value
    )
    assert recorded["governance_scope"] == f"search_harness_release:{release_id}"
    assert recorded["search_harness_evaluation_id"] == evaluation_id
    assert recorded["search_harness_release_id"] == release_id
    assert session.added[1].semantic_governance_event_id == governance_event_id


def test_materialize_retrieval_learning_dataset_uses_judgment_set_scope_without_release_id(
    monkeypatch,
) -> None:
    session = FakeSession()
    now = datetime(2026, 5, 11, 12, 0, tzinfo=UTC)
    recorded: dict[str, object] = {}

    monkeypatch.setattr(retrieval_learning_datasets, "utcnow", lambda: now)
    monkeypatch.setattr(
        retrieval_learning_datasets,
        "_collect_feedback_sources",
        lambda *_args, **_kwargs: ([], []),
    )

    def fake_record_semantic_governance_event(_session, **kwargs):
        recorded.update(kwargs)
        return SimpleNamespace(id=uuid4())

    monkeypatch.setattr(
        retrieval_learning_datasets,
        "record_semantic_governance_event",
        fake_record_semantic_governance_event,
    )

    response = retrieval_learning_datasets.materialize_retrieval_learning_dataset(
        session,
        limit=5,
        source_types=["feedback"],
        created_by="unit-test",
    )

    assert recorded["governance_scope"] == f"retrieval_learning:{response['judgment_set_id']}"
