from __future__ import annotations

import re

from app.hotspot_prevention_classifier_support import ClassifiedLine, blocked
from app.hotspot_prevention_diff import ChangedLine

_CLASS_RE = re.compile(r"class\s+([A-Za-z_][A-Za-z0-9_]*)\b")


def classify_model_addition(*, stripped: str, line: ChangedLine) -> ClassifiedLine | None:
    if "relationship(" in stripped:
        return blocked(
            line,
            "relationship_logic",
            "new relationship logic belongs in a model domain",
        )
    if _CLASS_RE.match(stripped):
        category = "enum" if "Enum" in stripped else "orm_class"
        return blocked(line, category, "new ORM or enum classes belong in app/db/model_domains/")
    return (
        blocked(line, "broad_helper", "new model helpers belong in a focused owner module")
        if stripped.startswith(("def ", "async def "))
        else None
    )


def classify_evidence_addition(*, stripped: str, line: ChangedLine) -> ClassifiedLine | None:
    if stripped.startswith(("def _", "async def _")):
        return blocked(line, "private_helper", "new evidence helpers belong in evidence_* modules")
    if stripped.startswith(("def ", "async def ", "class ")):
        return blocked(
            line, "payload_builder", "new evidence behavior belongs in evidence_* modules"
        )
    if any(token in stripped for token in ("write_text(", "json.dumps(", "artifact", "payload")):
        return blocked(
            line, "artifact_assembly", "new evidence assembly belongs in evidence_* modules"
        )
    return None


def classify_evidence_provenance_export_addition(
    *,
    stripped: str,
    line: ChangedLine,
) -> ClassifiedLine | None:
    lowered = stripped.lower()
    graph_patterns = (
        r"(async def |def )_(build_|populate_|finalize_)",
        r"(async def |def )build_agent_task_provenance_export",
    )
    lineage_tokens = (
        "claim_retrieval_feedback",
        "claim_derivations",
        "evidence_cards",
        "operator_runs",
        "report_trace",
    )
    lifecycle_tokens = (
        "persist_agent_task_provenance_export",
        "get_agent_task_provenance_export",
        "existing_prov_export_artifact",
        "record_prov_export_supersession_attempt",
        "technical_report_prov_export_filename",
        "technical_report_prov_export_artifact_kind",
        "write_text(",
        "json.dumps(",
        "frozen_prov_export_payload(",
        "supersession_attempt",
    )
    governance_tokens = (
        "change_impact",
        "evidencepackageexport",
        "record_technical_report_prov_export_governance_event",
        "technical_report_change_impact_for_governance",
    )
    if any(re.match(pattern, stripped) for pattern in graph_patterns) or any(
        token in lowered
        for token in (
            "was_generated_by",
            "was_derived_from",
            "was_associated_with",
            "was_attributed_to",
            "prov_identifier(",
            "state.add_entity(",
            "state.add_activity(",
            "state.add_generated(",
            "state.add_used(",
            "state.add_derived(",
        )
    ):
        return blocked(
            line,
            "provenance_graph_logic",
            "provenance graph assembly belongs in the provenance-export owner modules",
        )
    if any(token in lowered for token in lineage_tokens):
        return blocked(
            line,
            "report_trace_lineage_logic",
            "report-trace lineage belongs in "
            "app/services/evidence_provenance_export_graph_report.py",
        )
    if any(token in lowered for token in lifecycle_tokens):
        return blocked(
            line,
            "export_lifecycle_logic",
            "provenance export lifecycle behavior belongs in "
            "app/services/evidence_provenance_export_lifecycle.py",
        )
    if any(token in lowered for token in governance_tokens):
        return blocked(
            line,
            "governance_change_impact_logic",
            "governance change-impact logic belongs in "
            "app/services/evidence_provenance_export_lifecycle.py",
        )
    if stripped.startswith(("def _", "async def _", "def ", "async def ", "class ")):
        return blocked(
            line,
            "provenance_graph_logic",
            "new provenance-export behavior belongs in the focused provenance owner modules",
        )
    return None
def classify_semantics_addition(*, stripped: str, line: ChangedLine) -> ClassifiedLine | None:
    lowered = stripped.lower()
    preview_tokens = (
        "preview_semantic_registry_update_for_document",
        "_preview_assertions",
        "_preview_concept_category_bindings",
        "introduced_expected_concepts",
        "regressed_expected_concepts",
        "semantic_evaluation_result",
        "candidate_registry_version",
    )
    read_tokens = (
        "get_active_semantic_pass_row",
        "get_active_semantic_pass_detail",
        "get_active_semantic_continuity",
        "_assertion_records",
        "_concept_category_binding_records",
        "_continuity_summary",
        "documentsemanticpassresponse",
        "semanticcontinuityresponse",
        "semanticassertionresponse",
    )
    review_tokens = (
        "_refresh_semantic_pass_projection",
        "review_active_semantic_assertion",
        "review_active_semantic_assertion_category_binding",
        "documentsemanticconceptreview",
        "documentsemanticcategoryreview",
        "review_overlay",
    )
    lifecycle_tokens = (
        "_prepare_semantic_pass_row",
        "execute_semantic_pass",
        "_sync_registry_definitions",
        "_replace_pass_assertions",
        "_persist_semantic_artifacts",
        "documentrunsemanticpass",
        "semanticpassstatus",
    )
    if any(token in lowered for token in preview_tokens):
        return blocked(
            line,
            "registry_preview_expectation_logic",
            "semantic registry preview and expectation-delta logic belongs in "
            "app/services/semantic_registry_preview.py",
        )
    if any(token in lowered for token in read_tokens):
        return blocked(
            line,
            "active_pass_read_logic",
            "active-pass read logic belongs in app/services/semantic_pass_reads.py",
        )
    if any(token in lowered for token in review_tokens):
        return blocked(
            line,
            "projection_refresh_review_logic",
            "projection refresh and review persistence belongs in "
            "app/services/semantic_pass_lifecycle.py",
        )
    if any(token in lowered for token in lifecycle_tokens):
        return blocked(
            line,
            "semantic_pass_lifecycle_logic",
            "semantic pass lifecycle logic belongs in app/services/semantic_pass_lifecycle.py",
        )
    if stripped.startswith(("def _", "async def _", "def ", "async def ", "class ")):
        return blocked(
            line,
            "semantic_pass_lifecycle_logic",
            "new semantics behavior belongs in the focused semantic owner modules",
        )
    return None


def classify_evaluations_addition(*, stripped: str, line: ChangedLine) -> ClassifiedLine | None:
    lowered = stripped.lower()
    if re.match(r"(async def |def )(get_latest_|_to_evaluation_summary)", stripped):  # noqa: E501
        return blocked(
            line,
            "latest_read_logic",
            "latest-evaluation reads belong in app/services/evaluation_reads.py",
        )  # noqa: E501
    structural_pattern = (
        r"(async def |def )_((summarize|evaluate)_structural_checks|"
        r"table_matches_merge_expectation|figure_(provenance|artifact)_count)"
    )
    if re.match(
        structural_pattern,
        stripped,
    ) or any(
        token in lowered
        for token in (
            "structural_passed",
            "expected_merged_tables",
            "overlay_family_key",
            "minimum_figures_with_provenance",
            "maximum_unexpected_merges",
        )
    ):  # noqa: E501
        return blocked(
            line,
            "structural_check_logic",
            "structural evaluation checks belong in app/services/evaluation_scoring.py",
        )  # noqa: E501
    scoring_pattern = (
        r"(async def |def )_((evaluate_(retrieval|answer)_case)|"
        r"summarize_retrieval_rank_metrics|retrieval_failure_kind|"
        r"rank_delta|classify_delta|reciprocal_rank)"
    )
    if re.match(
        scoring_pattern,
        stripped,
    ) or any(
        token in lowered
        for token in (
            "retrieval_rank_metrics",
            "candidate_rank",
            "baseline_rank",
            "rank_delta",
            "minimum_citation_count",
            "maximum_foreign_citations",
        )
    ):  # noqa: E501
        return blocked(
            line,
            "scoring_logic",
            "evaluation scoring belongs in app/services/evaluation_scoring.py",
        )  # noqa: E501
    fixture_pattern = (
        r"(async def |def )(_(load_corpus_documents|write_corpus_documents|"
        r"normalize_fixture_|fixture_|auto_|source_filename_queries)|"
        r"load_evaluation_fixtures|fixture_for_document|"
        r"build_auto_evaluation_fixture_document|ensure_auto_evaluation_fixture)"
    )
    if re.match(
        fixture_pattern,
        stripped,
    ) or any(
        token in lowered
        for token in (
            "fixture",
            "corpus_path",
            "yaml.safe_dump",
            "load_corpus_documents_cached(",
            "auto_generated_document",
        )
    ):  # noqa: E501
        return blocked(
            line,
            "fixture_corpus_logic",
            "fixture and corpus logic belong in app/services/evaluation_fixtures.py",
        )  # noqa: E501
    if stripped.startswith(("def _", "async def _")):
        return blocked(
            line,
            "fixture_corpus_logic",
            "new evaluation helpers belong in focused evaluation owner modules",
        )  # noqa: E501
    return (
        blocked(
            line,
            "latest_read_logic",
            "new evaluation service behavior belongs in focused evaluation owner modules",
        )
        if stripped.startswith(("def ", "async def "))
        else None
    )  # noqa: E501
