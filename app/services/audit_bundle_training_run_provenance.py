from __future__ import annotations

from typing import Any
from uuid import UUID

from app.db.public.retrieval import (
    RetrievalHardNegative,
    RetrievalJudgment,
    RetrievalJudgmentSet,
    RetrievalTrainingRun,
)
from app.db.public.semantic_memory import SemanticGovernanceEvent


def training_run_prov_graph(
    *,
    training_run: RetrievalTrainingRun,
    judgment_set: RetrievalJudgmentSet | None,
    judgments: list[RetrievalJudgment],
    hard_negatives: list[RetrievalHardNegative],
    governance_events: list[SemanticGovernanceEvent],
    claim_support_replay_alert_corpus_lineage: dict[str, Any],
    bundle_id: UUID,
    created_by: str | None,
    bundle_kind: str,
    source_table: str,
) -> dict[str, Any]:
    training_entity = f"docling:retrieval_training_run:{training_run.id}"
    dataset_entity = f"docling:retrieval_training_dataset:{training_run.id}"
    judgment_set_entity = f"docling:retrieval_judgment_set:{training_run.judgment_set_id}"
    exporter_activity = f"docling:activity:audit_bundle_export:{bundle_id}"
    materialization_activity = (
        f"docling:activity:retrieval_training_run_materialization:{training_run.id}"
    )
    agent = f"docling:agent:{created_by or training_run.created_by or 'system'}"

    entities: dict[str, dict[str, Any]] = {
        training_entity: {
            "prov:type": "docling:RetrievalTrainingRun",
            "docling:trainingDatasetSha256": training_run.training_dataset_sha256,
            "docling:exampleCount": training_run.example_count,
        },
        dataset_entity: {
            "prov:type": "docling:RetrievalTrainingDataset",
            "docling:sha256": training_run.training_dataset_sha256,
        },
        judgment_set_entity: {
            "prov:type": "docling:RetrievalJudgmentSet",
            "docling:payloadSha256": judgment_set.payload_sha256 if judgment_set else None,
            "docling:judgmentCount": judgment_set.judgment_count if judgment_set else None,
        },
        f"docling:audit_bundle_export:{bundle_id}": {
            "prov:type": "docling:AuditBundleExport",
            "docling:bundleKind": bundle_kind,
        },
    }
    for judgment in judgments:
        entities[f"docling:retrieval_judgment:{judgment.id}"] = {
            "prov:type": "docling:RetrievalJudgment",
            "docling:judgmentKind": judgment.judgment_kind,
            "docling:sourcePayloadSha256": judgment.source_payload_sha256,
        }
    for hard_negative in hard_negatives:
        entities[f"docling:retrieval_hard_negative:{hard_negative.id}"] = {
            "prov:type": "docling:RetrievalHardNegative",
            "docling:hardNegativeKind": hard_negative.hard_negative_kind,
            "docling:sourcePayloadSha256": hard_negative.source_payload_sha256,
        }
    for event in governance_events:
        entities[f"docling:semantic_governance_event:{event.id}"] = {
            "prov:type": "docling:SemanticGovernanceEvent",
            "docling:eventKind": event.event_kind,
            "docling:eventHash": event.event_hash,
            "docling:payloadSha256": event.payload_sha256,
        }
    for snapshot in claim_support_replay_alert_corpus_lineage.get("snapshots") or []:
        snapshot_entity = (
            f"docling:claim_support_replay_alert_corpus_snapshot:{snapshot['snapshot_id']}"
        )
        entities[snapshot_entity] = {
            "prov:type": "docling:ClaimSupportReplayAlertFixtureCorpusSnapshot",
            "docling:snapshotSha256": snapshot.get("snapshot_sha256"),
            "docling:computedSnapshotSha256": snapshot.get("computed_snapshot_sha256"),
            "docling:fixtureCount": snapshot.get("fixture_count"),
        }
    for corpus_row in claim_support_replay_alert_corpus_lineage.get("rows") or []:
        entities[f"docling:claim_support_replay_alert_corpus_row:{corpus_row['corpus_row_id']}"] = {
            "prov:type": "docling:ClaimSupportReplayAlertFixtureCorpusRow",
            "docling:fixtureSha256": corpus_row.get("fixture_sha256"),
            "docling:computedFixtureSha256": corpus_row.get("computed_fixture_sha256"),
            "docling:caseId": corpus_row.get("case_id"),
        }
    for artifact in [
        *(claim_support_replay_alert_corpus_lineage.get("promotion_artifacts") or []),
        *(claim_support_replay_alert_corpus_lineage.get("snapshot_governance_artifacts") or []),
    ]:
        entities[f"docling:agent_task_artifact:{artifact['artifact_id']}"] = {
            "prov:type": "docling:AgentTaskArtifact",
            "docling:artifactKind": artifact.get("artifact_kind"),
            "docling:payloadSha256": artifact.get("payload_sha256"),
            "docling:receiptSha256": artifact.get("receipt_sha256"),
        }
    for event_payload in [
        *(claim_support_replay_alert_corpus_lineage.get("promotion_events") or []),
        *(claim_support_replay_alert_corpus_lineage.get("escalation_events") or []),
        *(claim_support_replay_alert_corpus_lineage.get("snapshot_governance_events") or []),
    ]:
        entities[f"docling:semantic_governance_event:{event_payload['event_id']}"] = {
            "prov:type": "docling:SemanticGovernanceEvent",
            "docling:eventKind": event_payload.get("event_kind"),
            "docling:eventHash": event_payload.get("event_hash"),
            "docling:payloadSha256": event_payload.get("payload_sha256"),
        }

    used = [{"activity": materialization_activity, "entity": judgment_set_entity}]
    was_derived_from = [
        {"generatedEntity": training_entity, "usedEntity": judgment_set_entity},
        {"generatedEntity": dataset_entity, "usedEntity": judgment_set_entity},
        {"generatedEntity": training_entity, "usedEntity": dataset_entity},
    ]
    for judgment in judgments:
        judgment_entity = f"docling:retrieval_judgment:{judgment.id}"
        used.append({"activity": materialization_activity, "entity": judgment_entity})
        was_derived_from.append({"generatedEntity": dataset_entity, "usedEntity": judgment_entity})
    for hard_negative in hard_negatives:
        hard_negative_entity = f"docling:retrieval_hard_negative:{hard_negative.id}"
        used.append({"activity": materialization_activity, "entity": hard_negative_entity})
        was_derived_from.append(
            {"generatedEntity": dataset_entity, "usedEntity": hard_negative_entity}
        )
        was_derived_from.append(
            {
                "generatedEntity": hard_negative_entity,
                "usedEntity": f"docling:retrieval_judgment:{hard_negative.judgment_id}",
            }
        )
        if hard_negative.positive_judgment_id is not None:
            was_derived_from.append(
                {
                    "generatedEntity": hard_negative_entity,
                    "usedEntity": (
                        f"docling:retrieval_judgment:{hard_negative.positive_judgment_id}"
                    ),
                }
            )
    for event in governance_events:
        governance_entity = f"docling:semantic_governance_event:{event.id}"
        used.append({"activity": exporter_activity, "entity": governance_entity})
        if event.subject_table == source_table:
            was_derived_from.append(
                {"generatedEntity": training_entity, "usedEntity": governance_entity}
            )
        if event.previous_event_id is not None:
            was_derived_from.append(
                {
                    "generatedEntity": governance_entity,
                    "usedEntity": f"docling:semantic_governance_event:{event.previous_event_id}",
                }
            )
    for reference in claim_support_replay_alert_corpus_lineage.get("source_references") or []:
        row_entity = f"docling:claim_support_replay_alert_corpus_row:{reference['corpus_row_id']}"
        snapshot_entity = (
            f"docling:claim_support_replay_alert_corpus_snapshot:{reference['snapshot_id']}"
        )
        carrier_entity = f"docling:{reference['carrier_type']}:{reference['carrier_id']}"
        used.append({"activity": materialization_activity, "entity": row_entity})
        was_derived_from.append({"generatedEntity": carrier_entity, "usedEntity": row_entity})
        was_derived_from.append({"generatedEntity": dataset_entity, "usedEntity": row_entity})
        was_derived_from.append({"generatedEntity": row_entity, "usedEntity": snapshot_entity})
        if reference.get("promotion_artifact_id"):
            was_derived_from.append(
                {
                    "generatedEntity": row_entity,
                    "usedEntity": (
                        f"docling:agent_task_artifact:{reference['promotion_artifact_id']}"
                    ),
                }
            )
        if reference.get("promotion_event_id"):
            was_derived_from.append(
                {
                    "generatedEntity": row_entity,
                    "usedEntity": (
                        f"docling:semantic_governance_event:{reference['promotion_event_id']}"
                    ),
                }
            )
        for escalation_event_id in reference.get("source_escalation_event_ids") or []:
            was_derived_from.append(
                {
                    "generatedEntity": row_entity,
                    "usedEntity": f"docling:semantic_governance_event:{escalation_event_id}",
                }
            )
    for snapshot in claim_support_replay_alert_corpus_lineage.get("snapshots") or []:
        snapshot_entity = (
            f"docling:claim_support_replay_alert_corpus_snapshot:{snapshot['snapshot_id']}"
        )
        if snapshot.get("governance_artifact_id"):
            was_derived_from.append(
                {
                    "generatedEntity": snapshot_entity,
                    "usedEntity": (
                        f"docling:agent_task_artifact:{snapshot['governance_artifact_id']}"
                    ),
                }
            )
        if snapshot.get("semantic_governance_event_id"):
            was_derived_from.append(
                {
                    "generatedEntity": snapshot_entity,
                    "usedEntity": (
                        "docling:semantic_governance_event:"
                        f"{snapshot['semantic_governance_event_id']}"
                    ),
                }
            )

    return {
        "prefix": {
            "prov": "http://www.w3.org/ns/prov#",
            "docling": "https://local.docling-system/prov#",
        },
        "entity": entities,
        "activity": {
            materialization_activity: {
                "prov:type": "docling:RetrievalTrainingRunMaterialization",
                "prov:endedAtTime": (
                    training_run.completed_at.isoformat()
                    if training_run.completed_at
                    else training_run.created_at.isoformat()
                ),
            },
            exporter_activity: {
                "prov:type": "docling:AuditBundleExport",
            },
        },
        "agent": {
            agent: {
                "prov:type": "prov:Person" if created_by else "prov:SoftwareAgent",
                "docling:identifier": created_by or training_run.created_by or "system",
            }
        },
        "wasGeneratedBy": [
            {"entity": training_entity, "activity": materialization_activity},
            {"entity": dataset_entity, "activity": materialization_activity},
            {
                "entity": f"docling:audit_bundle_export:{bundle_id}",
                "activity": exporter_activity,
            },
        ],
        "used": used,
        "wasDerivedFrom": was_derived_from,
        "wasAssociatedWith": [
            {"activity": materialization_activity, "agent": agent},
            {"activity": exporter_activity, "agent": agent},
        ],
    }
