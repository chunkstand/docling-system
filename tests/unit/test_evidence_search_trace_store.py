from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

from app.services.evidence_search_trace_store import search_evidence_trace_integrity_payload


def test_trace_integrity_recomputes_package_via_builder_seam(monkeypatch) -> None:
    export_id = uuid4()
    search_request_id = uuid4()
    row = SimpleNamespace(
        id=export_id,
        search_request_id=search_request_id,
        package_sha256="package-sha",
        trace_sha256="trace-sha",
        export_status="completed",
        package_payload_json={
            "schema_name": "search_evidence_package",
            "package_sha256": "ignored",
            "trace_graph": {"trace_sha256": "trace-sha"},
        },
    )

    monkeypatch.setattr(
        "app.services.evidence_search_trace_store.build_search_evidence_package",
        lambda session, request_id: {
            "package_sha256": "package-sha",
            "trace_graph": {"trace_sha256": "trace-sha"},
        },
    )
    monkeypatch.setattr(
        "app.services.evidence_search_trace_store.search_trace_specs_from_package",
        lambda payload: ([{"node_key": "node"}], [{"edge_key": "edge"}], "trace-sha"),
    )
    monkeypatch.setattr(
        "app.services.evidence_search_trace_store.search_trace_graph_sha256",
        lambda nodes, edges: "trace-sha",
    )

    payload = search_evidence_trace_integrity_payload(None, row, [], [])

    assert payload["recomputed_package_sha256"] == "package-sha"
    assert payload["recomputed_trace_sha256"] == "trace-sha"
    assert payload["recomputed_package_hash_matches"] is True
    assert payload["recomputed_trace_hash_matches"] is True
