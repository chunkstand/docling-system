"""DB model contract fragment for semantic memory."""

from __future__ import annotations

MODEL_SYMBOLS = (
    "SemanticOntologySnapshot",
    "WorkspaceSemanticState",
    "SemanticGraphSnapshot",
    "WorkspaceSemanticGraphState",
    "SemanticConcept",
    "SemanticCategory",
    "SemanticTerm",
    "SemanticConceptTerm",
    "SemanticConceptCategoryBinding",
    "DocumentSemanticConceptReview",
    "DocumentSemanticCategoryReview",
    "DocumentRunSemanticPass",
    "SemanticAssertion",
    "SemanticAssertionCategoryBinding",
    "SemanticAssertionEvidence",
    "SemanticEntity",
    "SemanticFact",
    "SemanticFactEvidence",
    "SemanticGovernanceEvent",
)

SEMANTIC_MEMORY_DOMAIN_TABLE_COLUMNS = {
    "semantic_ontology_snapshots": frozenset(
        {
            "activated_at",
            "created_at",
            "id",
            "ontology_name",
            "ontology_version",
            "parent_snapshot_id",
            "payload",
            "sha256",
            "source_kind",
            "source_task_id",
            "source_task_type",
            "upper_ontology_version",
        }
    ),
    "workspace_semantic_state": frozenset(
        {"active_ontology_snapshot_id", "created_at", "updated_at", "workspace_key"}
    ),
    "semantic_graph_snapshots": frozenset(
        {
            "activated_at",
            "created_at",
            "graph_name",
            "graph_version",
            "id",
            "ontology_snapshot_id",
            "parent_snapshot_id",
            "payload",
            "sha256",
            "source_kind",
            "source_task_id",
            "source_task_type",
        }
    ),
    "workspace_semantic_graph_state": frozenset(
        {"active_graph_snapshot_id", "created_at", "updated_at", "workspace_key"}
    ),
    "semantic_concepts": frozenset(
        {
            "concept_key",
            "created_at",
            "id",
            "metadata",
            "preferred_label",
            "registry_version",
            "scope_note",
            "updated_at",
        }
    ),
    "semantic_categories": frozenset(
        {
            "category_key",
            "created_at",
            "id",
            "metadata",
            "preferred_label",
            "registry_version",
            "scope_note",
            "updated_at",
        }
    ),
    "semantic_terms": frozenset(
        {
            "created_at",
            "id",
            "metadata",
            "normalized_text",
            "registry_version",
            "term_kind",
            "term_text",
        }
    ),
    "semantic_concept_terms": frozenset(
        {
            "concept_id",
            "created_at",
            "created_from",
            "details",
            "id",
            "mapping_kind",
            "review_status",
            "term_id",
        }
    ),
    "semantic_concept_category_bindings": frozenset(
        {
            "binding_type",
            "category_id",
            "concept_id",
            "created_at",
            "created_from",
            "details",
            "id",
            "review_status",
        }
    ),
    "document_semantic_concept_reviews": frozenset(
        {
            "concept_id",
            "created_at",
            "document_id",
            "id",
            "review_note",
            "review_status",
            "reviewed_by",
        }
    ),
    "document_semantic_category_reviews": frozenset(
        {
            "category_id",
            "concept_id",
            "created_at",
            "document_id",
            "id",
            "review_note",
            "review_status",
            "reviewed_by",
        }
    ),
    "document_run_semantic_passes": frozenset(
        {
            "artifact_json_path",
            "artifact_json_sha256",
            "artifact_schema_version",
            "artifact_yaml_path",
            "artifact_yaml_sha256",
            "assertion_count",
            "baseline_run_id",
            "baseline_semantic_pass_id",
            "completed_at",
            "continuity_summary",
            "created_at",
            "document_id",
            "error_message",
            "evaluation_fixture_name",
            "evaluation_status",
            "evaluation_summary",
            "evaluation_version",
            "evidence_count",
            "extractor_version",
            "id",
            "ontology_snapshot_id",
            "registry_sha256",
            "registry_version",
            "run_id",
            "status",
            "summary",
            "upper_ontology_version",
        }
    ),
    "semantic_assertions": frozenset(
        {
            "assertion_kind",
            "concept_id",
            "confidence",
            "context_scope",
            "created_at",
            "details",
            "epistemic_status",
            "evidence_count",
            "id",
            "matched_terms",
            "review_status",
            "semantic_pass_id",
            "source_types",
        }
    ),
    "semantic_assertion_category_bindings": frozenset(
        {
            "assertion_id",
            "binding_type",
            "category_id",
            "concept_category_binding_id",
            "created_at",
            "created_from",
            "details",
            "id",
            "review_status",
        }
    ),
    "semantic_assertion_evidence": frozenset(
        {
            "assertion_id",
            "chunk_id",
            "created_at",
            "details",
            "document_id",
            "excerpt",
            "figure_id",
            "id",
            "matched_terms",
            "page_from",
            "page_to",
            "run_id",
            "source_artifact_path",
            "source_artifact_sha256",
            "source_label",
            "source_locator",
            "source_type",
            "table_id",
        }
    ),
    "semantic_entities": frozenset(
        {
            "concept_id",
            "created_at",
            "details",
            "document_id",
            "entity_key",
            "entity_type",
            "id",
            "ontology_snapshot_id",
            "preferred_label",
        }
    ),
    "semantic_facts": frozenset(
        {
            "confidence",
            "created_at",
            "details",
            "document_id",
            "id",
            "object_entity_id",
            "object_value_text",
            "ontology_snapshot_id",
            "relation_key",
            "relation_label",
            "review_status",
            "run_id",
            "semantic_pass_id",
            "source_assertion_id",
            "subject_entity_id",
        }
    ),
    "semantic_fact_evidence": frozenset(
        {"assertion_evidence_id", "assertion_id", "created_at", "fact_id", "id"}
    ),
    "semantic_governance_events": frozenset(
        {
            "agent_task_artifact_id",
            "created_at",
            "created_by",
            "deduplication_key",
            "event_hash",
            "event_kind",
            "event_payload",
            "event_sequence",
            "evidence_manifest_id",
            "evidence_package_export_id",
            "governance_scope",
            "id",
            "ontology_snapshot_id",
            "payload_sha256",
            "previous_event_hash",
            "previous_event_id",
            "receipt_sha256",
            "search_harness_evaluation_id",
            "search_harness_release_id",
            "semantic_graph_snapshot_id",
            "subject_id",
            "subject_table",
            "task_id",
        }
    ),
}

REQUIRED_TABLE_INDEX_NAMES = {
    "semantic_ontology_snapshots": frozenset(
        {
            "ix_semantic_ontology_snapshots_created_at",
            "ix_semantic_ontology_snapshots_upper_ontology_version",
        }
    ),
    "semantic_graph_snapshots": frozenset(
        {
            "ix_semantic_graph_snapshots_created_at",
            "ix_semantic_graph_snapshots_ontology_snapshot_id",
        }
    ),
    "semantic_concepts": frozenset(
        {"ix_semantic_concepts_concept_key", "ix_semantic_concepts_registry_version"}
    ),
    "semantic_categories": frozenset(
        {"ix_semantic_categories_category_key", "ix_semantic_categories_registry_version"}
    ),
    "semantic_terms": frozenset(
        {"ix_semantic_terms_normalized_text", "ix_semantic_terms_registry_version"}
    ),
    "semantic_concept_terms": frozenset(
        {"ix_semantic_concept_terms_concept_id", "ix_semantic_concept_terms_term_id"}
    ),
    "semantic_concept_category_bindings": frozenset(
        {
            "ix_semantic_concept_category_bindings_category_id",
            "ix_semantic_concept_category_bindings_concept_id",
        }
    ),
    "document_semantic_concept_reviews": frozenset(
        {
            "ix_doc_sem_concept_reviews_doc_concept_created_at",
            "ix_document_semantic_concept_reviews_concept_id",
            "ix_document_semantic_concept_reviews_document_id",
        }
    ),
    "document_semantic_category_reviews": frozenset(
        {
            "ix_doc_sem_category_reviews_doc_binding_created_at",
            "ix_document_semantic_category_reviews_category_id",
            "ix_document_semantic_category_reviews_concept_id",
            "ix_document_semantic_category_reviews_document_id",
        }
    ),
    "document_run_semantic_passes": frozenset(
        {
            "ix_document_run_semantic_passes_baseline_run_id",
            "ix_document_run_semantic_passes_document_id",
            "ix_document_run_semantic_passes_ontology_snapshot_id",
            "ix_document_run_semantic_passes_run_id",
            "ix_document_run_semantic_passes_status",
        }
    ),
    "semantic_assertions": frozenset(
        {"ix_semantic_assertions_concept_id", "ix_semantic_assertions_semantic_pass_id"}
    ),
    "semantic_assertion_category_bindings": frozenset(
        {
            "ix_semantic_assertion_category_bindings_assertion_id",
            "ix_semantic_assertion_category_bindings_category_id",
        }
    ),
    "semantic_assertion_evidence": frozenset(
        {
            "ix_semantic_assertion_evidence_assertion_id",
            "ix_semantic_assertion_evidence_run_id",
            "ix_semantic_assertion_evidence_source_type",
        }
    ),
    "semantic_entities": frozenset(
        {"ix_semantic_entities_concept_id", "ix_semantic_entities_document_id"}
    ),
    "semantic_facts": frozenset(
        {
            "ix_semantic_facts_document_id",
            "ix_semantic_facts_object_entity_id",
            "ix_semantic_facts_relation_key",
            "ix_semantic_facts_run_id",
            "ix_semantic_facts_semantic_pass_id",
            "ix_semantic_facts_subject_entity_id",
        }
    ),
    "semantic_fact_evidence": frozenset(
        {
            "ix_semantic_fact_evidence_assertion_id",
            "ix_semantic_fact_evidence_evidence_id",
            "ix_semantic_fact_evidence_fact_id",
        }
    ),
    "semantic_governance_events": frozenset(
        {
            "ix_semantic_governance_events_artifact",
            "ix_semantic_governance_events_event_hash",
            "ix_semantic_governance_events_graph",
            "ix_semantic_governance_events_kind_created",
            "ix_semantic_governance_events_manifest",
            "ix_semantic_governance_events_ontology",
            "ix_semantic_governance_events_payload_sha",
            "ix_semantic_governance_events_receipt_sha",
            "ix_semantic_governance_events_release",
            "ix_semantic_governance_events_scope_created",
            "ix_semantic_governance_events_subject",
            "ix_semantic_governance_events_task_created",
        }
    ),
}

REQUIRED_TABLE_INDEX_COLUMNS = {
    "semantic_ontology_snapshots": {
        "ix_semantic_ontology_snapshots_created_at": ("created_at",),
        "ix_semantic_ontology_snapshots_upper_ontology_version": ("upper_ontology_version",),
    },
    "semantic_graph_snapshots": {
        "ix_semantic_graph_snapshots_created_at": ("created_at",),
        "ix_semantic_graph_snapshots_ontology_snapshot_id": ("ontology_snapshot_id",),
    },
    "semantic_concepts": {
        "ix_semantic_concepts_concept_key": ("concept_key",),
        "ix_semantic_concepts_registry_version": ("registry_version",),
    },
    "semantic_categories": {
        "ix_semantic_categories_category_key": ("category_key",),
        "ix_semantic_categories_registry_version": ("registry_version",),
    },
    "semantic_terms": {
        "ix_semantic_terms_registry_version": ("registry_version",),
        "ix_semantic_terms_normalized_text": ("normalized_text",),
    },
    "semantic_concept_terms": {
        "ix_semantic_concept_terms_concept_id": ("concept_id",),
        "ix_semantic_concept_terms_term_id": ("term_id",),
    },
    "semantic_concept_category_bindings": {
        "ix_semantic_concept_category_bindings_concept_id": ("concept_id",),
        "ix_semantic_concept_category_bindings_category_id": ("category_id",),
    },
    "document_semantic_concept_reviews": {
        "ix_document_semantic_concept_reviews_document_id": ("document_id",),
        "ix_document_semantic_concept_reviews_concept_id": ("concept_id",),
        "ix_doc_sem_concept_reviews_doc_concept_created_at": (
            "document_id",
            "concept_id",
            "created_at",
        ),
    },
    "document_semantic_category_reviews": {
        "ix_document_semantic_category_reviews_document_id": ("document_id",),
        "ix_document_semantic_category_reviews_concept_id": ("concept_id",),
        "ix_document_semantic_category_reviews_category_id": ("category_id",),
        "ix_doc_sem_category_reviews_doc_binding_created_at": (
            "document_id",
            "concept_id",
            "category_id",
            "created_at",
        ),
    },
    "document_run_semantic_passes": {
        "ix_document_run_semantic_passes_document_id": ("document_id",),
        "ix_document_run_semantic_passes_run_id": ("run_id",),
        "ix_document_run_semantic_passes_baseline_run_id": ("baseline_run_id",),
        "ix_document_run_semantic_passes_ontology_snapshot_id": ("ontology_snapshot_id",),
        "ix_document_run_semantic_passes_status": ("status",),
    },
    "semantic_assertions": {
        "ix_semantic_assertions_semantic_pass_id": ("semantic_pass_id",),
        "ix_semantic_assertions_concept_id": ("concept_id",),
    },
    "semantic_assertion_category_bindings": {
        "ix_semantic_assertion_category_bindings_assertion_id": ("assertion_id",),
        "ix_semantic_assertion_category_bindings_category_id": ("category_id",),
    },
    "semantic_assertion_evidence": {
        "ix_semantic_assertion_evidence_assertion_id": ("assertion_id",),
        "ix_semantic_assertion_evidence_run_id": ("run_id",),
        "ix_semantic_assertion_evidence_source_type": ("source_type",),
    },
    "semantic_entities": {
        "ix_semantic_entities_document_id": ("document_id",),
        "ix_semantic_entities_concept_id": ("concept_id",),
    },
    "semantic_facts": {
        "ix_semantic_facts_document_id": ("document_id",),
        "ix_semantic_facts_run_id": ("run_id",),
        "ix_semantic_facts_semantic_pass_id": ("semantic_pass_id",),
        "ix_semantic_facts_relation_key": ("relation_key",),
        "ix_semantic_facts_subject_entity_id": ("subject_entity_id",),
        "ix_semantic_facts_object_entity_id": ("object_entity_id",),
    },
    "semantic_fact_evidence": {
        "ix_semantic_fact_evidence_fact_id": ("fact_id",),
        "ix_semantic_fact_evidence_assertion_id": ("assertion_id",),
        "ix_semantic_fact_evidence_evidence_id": ("assertion_evidence_id",),
    },
    "semantic_governance_events": {
        "ix_semantic_governance_events_scope_created": ("governance_scope", "created_at"),
        "ix_semantic_governance_events_kind_created": ("event_kind", "created_at"),
        "ix_semantic_governance_events_subject": ("subject_table", "subject_id"),
        "ix_semantic_governance_events_task_created": ("task_id", "created_at"),
        "ix_semantic_governance_events_ontology": ("ontology_snapshot_id", "created_at"),
        "ix_semantic_governance_events_graph": ("semantic_graph_snapshot_id", "created_at"),
        "ix_semantic_governance_events_release": ("search_harness_release_id", "created_at"),
        "ix_semantic_governance_events_manifest": ("evidence_manifest_id", "created_at"),
        "ix_semantic_governance_events_artifact": ("agent_task_artifact_id", "created_at"),
        "ix_semantic_governance_events_receipt_sha": ("receipt_sha256",),
        "ix_semantic_governance_events_payload_sha": ("payload_sha256",),
        "ix_semantic_governance_events_event_hash": ("event_hash",),
    },
}

REQUIRED_TABLE_UNIQUE_CONSTRAINT_NAMES = {
    "semantic_ontology_snapshots": frozenset({"uq_semantic_ontology_snapshots_ontology_version"}),
    "semantic_graph_snapshots": frozenset({"uq_semantic_graph_snapshots_graph_version"}),
    "semantic_concepts": frozenset({"uq_semantic_concepts_key_registry_version"}),
    "semantic_categories": frozenset({"uq_semantic_categories_key_registry_version"}),
    "semantic_terms": frozenset({"uq_semantic_terms_registry_version_normalized_text"}),
    "semantic_concept_terms": frozenset({"uq_semantic_concept_terms_concept_term"}),
    "semantic_concept_category_bindings": frozenset(
        {"uq_semantic_concept_category_bindings_concept_category"}
    ),
    "document_run_semantic_passes": frozenset(
        {"uq_document_run_semantic_passes_run_version_tuple"}
    ),
    "semantic_assertions": frozenset({"uq_semantic_assertions_pass_concept_kind"}),
    "semantic_assertion_category_bindings": frozenset(
        {"uq_semantic_assertion_category_bindings_assertion_category"}
    ),
    "semantic_assertion_evidence": frozenset({"uq_semantic_assertion_evidence_assertion_source"}),
    "semantic_entities": frozenset({"uq_semantic_entities_entity_key"}),
    "semantic_governance_events": frozenset(
        {"uq_semantic_governance_events_dedup_key", "uq_semantic_governance_events_sequence"}
    ),
}

REQUIRED_TABLE_UNIQUE_CONSTRAINT_COLUMNS = {
    "semantic_ontology_snapshots": {
        "uq_semantic_ontology_snapshots_ontology_version": ("ontology_version",)
    },
    "semantic_graph_snapshots": {"uq_semantic_graph_snapshots_graph_version": ("graph_version",)},
    "semantic_concepts": {
        "uq_semantic_concepts_key_registry_version": ("concept_key", "registry_version")
    },
    "semantic_categories": {
        "uq_semantic_categories_key_registry_version": ("category_key", "registry_version")
    },
    "semantic_terms": {
        "uq_semantic_terms_registry_version_normalized_text": (
            "registry_version",
            "normalized_text",
        )
    },
    "semantic_concept_terms": {"uq_semantic_concept_terms_concept_term": ("concept_id", "term_id")},
    "semantic_concept_category_bindings": {
        "uq_semantic_concept_category_bindings_concept_category": ("concept_id", "category_id")
    },
    "document_run_semantic_passes": {
        "uq_document_run_semantic_passes_run_version_tuple": (
            "run_id",
            "registry_version",
            "extractor_version",
            "artifact_schema_version",
        )
    },
    "semantic_assertions": {
        "uq_semantic_assertions_pass_concept_kind": (
            "semantic_pass_id",
            "concept_id",
            "assertion_kind",
        )
    },
    "semantic_assertion_category_bindings": {
        "uq_semantic_assertion_category_bindings_assertion_category": (
            "assertion_id",
            "category_id",
        )
    },
    "semantic_assertion_evidence": {
        "uq_semantic_assertion_evidence_assertion_source": (
            "assertion_id",
            "source_type",
            "source_locator",
        )
    },
    "semantic_entities": {"uq_semantic_entities_entity_key": ("entity_key",)},
    "semantic_governance_events": {
        "uq_semantic_governance_events_dedup_key": ("deduplication_key",),
        "uq_semantic_governance_events_sequence": ("event_sequence",),
    },
}

REQUIRED_VECTOR_DIMENSIONS = {}

REQUIRED_COMPUTED_SQL = {}
