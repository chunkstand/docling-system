from __future__ import annotations

from collections.abc import Iterable
from typing import Any
from uuid import UUID

from app.core.json_utils import json_object_payload as _json_payload
from app.services.evidence_common import payload_sha256, trace_payload_sha256
from app.services.evidence_common import trace_node_key as _trace_node_key
from app.services.evidence_common import uuid_or_none_safe as _uuid_or_none_safe


def search_evidence_provenance_edges(
    *,
    search_request_id: UUID,
    source_evidence: list[dict],
) -> list[dict]:
    edges: list[dict] = []
    for item in source_evidence:
        search_result_id = item.get("search_request_result_id")
        if search_result_id:
            edge_payload = {
                "edge_type": "search_request_selected_result",
                "search_request_id": str(search_request_id),
                "search_request_result_id": str(search_result_id),
            }
            edges.append(
                {
                    **edge_payload,
                    "from": {"table": "search_requests", "id": str(search_request_id)},
                    "to": {"table": "search_request_results", "id": str(search_result_id)},
                    "derivation_sha256": payload_sha256(edge_payload),
                }
            )
        for span in item.get("retrieval_evidence_spans", []):
            result_span_id = span.get("search_request_result_span_id")
            source_span_id = span.get("retrieval_evidence_span_id")
            if search_result_id and result_span_id:
                edge_payload = {
                    "edge_type": "selected_span_supports_search_result",
                    "search_request_result_span_id": str(result_span_id),
                    "search_request_result_id": str(search_result_id),
                    "score_kind": span.get("score_kind"),
                }
                edges.append(
                    {
                        **edge_payload,
                        "from": {
                            "table": "search_request_result_spans",
                            "id": str(result_span_id),
                        },
                        "to": {"table": "search_request_results", "id": str(search_result_id)},
                        "derivation_sha256": payload_sha256(edge_payload),
                    }
                )
            if source_span_id and result_span_id:
                edge_payload = {
                    "edge_type": "retrieval_span_cited_as_selected_span",
                    "retrieval_evidence_span_id": str(source_span_id),
                    "search_request_result_span_id": str(result_span_id),
                    "content_sha256": span.get("content_sha256"),
                }
                edges.append(
                    {
                        **edge_payload,
                        "from": {"table": "retrieval_evidence_spans", "id": str(source_span_id)},
                        "to": {
                            "table": "search_request_result_spans",
                            "id": str(result_span_id),
                        },
                        "derivation_sha256": payload_sha256(edge_payload),
                    }
                )
            for vector in span.get("late_interaction_multivectors", []):
                span_vector_id = vector.get("span_vector_id")
                if span_vector_id and result_span_id:
                    edge_payload = {
                        "edge_type": "span_vector_matched_selected_span",
                        "span_vector_id": str(span_vector_id),
                        "search_request_result_span_id": str(result_span_id),
                        "content_sha256": vector.get("content_sha256"),
                        "embedding_sha256": vector.get("embedding_sha256"),
                    }
                    edges.append(
                        {
                            **edge_payload,
                            "from": {
                                "table": "retrieval_evidence_span_multivectors",
                                "id": str(span_vector_id),
                            },
                            "to": {
                                "table": "search_request_result_spans",
                                "id": str(result_span_id),
                            },
                            "derivation_sha256": payload_sha256(edge_payload),
                        }
                    )
                for link in vector.get("generation_operator_runs", []):
                    generation_operator_run_id = link.get("generation_operator_run_id")
                    if source_span_id and generation_operator_run_id:
                        edge_payload = {
                            "edge_type": "source_span_input_to_multivector_generation",
                            "retrieval_evidence_span_id": str(source_span_id),
                            "generation_operator_run_id": str(generation_operator_run_id),
                            "content_sha256": span.get("content_sha256"),
                        }
                        edges.append(
                            {
                                **edge_payload,
                                "from": {
                                    "table": "retrieval_evidence_spans",
                                    "id": str(source_span_id),
                                },
                                "to": {
                                    "table": "knowledge_operator_runs",
                                    "id": str(generation_operator_run_id),
                                },
                                "derivation_sha256": payload_sha256(edge_payload),
                            }
                        )
                    if generation_operator_run_id and span_vector_id:
                        edge_payload = {
                            "edge_type": "multivector_generation_output",
                            "generation_operator_run_id": str(generation_operator_run_id),
                            "span_vector_id": str(span_vector_id),
                            "generation_output_id": str(link.get("generation_output_id")),
                            "generation_output_sha256": link.get("generation_output_sha256"),
                        }
                        edges.append(
                            {
                                **edge_payload,
                                "from": {
                                    "table": "knowledge_operator_runs",
                                    "id": str(generation_operator_run_id),
                                },
                                "to": {
                                    "table": "retrieval_evidence_span_multivectors",
                                    "id": str(span_vector_id),
                                },
                                "derivation_sha256": payload_sha256(edge_payload),
                            }
                        )
    return edges


_SEARCH_TRACE_NODE_KIND_BY_TABLE = {
    "knowledge_operator_runs": "operator_run",
    "search_requests": "search_request",
    "search_request_results": "search_result",
    "search_request_result_spans": "selected_retrieval_span",
    "retrieval_evidence_spans": "retrieval_evidence_span",
    "retrieval_evidence_span_multivectors": "retrieval_evidence_span_multivector",
}


def _put_search_trace_node(
    nodes: dict[str, dict[str, Any]],
    *,
    source_table: str,
    source_ref: Any,
    node_kind: str | None = None,
    source_id: UUID | None = None,
    payload: dict[str, Any] | None = None,
) -> str:
    normalized_source_ref = str(source_ref)
    key = _trace_node_key(source_table, normalized_source_ref)
    node_payload = {
        "source_table": source_table,
        "source_ref": normalized_source_ref,
        **_json_payload(payload),
    }
    if source_id is not None:
        node_payload["source_id"] = str(source_id)
    existing = nodes.get(key)
    if existing is not None and not existing["payload"].get("placeholder"):
        return key
    nodes[key] = {
        "node_key": key,
        "node_kind": node_kind
        or _SEARCH_TRACE_NODE_KIND_BY_TABLE.get(source_table, source_table),
        "source_table": source_table,
        "source_id": source_id,
        "source_ref": normalized_source_ref,
        "content_sha256": trace_payload_sha256(node_payload),
        "payload": node_payload,
    }
    return key


def _put_search_trace_node_from_id(
    nodes: dict[str, dict[str, Any]],
    *,
    source_table: str,
    source_id: Any,
    node_kind: str | None = None,
    payload: dict[str, Any] | None = None,
) -> str | None:
    parsed_source_id = _uuid_or_none_safe(source_id)
    if parsed_source_id is None:
        return None
    return _put_search_trace_node(
        nodes,
        source_table=source_table,
        source_ref=parsed_source_id,
        source_id=parsed_source_id,
        node_kind=node_kind,
        payload=payload,
    )


def _put_search_trace_node_from_ref(
    nodes: dict[str, dict[str, Any]],
    ref: dict[str, Any],
) -> str:
    source_table = str(ref.get("table") or "unknown")
    source_ref = ref.get("id") or ref.get("sha256") or ref.get("ref") or "unknown"
    source_id = _uuid_or_none_safe(ref.get("id"))
    return _put_search_trace_node(
        nodes,
        source_table=source_table,
        source_ref=source_ref,
        source_id=source_id,
        payload={"placeholder": True, "ref": ref},
    )


def _put_search_trace_edge(
    edges: list[dict[str, Any]],
    *,
    edge_key: str,
    edge_kind: str,
    from_node_key: str | None,
    to_node_key: str | None,
    derivation_sha256: str | None = None,
    payload: dict[str, Any] | None = None,
) -> None:
    if not from_node_key or not to_node_key:
        return
    if any(edge.get("edge_key") == edge_key for edge in edges):
        return
    edge_payload = {
        "edge_kind": edge_kind,
        "from_node_key": from_node_key,
        "to_node_key": to_node_key,
        **_json_payload(payload),
    }
    if derivation_sha256:
        edge_payload["derivation_sha256"] = derivation_sha256
    edges.append(
        {
            "edge_key": edge_key,
            "edge_kind": edge_kind,
            "from_node_key": from_node_key,
            "to_node_key": to_node_key,
            "derivation_sha256": derivation_sha256,
            "content_sha256": trace_payload_sha256(edge_payload),
            "payload": edge_payload,
        }
    )


def _search_trace_graph_payload(
    nodes: Iterable[dict[str, Any]],
    edges: Iterable[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "schema_name": "search_evidence_trace_graph",
        "schema_version": "1.0",
        "nodes": [
            {
                "node_key": node["node_key"],
                "node_kind": node["node_kind"],
                "source_table": node.get("source_table"),
                "source_id": str(node["source_id"]) if node.get("source_id") else None,
                "source_ref": node.get("source_ref"),
                "content_sha256": node["content_sha256"],
                "payload": _json_payload(node.get("payload")),
            }
            for node in sorted(nodes, key=lambda item: item["node_key"])
        ],
        "edges": [
            {
                "edge_key": edge["edge_key"],
                "edge_kind": edge["edge_kind"],
                "from_node_key": edge["from_node_key"],
                "to_node_key": edge["to_node_key"],
                "derivation_sha256": edge.get("derivation_sha256"),
                "content_sha256": edge["content_sha256"],
                "payload": _json_payload(edge.get("payload")),
            }
            for edge in sorted(edges, key=lambda item: item["edge_key"])
        ],
    }


def search_trace_graph_sha256(
    nodes: Iterable[dict[str, Any]],
    edges: Iterable[dict[str, Any]],
) -> str:
    return str(payload_sha256(_search_trace_graph_payload(nodes, edges)))


def build_search_evidence_trace_graph(package: dict[str, Any]) -> dict[str, Any]:
    nodes: dict[str, dict[str, Any]] = {}
    edges: list[dict[str, Any]] = []
    search_request = package.get("search_request") or {}
    search_request_id = search_request.get("id")
    _put_search_trace_node_from_id(
        nodes,
        source_table="search_requests",
        source_id=search_request_id,
        payload=search_request,
    )
    for operator_run in package.get("operator_runs") or []:
        _put_search_trace_node_from_id(
            nodes,
            source_table="knowledge_operator_runs",
            source_id=operator_run.get("operator_run_id"),
            payload=operator_run,
        )
    for item in package.get("source_evidence") or []:
        result_id = item.get("search_request_result_id")
        _put_search_trace_node_from_id(
            nodes,
            source_table="search_request_results",
            source_id=result_id,
            payload={
                "search_request_result_id": str(result_id),
                "rank": item.get("rank"),
                "result_type": item.get("result_type"),
            },
        )
        for span in item.get("retrieval_evidence_spans", []):
            _put_search_trace_node_from_id(
                nodes,
                source_table="search_request_result_spans",
                source_id=span.get("search_request_result_span_id"),
                payload=span,
            )
            _put_search_trace_node_from_id(
                nodes,
                source_table="retrieval_evidence_spans",
                source_id=span.get("retrieval_evidence_span_id"),
                payload={
                    "retrieval_evidence_span_id": str(span.get("retrieval_evidence_span_id")),
                    "source_type": span.get("source_type"),
                    "source_id": str(span.get("source_id")),
                    "span_index": span.get("span_index"),
                    "content_sha256": span.get("content_sha256"),
                    "source_snapshot_sha256": span.get("source_snapshot_sha256"),
                },
            )
            for vector in span.get("late_interaction_multivectors", []):
                _put_search_trace_node_from_id(
                    nodes,
                    source_table="retrieval_evidence_span_multivectors",
                    source_id=vector.get("span_vector_id"),
                    payload=vector,
                )
    for index, provenance_edge in enumerate(package.get("provenance_edges") or []):
        from_node_key = _put_search_trace_node_from_ref(
            nodes,
            provenance_edge.get("from") or {},
        )
        to_node_key = _put_search_trace_node_from_ref(nodes, provenance_edge.get("to") or {})
        _put_search_trace_edge(
            edges,
            edge_key=f"search_evidence:{index}:{provenance_edge.get('edge_type')}",
            edge_kind=str(provenance_edge.get("edge_type") or "provenance_edge"),
            from_node_key=from_node_key,
            to_node_key=to_node_key,
            derivation_sha256=provenance_edge.get("derivation_sha256"),
            payload={
                "source": "search_evidence_package",
                "provenance_edge_index": index,
                "provenance_edge": provenance_edge,
            },
        )

    node_specs = sorted(nodes.values(), key=lambda item: item["node_key"])
    edge_specs = sorted(edges, key=lambda item: item["edge_key"])
    graph = _search_trace_graph_payload(node_specs, edge_specs)
    graph["trace_sha256"] = search_trace_graph_sha256(node_specs, edge_specs)
    return graph


def search_trace_specs_from_package(
    package_payload: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], str]:
    graph = package_payload.get("trace_graph")
    if not isinstance(graph, dict):
        graph = build_search_evidence_trace_graph(package_payload)
    node_specs = [
        {
            "node_key": str(node["node_key"]),
            "node_kind": str(node["node_kind"]),
            "source_table": node.get("source_table"),
            "source_id": _uuid_or_none_safe(node.get("source_id")),
            "source_ref": node.get("source_ref"),
            "content_sha256": str(node["content_sha256"]),
            "payload": _json_payload(node.get("payload")),
        }
        for node in graph.get("nodes", [])
    ]
    edge_specs = [
        {
            "edge_key": str(edge["edge_key"]),
            "edge_kind": str(edge["edge_kind"]),
            "from_node_key": str(edge["from_node_key"]),
            "to_node_key": str(edge["to_node_key"]),
            "derivation_sha256": edge.get("derivation_sha256"),
            "content_sha256": str(edge["content_sha256"]),
            "payload": _json_payload(edge.get("payload")),
        }
        for edge in graph.get("edges", [])
    ]
    return (
        node_specs,
        edge_specs,
        str(graph.get("trace_sha256") or search_trace_graph_sha256(node_specs, edge_specs)),
    )
