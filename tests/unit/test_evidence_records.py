from __future__ import annotations

import uuid

from app.core.time import utcnow
from app.db.public.agent_tasks import KnowledgeOperatorInput, KnowledgeOperatorRun
from app.services import evidence
from app.services.evidence_records import (
    io_payload,
    operator_run_payload,
    select_by_ids,
    source_evidence_payloads,
)


def test_io_payload_stringifies_ids_and_drops_empty_links() -> None:
    now = utcnow()
    row = KnowledgeOperatorInput(
        id=uuid.uuid4(),
        operator_run_id=uuid.uuid4(),
        input_index=0,
        input_kind="query",
        source_table=None,
        source_id=None,
        artifact_path=None,
        artifact_sha256=None,
        payload_json={"query": "forest plan"},
        created_at=now,
    )

    payload = io_payload(row, kind_field="input_kind")

    assert payload == {
        "id": str(row.id),
        "operator_run_id": str(row.operator_run_id),
        "input_kind": "query",
        "payload": {"query": "forest plan"},
        "created_at": now,
    }


def test_operator_run_payload_preserves_existing_shape() -> None:
    now = utcnow()
    run = KnowledgeOperatorRun(
        id=uuid.uuid4(),
        operator_kind="retrieve",
        operator_name="hybrid_search",
        status="completed",
        config_sha256="config-sha",
        input_sha256="input-sha",
        output_sha256="output-sha",
        metrics_json={"result_count": 3},
        metadata_json={"profile": "default"},
        created_at=now,
    )

    payload = operator_run_payload(run, inputs=[], outputs=[])

    assert payload["id"] == run.id
    assert "operator_run_id" not in payload
    assert payload["operator_kind"] == "retrieve"
    assert payload["metrics"] == {"result_count": 3}
    assert payload["inputs"] == []
    assert payload["outputs"] == []


def test_evidence_facade_preserves_record_helper_aliases() -> None:
    assert evidence._operator_run_payload is operator_run_payload
    assert evidence._select_by_ids is select_by_ids
    assert evidence._source_evidence_payloads is source_evidence_payloads
