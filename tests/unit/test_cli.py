from __future__ import annotations

import json
import sys
from uuid import uuid4

import app.cli as cli


def test_materialize_retrieval_learning_dataset_cli_prints_summary(
    monkeypatch, capsys
) -> None:
    class FakeSession:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def commit(self):
            return None

    release_id = uuid4()
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "docling-system-materialize-retrieval-learning",
            "--limit",
            "7",
            "--source-type",
            "feedback",
            "--set-name",
            "operator-set",
            "--created-by",
            "tester",
            "--search-harness-release-id",
            str(release_id),
        ],
    )
    monkeypatch.setattr("app.cli.get_session_factory", lambda: lambda: FakeSession())

    def fake_materialize(session, **kwargs):
        assert kwargs["limit"] == 7
        assert kwargs["source_types"] == ["feedback"]
        assert kwargs["set_name"] == "operator-set"
        assert kwargs["created_by"] == "tester"
        assert kwargs["search_harness_release_id"] == release_id
        return {
            "judgment_set_id": str(uuid4()),
            "summary": {"judgment_count": 3, "hard_negative_count": 1},
        }

    monkeypatch.setattr(
        "app.cli.materialize_retrieval_learning_dataset",
        fake_materialize,
    )

    cli.run_materialize_retrieval_learning_dataset()

    output = json.loads(capsys.readouterr().out.strip())
    assert output["summary"]["judgment_count"] == 3
    assert output["summary"]["hard_negative_count"] == 1


def test_materialize_retrieval_learning_dataset_cli_accepts_replay_alert_corpus_source(
    monkeypatch,
    capsys,
) -> None:
    class FakeSession:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def commit(self):
            return None

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "docling-system-materialize-retrieval-learning",
            "--source-type",
            "claim_support_replay_alert_corpus",
        ],
    )
    monkeypatch.setattr("app.cli.get_session_factory", lambda: lambda: FakeSession())

    def fake_materialize(session, **kwargs):
        assert kwargs["source_types"] == ["claim_support_replay_alert_corpus"]
        return {
            "judgment_set_id": str(uuid4()),
            "summary": {"judgment_count": 1, "hard_negative_count": 1},
        }

    monkeypatch.setattr(
        "app.cli.materialize_retrieval_learning_dataset",
        fake_materialize,
    )

    cli.run_materialize_retrieval_learning_dataset()

    output = json.loads(capsys.readouterr().out.strip())
    assert output["summary"]["judgment_count"] == 1
