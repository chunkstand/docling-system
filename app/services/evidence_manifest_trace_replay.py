from __future__ import annotations

from typing import Any

from app.services.evidence_constants import (
    CLAIM_SUPPORT_POLICY_IMPACT_FIXTURE_PROMOTED_EVENT_KIND,
    CLAIM_SUPPORT_POLICY_IMPACT_FIXTURE_PROMOTION_ARTIFACT_KIND,
    CLAIM_SUPPORT_POLICY_IMPACT_REPLAY_ESCALATED_EVENT_KIND,
    CLAIM_SUPPORT_REPLAY_ALERT_FIXTURE_CORPUS_SNAPSHOT_ARTIFACT_KIND,
    CLAIM_SUPPORT_REPLAY_ALERT_FIXTURE_CORPUS_SNAPSHOT_EVENT_KIND,
)
from app.services.evidence_manifest_trace_graph import (
    put_trace_edge,
    put_trace_node_from_id,
)


def add_claim_support_replay_trace(
    nodes: dict[str, dict[str, Any]],
    edges: list[dict[str, Any]],
    *,
    policy_impacts: list[dict[str, Any]],
    verification_id: Any,
    verification_record_node_key: str | None,
) -> None:
    for impact in policy_impacts:
        impact_node_key = put_trace_node_from_id(
            nodes,
            source_table="claim_support_policy_change_impacts",
            source_id=impact.get("change_impact_id"),
            payload=impact,
        )
        for event_kind, event_rows in [
            ("replay_closure_event", impact.get("closure_governance_events") or []),
            ("replay_escalation_event", impact.get("escalation_governance_events") or []),
            (
                "replay_fixture_promotion_event",
                impact.get("fixture_promotion_governance_events") or [],
            ),
            (
                "replay_fixture_waiver_closure_event",
                impact.get("waiver_closure_governance_events") or [],
            ),
        ]:
            for event in event_rows:
                event_node_key = put_trace_node_from_id(
                    nodes,
                    source_table="semantic_governance_events",
                    source_id=event.get("event_id"),
                    payload=event,
                )
                put_trace_edge(
                    edges,
                    edge_key=(
                        f"claim-support-impact:{impact.get('change_impact_id')}:"
                        f"{event_kind}:{event.get('event_id')}"
                    ),
                    edge_kind=event_kind,
                    from_node_key=impact_node_key,
                    to_node_key=event_node_key,
                    payload={"source": "claim_support_policy_change_impact"},
                )
                artifact_id = event.get("agent_task_artifact_id")
                if artifact_id:
                    artifact_node_key = put_trace_node_from_id(
                        nodes,
                        source_table="agent_task_artifacts",
                        source_id=artifact_id,
                        payload={
                            "artifact_id": artifact_id,
                            "receipt_sha256": event.get("receipt_sha256"),
                        },
                    )
                    put_trace_edge(
                        edges,
                        edge_key=(
                            f"claim-support-impact:{impact.get('change_impact_id')}:"
                            f"{event_kind}-artifact:{artifact_id}"
                        ),
                        edge_kind=f"{event_kind}_artifact",
                        from_node_key=event_node_key,
                        to_node_key=artifact_node_key,
                        payload={"source": "claim_support_policy_change_impact"},
                    )

        for snapshot in impact.get("replay_alert_fixture_corpus_snapshots") or []:
            snapshot_id = snapshot.get("snapshot_id")
            snapshot_node_key = put_trace_node_from_id(
                nodes,
                source_table="claim_support_replay_alert_fixture_corpus_snapshots",
                source_id=snapshot_id,
                payload=snapshot,
            )
            put_trace_edge(
                edges,
                edge_key=(
                    f"claim-support-impact:{impact.get('change_impact_id')}:"
                    f"replay-fixture-corpus-snapshot:{snapshot_id}"
                ),
                edge_kind="replay_fixture_corpus_snapshot",
                from_node_key=impact_node_key,
                to_node_key=snapshot_node_key,
                payload={"source": "claim_support_policy_change_impact"},
            )
            put_trace_edge(
                edges,
                edge_key=(
                    f"verification:{verification_id}:"
                    f"uses-replay-fixture-corpus-snapshot:{snapshot_id}"
                ),
                edge_kind="verification_uses_replay_fixture_corpus_snapshot",
                from_node_key=verification_record_node_key,
                to_node_key=snapshot_node_key,
                payload={"source": "claim_support_policy_change_impact"},
            )
            governance_event_id = snapshot.get("semantic_governance_event_id")
            governance_event_node_key = put_trace_node_from_id(
                nodes,
                source_table="semantic_governance_events",
                source_id=governance_event_id,
                payload={
                    "event_id": governance_event_id,
                    "event_kind": CLAIM_SUPPORT_REPLAY_ALERT_FIXTURE_CORPUS_SNAPSHOT_EVENT_KIND,
                    "receipt_sha256": snapshot.get("governance_receipt_sha256"),
                    "governance_integrity": snapshot.get("governance_integrity"),
                },
            )
            put_trace_edge(
                edges,
                edge_key=(
                    f"replay-fixture-corpus-snapshot:{snapshot_id}:"
                    f"governance-event:{governance_event_id}"
                ),
                edge_kind="replay_fixture_corpus_snapshot_governance_event",
                from_node_key=snapshot_node_key,
                to_node_key=governance_event_node_key,
                payload={"source": "claim_support_replay_alert_fixture_corpus"},
            )
            governance_artifact_id = snapshot.get("governance_artifact_id")
            governance_artifact_node_key = put_trace_node_from_id(
                nodes,
                source_table="agent_task_artifacts",
                source_id=governance_artifact_id,
                payload={
                    "artifact_id": governance_artifact_id,
                    "artifact_kind": (
                        CLAIM_SUPPORT_REPLAY_ALERT_FIXTURE_CORPUS_SNAPSHOT_ARTIFACT_KIND
                    ),
                    "receipt_sha256": snapshot.get("governance_receipt_sha256"),
                },
            )
            put_trace_edge(
                edges,
                edge_key=(
                    f"replay-fixture-corpus-snapshot:{snapshot_id}:"
                    f"governance-artifact:{governance_artifact_id}"
                ),
                edge_kind="replay_fixture_corpus_snapshot_governance_artifact",
                from_node_key=governance_event_node_key,
                to_node_key=governance_artifact_node_key,
                payload={"source": "claim_support_replay_alert_fixture_corpus"},
            )
            for row in snapshot.get("rows") or []:
                row_id = row.get("row_id")
                row_node_key = put_trace_node_from_id(
                    nodes,
                    source_table="claim_support_replay_alert_fixture_corpus_rows",
                    source_id=row_id,
                    payload=row,
                )
                put_trace_edge(
                    edges,
                    edge_key=f"replay-fixture-corpus-snapshot:{snapshot_id}:row:{row_id}",
                    edge_kind="replay_fixture_corpus_row",
                    from_node_key=snapshot_node_key,
                    to_node_key=row_node_key,
                    payload={"source": "claim_support_replay_alert_fixture_corpus"},
                )
                promotion_event_id = row.get("promotion_event_id")
                promotion_event_node_key = put_trace_node_from_id(
                    nodes,
                    source_table="semantic_governance_events",
                    source_id=promotion_event_id,
                    payload={
                        "event_id": promotion_event_id,
                        "event_kind": CLAIM_SUPPORT_POLICY_IMPACT_FIXTURE_PROMOTED_EVENT_KIND,
                        "receipt_sha256": row.get("promotion_receipt_sha256"),
                    },
                )
                put_trace_edge(
                    edges,
                    edge_key=(
                        f"replay-fixture-corpus-row:{row_id}:promotion-event:{promotion_event_id}"
                    ),
                    edge_kind="replay_fixture_corpus_row_promotion_event",
                    from_node_key=row_node_key,
                    to_node_key=promotion_event_node_key,
                    payload={"source": "claim_support_replay_alert_fixture_corpus"},
                )
                promotion_artifact_id = row.get("promotion_artifact_id")
                promotion_artifact_node_key = put_trace_node_from_id(
                    nodes,
                    source_table="agent_task_artifacts",
                    source_id=promotion_artifact_id,
                    payload={
                        "artifact_id": promotion_artifact_id,
                        "artifact_kind": (
                            CLAIM_SUPPORT_POLICY_IMPACT_FIXTURE_PROMOTION_ARTIFACT_KIND
                        ),
                        "receipt_sha256": row.get("promotion_receipt_sha256"),
                    },
                )
                put_trace_edge(
                    edges,
                    edge_key=(
                        f"replay-fixture-corpus-row:{row_id}:"
                        f"promotion-artifact:{promotion_artifact_id}"
                    ),
                    edge_kind="replay_fixture_corpus_row_promotion_artifact",
                    from_node_key=row_node_key,
                    to_node_key=promotion_artifact_node_key,
                    payload={"source": "claim_support_replay_alert_fixture_corpus"},
                )
                for escalation_event_id in row.get("source_escalation_event_ids") or []:
                    escalation_event_node_key = put_trace_node_from_id(
                        nodes,
                        source_table="semantic_governance_events",
                        source_id=escalation_event_id,
                        payload={
                            "event_id": escalation_event_id,
                            "event_kind": CLAIM_SUPPORT_POLICY_IMPACT_REPLAY_ESCALATED_EVENT_KIND,
                        },
                    )
                    put_trace_edge(
                        edges,
                        edge_key=(
                            f"replay-fixture-corpus-row:{row_id}:"
                            f"source-escalation-event:{escalation_event_id}"
                        ),
                        edge_kind="replay_fixture_corpus_row_source_escalation_event",
                        from_node_key=row_node_key,
                        to_node_key=escalation_event_node_key,
                        payload={"source": "claim_support_replay_alert_fixture_corpus"},
                    )
