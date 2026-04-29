from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

from app.services.evaluation_corpus_runner import run_eval_corpus_summary


def test_eval_corpus_runner_reuses_existing_auto_fixtures(monkeypatch) -> None:
    document_id = uuid4()
    run_id = uuid4()

    class FakeQuery:
        def order_by(self, *_args, **_kwargs):
            return self

        def all(self):
            return [
                SimpleNamespace(
                    id=document_id,
                    source_filename="autogen_doc.pdf",
                    active_run_id=run_id,
                    updated_at=None,
                )
            ]

    class FakeSession:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def query(self, _model):
            return FakeQuery()

        def get(self, model, key):
            if model.__name__ == "DocumentRun" and key == run_id:
                return SimpleNamespace(id=run_id)
            return None

    seen_evaluate_kwargs: list[dict] = []
    prewarm_state = {"calls": 0}

    def fake_evaluate_run(session, document, run, **kwargs):
        seen_evaluate_kwargs.append(kwargs)
        return SimpleNamespace(
            status="completed",
            fixture_name="auto_autogen_doc",
            summary_json={"query_count": 2, "passed_queries": 2},
        )

    monkeypatch.setattr(
        "app.services.evaluation_corpus_runner.get_session_factory",
        lambda: lambda: FakeSession(),
    )
    monkeypatch.setattr(
        "app.services.evaluation_corpus_runner.prewarm_eval_corpus_query_embeddings",
        lambda: prewarm_state.__setitem__("calls", prewarm_state["calls"] + 1),
    )
    monkeypatch.setattr(
        "app.services.evaluation_corpus_runner.evaluate_run",
        fake_evaluate_run,
    )

    output = run_eval_corpus_summary()

    assert output[0]["document_id"] == str(document_id)
    assert output[0]["run_id"] == str(run_id)
    assert output[0]["fixture_name"] == "auto_autogen_doc"
    assert seen_evaluate_kwargs == [{"refresh_auto_fixture": False}]
    assert prewarm_state["calls"] == 1
