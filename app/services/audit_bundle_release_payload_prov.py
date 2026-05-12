from __future__ import annotations

from typing import Any
from uuid import UUID

from app.core.hashes import payload_sha256 as _payload_sha256
from app.db.models import (
    AuditBundleExport,
    RetrievalJudgmentSet,
    RetrievalLearningCandidateEvaluation,
    RetrievalRerankerArtifact,
    RetrievalTrainingRun,
    SearchHarnessEvaluation,
    SearchHarnessEvaluationSource,
    SearchHarnessRelease,
    SearchReplayRun,
    SemanticGovernanceEvent,
)
from app.services.audit_bundle_release_payload_serialization import (
    SEARCH_HARNESS_RELEASE_AUDIT_BUNDLE_KIND,
)


def prov_jsonld_node(node_id: str, attrs: dict[str, Any], fallback_type: str) -> dict[str, Any]:
    node = {"@id": node_id, "@type": attrs.get("prov:type") or fallback_type}
    for key, value in sorted(attrs.items()):
        if key == "prov:type":
            continue
        node[key] = value
    return node


def prov_edge_id(edge_type: str, edge: dict[str, Any]) -> str:
    return "docling:edge:" + _payload_sha256({"edge_type": edge_type, "edge": edge})[:32]


def prov_jsonld_from_graph(prov: dict[str, Any]) -> dict[str, Any]:
    graph: list[dict[str, Any]] = []
    for entity_id, attrs in sorted((prov.get("entity") or {}).items()):
        graph.append(prov_jsonld_node(entity_id, attrs, "prov:Entity"))
    for activity_id, attrs in sorted((prov.get("activity") or {}).items()):
        graph.append(prov_jsonld_node(activity_id, attrs, "prov:Activity"))
    for agent_id, attrs in sorted((prov.get("agent") or {}).items()):
        graph.append(prov_jsonld_node(agent_id, attrs, "prov:Agent"))
    edge_specs = (
        ("wasGeneratedBy", "prov:Generation"),
        ("used", "prov:Usage"),
        ("wasDerivedFrom", "prov:Derivation"),
        ("wasAssociatedWith", "prov:Association"),
    )
    for edge_key, edge_type in edge_specs:
        for edge in prov.get(edge_key) or []:
            node = {"@id": prov_edge_id(edge_key, edge), "@type": edge_type}
            for key, value in sorted(edge.items()):
                if isinstance(value, str) and key in {
                    "entity",
                    "activity",
                    "agent",
                    "generatedEntity",
                    "usedEntity",
                }:
                    node[f"prov:{key}"] = {"@id": value}
                else:
                    node[f"prov:{key}"] = value
            graph.append(node)
    return {
        "@context": {
            "prov": "http://www.w3.org/ns/prov#",
            "docling": "https://local.docling-system/prov#",
        },
        "@graph": graph,
    }


def validate_prov_graph(
    bundle: dict[str, Any],
    *,
    validation_error,
) -> tuple[dict[str, Any], list[dict[str, str]]]:
    errors: list[dict[str, str]] = []
    payload = bundle.get("payload") or {}
    prov = payload.get("prov") or {}
    if not isinstance(prov, dict):
        return {}, [
            validation_error(
                "prov_graph_missing",
                "PROV graph must be present.",
                "bundle.payload.prov",
            )
        ]
    entities = set((prov.get("entity") or {}).keys())
    activities = set((prov.get("activity") or {}).keys())
    agents = set((prov.get("agent") or {}).keys())
    if not entities:
        errors.append(
            validation_error("prov_entities_missing", "PROV graph has no entities.", "prov.entity")
        )
    if not activities:
        errors.append(
            validation_error(
                "prov_activities_missing",
                "PROV graph has no activities.",
                "prov.activity",
            )
        )
    for index, edge in enumerate(prov.get("wasGeneratedBy") or []):
        if edge.get("entity") not in entities:
            errors.append(
                validation_error(
                    "prov_generated_entity_missing",
                    "wasGeneratedBy references a missing entity.",
                    f"prov.wasGeneratedBy[{index}].entity",
                )
            )
        if edge.get("activity") not in activities:
            errors.append(
                validation_error(
                    "prov_generation_activity_missing",
                    "wasGeneratedBy references a missing activity.",
                    f"prov.wasGeneratedBy[{index}].activity",
                )
            )
    for index, edge in enumerate(prov.get("used") or []):
        if edge.get("activity") not in activities:
            errors.append(
                validation_error(
                    "prov_usage_activity_missing",
                    "used references a missing activity.",
                    f"prov.used[{index}].activity",
                )
            )
        if edge.get("entity") not in entities:
            errors.append(
                validation_error(
                    "prov_usage_entity_missing",
                    "used references a missing entity.",
                    f"prov.used[{index}].entity",
                )
            )
    for index, edge in enumerate(prov.get("wasDerivedFrom") or []):
        if edge.get("generatedEntity") not in entities:
            errors.append(
                validation_error(
                    "prov_derivation_generated_entity_missing",
                    "wasDerivedFrom references a missing generated entity.",
                    f"prov.wasDerivedFrom[{index}].generatedEntity",
                )
            )
        if edge.get("usedEntity") not in entities:
            errors.append(
                validation_error(
                    "prov_derivation_used_entity_missing",
                    "wasDerivedFrom references a missing used entity.",
                    f"prov.wasDerivedFrom[{index}].usedEntity",
                )
            )
    for index, edge in enumerate(prov.get("wasAssociatedWith") or []):
        if edge.get("activity") not in activities:
            errors.append(
                validation_error(
                    "prov_association_activity_missing",
                    "wasAssociatedWith references a missing activity.",
                    f"prov.wasAssociatedWith[{index}].activity",
                )
            )
        if edge.get("agent") not in agents:
            errors.append(
                validation_error(
                    "prov_association_agent_missing",
                    "wasAssociatedWith references a missing agent.",
                    f"prov.wasAssociatedWith[{index}].agent",
                )
            )
    return prov_jsonld_from_graph(prov), errors


def prov_graph(
    *,
    release: SearchHarnessRelease,
    evaluation: SearchHarnessEvaluation | None,
    sources: list[SearchHarnessEvaluationSource],
    replay_runs: list[SearchReplayRun],
    learning_candidates: list[RetrievalLearningCandidateEvaluation],
    reranker_artifacts: list[RetrievalRerankerArtifact],
    training_runs: list[RetrievalTrainingRun],
    training_audit_bundles: list[AuditBundleExport],
    judgment_sets: list[RetrievalJudgmentSet],
    governance_events: list[SemanticGovernanceEvent],
    bundle_id: UUID,
    created_by: str | None,
) -> dict[str, Any]:
    release_entity = f"docling:search_harness_release:{release.id}"
    evaluation_entity = f"docling:search_harness_evaluation:{release.search_harness_evaluation_id}"
    activity = f"docling:activity:search_harness_release_gate:{release.id}"
    exporter_activity = f"docling:activity:audit_bundle_export:{bundle_id}"
    agent = f"docling:agent:{created_by or release.requested_by or 'system'}"

    entities: dict[str, dict[str, Any]] = {
        release_entity: {
            "prov:type": "docling:SearchHarnessRelease",
            "docling:outcome": release.outcome,
            "docling:releasePackageSha256": release.release_package_sha256,
        },
        evaluation_entity: {
            "prov:type": "docling:SearchHarnessEvaluation",
            "docling:status": evaluation.status if evaluation else None,
        },
        f"docling:thresholds:{release.id}": {
            "prov:type": "docling:ReleaseThresholds",
            "docling:sha256": _payload_sha256(release.thresholds_json or {}),
        },
        f"docling:audit_bundle_export:{bundle_id}": {
            "prov:type": "docling:AuditBundleExport",
            "docling:bundleKind": SEARCH_HARNESS_RELEASE_AUDIT_BUNDLE_KIND,
        },
    }
    for source in sources:
        entities[f"docling:search_harness_evaluation_source:{source.id}"] = {
            "prov:type": "docling:SearchHarnessEvaluationSource",
            "docling:sourceType": source.source_type,
        }
    for replay_run in replay_runs:
        entities[f"docling:search_replay_run:{replay_run.id}"] = {
            "prov:type": "docling:SearchReplayRun",
            "docling:status": replay_run.status,
            "docling:harnessName": replay_run.harness_name,
        }
    for candidate in learning_candidates:
        entities[f"docling:retrieval_learning_candidate_evaluation:{candidate.id}"] = {
            "prov:type": "docling:RetrievalLearningCandidateEvaluation",
            "docling:gateOutcome": candidate.gate_outcome,
            "docling:learningPackageSha256": candidate.learning_package_sha256,
        }
    for artifact in reranker_artifacts:
        entities[f"docling:retrieval_reranker_artifact:{artifact.id}"] = {
            "prov:type": "docling:RetrievalRerankerArtifact",
            "docling:artifactKind": artifact.artifact_kind,
            "docling:artifactSha256": artifact.artifact_sha256,
            "docling:changeImpactSha256": artifact.change_impact_sha256,
            "docling:gateOutcome": artifact.gate_outcome,
        }
    for training_run in training_runs:
        entities[f"docling:retrieval_training_run:{training_run.id}"] = {
            "prov:type": "docling:RetrievalTrainingRun",
            "docling:trainingDatasetSha256": training_run.training_dataset_sha256,
            "docling:exampleCount": training_run.example_count,
        }
    for judgment_set in judgment_sets:
        entities[f"docling:retrieval_judgment_set:{judgment_set.id}"] = {
            "prov:type": "docling:RetrievalJudgmentSet",
            "docling:payloadSha256": judgment_set.payload_sha256,
            "docling:judgmentCount": judgment_set.judgment_count,
        }
    for bundle in training_audit_bundles:
        entities[f"docling:audit_bundle_export:{bundle.id}"] = {
            "prov:type": "docling:AuditBundleExport",
            "docling:bundleKind": bundle.bundle_kind,
            "docling:payloadSha256": bundle.payload_sha256,
            "docling:bundleSha256": bundle.bundle_sha256,
            "docling:sourceTable": bundle.source_table,
            "docling:sourceId": str(bundle.source_id),
        }
    for event in governance_events:
        entities[f"docling:semantic_governance_event:{event.id}"] = {
            "prov:type": "docling:SemanticGovernanceEvent",
            "docling:eventKind": event.event_kind,
            "docling:eventHash": event.event_hash,
            "docling:payloadSha256": event.payload_sha256,
        }

    used = [
        {"activity": activity, "entity": evaluation_entity},
        {"activity": activity, "entity": f"docling:thresholds:{release.id}"},
    ]
    was_derived_from = [
        {"generatedEntity": release_entity, "usedEntity": evaluation_entity},
    ]
    for source in sources:
        source_entity = f"docling:search_harness_evaluation_source:{source.id}"
        used.append({"activity": activity, "entity": source_entity})
        was_derived_from.append({"generatedEntity": release_entity, "usedEntity": source_entity})
        was_derived_from.append(
            {
                "generatedEntity": source_entity,
                "usedEntity": f"docling:search_replay_run:{source.baseline_replay_run_id}",
            }
        )
        was_derived_from.append(
            {
                "generatedEntity": source_entity,
                "usedEntity": f"docling:search_replay_run:{source.candidate_replay_run_id}",
            }
        )
    for candidate in learning_candidates:
        candidate_entity = f"docling:retrieval_learning_candidate_evaluation:{candidate.id}"
        training_run_entity = (
            f"docling:retrieval_training_run:{candidate.retrieval_training_run_id}"
        )
        judgment_set_entity = f"docling:retrieval_judgment_set:{candidate.judgment_set_id}"
        used.append({"activity": activity, "entity": candidate_entity})
        was_derived_from.append({"generatedEntity": release_entity, "usedEntity": candidate_entity})
        was_derived_from.append(
            {"generatedEntity": candidate_entity, "usedEntity": training_run_entity}
        )
        was_derived_from.append(
            {"generatedEntity": training_run_entity, "usedEntity": judgment_set_entity}
        )
        if candidate.semantic_governance_event_id is not None:
            was_derived_from.append(
                {
                    "generatedEntity": candidate_entity,
                    "usedEntity": (
                        "docling:semantic_governance_event:"
                        f"{candidate.semantic_governance_event_id}"
                    ),
                }
            )

    for artifact in reranker_artifacts:
        artifact_entity = f"docling:retrieval_reranker_artifact:{artifact.id}"
        candidate_entity = (
            "docling:retrieval_learning_candidate_evaluation:"
            f"{artifact.retrieval_learning_candidate_evaluation_id}"
        )
        training_run_entity = f"docling:retrieval_training_run:{artifact.retrieval_training_run_id}"
        used.append({"activity": activity, "entity": artifact_entity})
        was_derived_from.append({"generatedEntity": release_entity, "usedEntity": artifact_entity})
        was_derived_from.append(
            {"generatedEntity": artifact_entity, "usedEntity": candidate_entity}
        )
        was_derived_from.append(
            {"generatedEntity": artifact_entity, "usedEntity": training_run_entity}
        )
        if artifact.semantic_governance_event_id is not None:
            was_derived_from.append(
                {
                    "generatedEntity": artifact_entity,
                    "usedEntity": (
                        f"docling:semantic_governance_event:{artifact.semantic_governance_event_id}"
                    ),
                }
            )

    for bundle in training_audit_bundles:
        training_bundle_entity = f"docling:audit_bundle_export:{bundle.id}"
        used.append({"activity": exporter_activity, "entity": training_bundle_entity})
        was_derived_from.append(
            {
                "generatedEntity": f"docling:audit_bundle_export:{bundle_id}",
                "usedEntity": training_bundle_entity,
            }
        )

    return {
        "prefix": {
            "prov": "http://www.w3.org/ns/prov#",
            "docling": "https://local.docling-system/prov#",
        },
        "entity": entities,
        "activity": {
            activity: {
                "prov:type": "docling:SearchHarnessReleaseGate",
                "prov:endedAtTime": release.created_at.isoformat(),
            },
            exporter_activity: {
                "prov:type": "docling:AuditBundleExport",
            },
        },
        "agent": {
            agent: {
                "prov:type": "prov:Person" if created_by else "prov:SoftwareAgent",
                "docling:identifier": created_by or release.requested_by or "system",
            }
        },
        "wasGeneratedBy": [
            {"entity": release_entity, "activity": activity},
            {
                "entity": f"docling:audit_bundle_export:{bundle_id}",
                "activity": exporter_activity,
            },
        ],
        "used": used,
        "wasDerivedFrom": was_derived_from,
        "wasAssociatedWith": [
            {"activity": activity, "agent": agent},
            {"activity": exporter_activity, "agent": agent},
        ],
    }
