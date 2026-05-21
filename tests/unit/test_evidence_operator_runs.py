from __future__ import annotations

from uuid import uuid4

from app.db.public.agent_tasks import (
    KnowledgeOperatorInput,
    KnowledgeOperatorOutput,
    KnowledgeOperatorRun,
)
from app.services import evidence, evidence_operator_runs, retrieval_spans, search
from app.services.evidence_operator_runs import record_knowledge_operator_run


class FakeSession:
    def __init__(self) -> None:
        self.added: list[object] = []
        self.flush_count = 0

    def add(self, row: object) -> None:
        self.added.append(row)

    def flush(self) -> None:
        self.flush_count += 1


def test_evidence_facade_reexports_operator_run_recorder() -> None:
    assert evidence.record_knowledge_operator_run is record_knowledge_operator_run
    assert evidence_operator_runs.record_knowledge_operator_run is record_knowledge_operator_run


def test_search_and_retrieval_spans_use_focused_operator_run_module() -> None:
    assert search.record_knowledge_operator_run is record_knowledge_operator_run
    assert retrieval_spans.record_knowledge_operator_run is record_knowledge_operator_run


def test_record_knowledge_operator_run_persists_inputs_and_outputs() -> None:
    source_id = uuid4()
    target_id = uuid4()
    session = FakeSession()

    run = record_knowledge_operator_run(
        session,
        operator_kind="retrieve",
        operator_name="test_retriever",
        operator_version="v1",
        config={"limit": 5},
        input_payload={"query": "water"},
        output_payload={"result_count": 1},
        metrics={"latency_ms": 12},
        metadata={"origin": "unit"},
        inputs=[
            {
                "kind": "request",
                "source_table": "search_request_records",
                "source_id": str(source_id),
                "payload": {"query": "water"},
            }
        ],
        outputs=[
            {
                "output_kind": "candidate_set",
                "target_table": "search_request_results",
                "target_id": str(target_id),
                "payload": {"count": 1},
            }
        ],
    )

    operator_runs = [row for row in session.added if isinstance(row, KnowledgeOperatorRun)]
    input_rows = [row for row in session.added if isinstance(row, KnowledgeOperatorInput)]
    output_rows = [row for row in session.added if isinstance(row, KnowledgeOperatorOutput)]

    assert run is operator_runs[0]
    assert run.operator_kind == "retrieve"
    assert run.operator_name == "test_retriever"
    assert run.config_sha256
    assert run.input_sha256
    assert run.output_sha256
    assert run.metrics_json == {"latency_ms": 12}
    assert run.metadata_json == {"origin": "unit"}
    assert input_rows[0].operator_run_id == run.id
    assert input_rows[0].input_kind == "request"
    assert input_rows[0].source_id == source_id
    assert input_rows[0].payload_json == {"query": "water"}
    assert output_rows[0].operator_run_id == run.id
    assert output_rows[0].output_kind == "candidate_set"
    assert output_rows[0].target_id == target_id
    assert output_rows[0].payload_json == {"count": 1}
    assert session.flush_count == 2


def test_record_knowledge_operator_run_ignores_missing_session() -> None:
    assert (
        record_knowledge_operator_run(
            None,
            operator_kind="retrieve",
            operator_name="test_retriever",
        )
        is None
    )
