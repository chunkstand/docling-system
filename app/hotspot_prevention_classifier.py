from __future__ import annotations

import re
from collections.abc import Callable
from typing import Any

from app.hotspot_prevention_classifier_support import (
    LOCAL_TEST_SUPPORT_PATHS,
    RESIDUAL_TEST_COMPATIBILITY_PATHS,
    ClassifiedLine,
    allowed_category_for_forwarder,
    allowed_category_for_import,
    blocked,
    classified_surface_decision,
    classify_cli_test_surface_addition,
    classify_local_test_support_surface_addition,
    classify_residual_test_surface_addition,
    exception_for_additions,
    fallback_block_category,
    finding_payload,
    is_agent_task_schema_alias_line,
    is_agent_task_schema_broad_reexport_hunk,
    is_agent_task_schema_export_sink_line,
    is_agent_task_schema_registry_hunk,
    is_agent_task_schema_registry_line,
    is_alias_only_hunk,
    is_comment_or_blank,
    is_compatibility_test_hunk,
    is_forwarding_call_line,
    is_forwarding_hunk,
    is_import_or_alias,
    is_multiline_import_continuation,
    is_registry_composition_hunk,
    is_test_signature_continuation_hunk,
    significant_unclassified_lines,
)
from app.hotspot_prevention_diff import ChangedFile, ChangedLine, DiffStat
from app.hotspot_prevention_policy import HotspotRule

_CLASS_RE = re.compile(r"class\s+([A-Za-z_][A-Za-z0-9_]*)\b")


def classify_changed_file(
    *,
    rule: HotspotRule,
    changed_file: ChangedFile,
    diff_stat: DiffStat,
) -> list[dict[str, Any]]:
    if not changed_file.added_lines and changed_file.deleted_line_count:
        return [deletion_finding(rule=rule, diff_stat=diff_stat)]
    exception = exception_for_additions(rule, changed_file.added_lines)
    alias_hunk_ids = alias_only_hunk_ids(rule, changed_file)
    registry_hunk_ids = registry_composition_hunk_ids(rule, changed_file)
    forwarding_body_hunk_ids = forwarding_only_body_hunk_ids(rule, changed_file)
    compatibility_test_hunk_ids = compatibility_test_only_hunk_ids(rule, changed_file)
    signature_hunk_ids = test_signature_continuation_hunk_ids(rule, changed_file)
    classified_lines: list[ClassifiedLine] = []
    forwarding_hunk_ids: set[int] = set()
    reported_alias_hunks: set[int] = set()
    reported_registry_hunks: set[int] = set()
    reported_forwarding_body_hunks: set[int] = set()
    reported_compatibility_test_hunks: set[int] = set()
    reported_signature_hunks: set[int] = set()
    findings: list[dict[str, Any]] = []
    for line in changed_file.added_lines:
        if line.hunk_id in alias_hunk_ids:
            if line.hunk_id not in reported_alias_hunks:
                import_category = allowed_category_for_import(rule)
                assert import_category is not None
                classified = ClassifiedLine(
                    line=line,
                    status="allowed",
                    category=import_category,
                    message="facade import or alias maintenance is allowed",
                    policy_rule=f"allow.{import_category}",
                )
                classified_lines.append(classified)
                findings.append(
                    finding_payload(
                        classified=classified,
                        rule=rule,
                        diff_stat=diff_stat,
                        exception=exception,
                    )
                )
                reported_alias_hunks.add(line.hunk_id)
            continue
        if line.hunk_id in registry_hunk_ids:
            if line.hunk_id not in reported_registry_hunks:
                classified = ClassifiedLine(
                    line=line,
                    status="allowed",
                    category="registry_composition",
                    message="owner-registry composition is allowed on the facade",
                    policy_rule="allow.registry_composition",
                )
                classified_lines.append(classified)
                findings.append(
                    finding_payload(
                        classified=classified,
                        rule=rule,
                        diff_stat=diff_stat,
                        exception=exception,
                    )
                )
                reported_registry_hunks.add(line.hunk_id)
            continue
        if line.hunk_id in forwarding_body_hunk_ids:
            forwarding_hunk_ids.add(line.hunk_id)
            if line.hunk_id not in reported_forwarding_body_hunks and is_forwarding_call_line(
                line.text.strip()
            ):
                classified = ClassifiedLine(
                    line=line,
                    status="allowed",
                    category="explicit_forwarding_function",
                    message="narrow forwarding wrapper is allowed",
                    policy_rule="allow.explicit_forwarding_function",
                )
                classified_lines.append(classified)
                findings.append(
                    finding_payload(
                        classified=classified,
                        rule=rule,
                        diff_stat=diff_stat,
                        exception=exception,
                    )
                )
                reported_forwarding_body_hunks.add(line.hunk_id)
            continue
        if line.hunk_id in compatibility_test_hunk_ids:
            if line.hunk_id not in reported_compatibility_test_hunks:
                classified = ClassifiedLine(
                    line=line,
                    status="allowed",
                    category="compatibility_assertion",
                    message="residual compatibility or smoke test hunk is allowed",
                    policy_rule="allow.compatibility_assertion",
                )
                classified_lines.append(classified)
                findings.append(
                    finding_payload(
                        classified=classified,
                        rule=rule,
                        diff_stat=diff_stat,
                        exception=exception,
                    )
                )
                reported_compatibility_test_hunks.add(line.hunk_id)
            continue
        if line.hunk_id in signature_hunk_ids:
            if line.hunk_id not in reported_signature_hunks:
                classified = ClassifiedLine(
                    line=line,
                    status="allowed",
                    category="compatibility_assertion",
                    message="residual test signature maintenance is allowed",
                    policy_rule="allow.compatibility_assertion",
                )
                classified_lines.append(classified)
                findings.append(
                    finding_payload(
                        classified=classified,
                        rule=rule,
                        diff_stat=diff_stat,
                        exception=exception,
                    )
                )
                reported_signature_hunks.add(line.hunk_id)
            continue
        classified = classify_python_addition(rule=rule, changed_file=changed_file, line=line)
        if classified is None:
            continue
        classified_lines.append(classified)
        if classified.policy_rule == "allow.explicit_forwarding_function":
            forwarding_hunk_ids.add(line.hunk_id)
        findings.append(
            finding_payload(
                classified=classified,
                rule=rule,
                diff_stat=diff_stat,
                exception=exception,
            )
        )
    significant = significant_unclassified_lines(
        changed_file.added_lines,
        classified_lines,
        ignored_hunk_ids=(
            forwarding_hunk_ids
            | alias_hunk_ids
            | registry_hunk_ids
            | compatibility_test_hunk_ids
            | signature_hunk_ids
        ),
    )
    if len(significant) >= 8:
        classified = blocked(
            significant[0],
            fallback_block_category(rule),
            "large unclassified implementation block added to a known hotspot",
        )
        findings.append(
            finding_payload(
                classified=classified,
                rule=rule,
                diff_stat=diff_stat,
                exception=exception,
            )
        )
    return findings


def forwarding_only_body_hunk_ids(rule: HotspotRule, changed_file: ChangedFile) -> set[int]:
    return (
        set()
        if allowed_category_for_forwarder(rule) is None
        else hunk_ids_matching(changed_file, is_forwarding_hunk)
    )


def alias_only_hunk_ids(rule: HotspotRule, changed_file: ChangedFile) -> set[int]:
    return (
        set()
        if allowed_category_for_import(rule) is None
        else hunk_ids_matching(changed_file, is_alias_only_hunk)
    )


def registry_composition_hunk_ids(rule: HotspotRule, changed_file: ChangedFile) -> set[int]:
    return (
        set()
        if "registry_composition" not in rule.allow
        else hunk_ids_matching(changed_file, is_registry_composition_hunk)
    )


def compatibility_test_only_hunk_ids(rule: HotspotRule, changed_file: ChangedFile) -> set[int]:
    return (
        set()
        if "compatibility_assertion" not in rule.allow
        else hunk_ids_matching(changed_file, is_compatibility_test_hunk)
    )


def test_signature_continuation_hunk_ids(rule: HotspotRule, changed_file: ChangedFile) -> set[int]:
    return (
        set()
        if "compatibility_assertion" not in rule.allow
        else hunk_ids_matching(changed_file, is_test_signature_continuation_hunk)
    )


def hunk_ids_matching(
    changed_file: ChangedFile,
    predicate: Callable[[tuple[str, ...]], bool],
) -> set[int]:
    lines_by_hunk: dict[int, list[str]] = {}
    for line in changed_file.added_lines:
        lines_by_hunk.setdefault(line.hunk_id, []).append(line.text)
    return {
        hunk_id for hunk_id, hunk_lines in lines_by_hunk.items() if predicate(tuple(hunk_lines))
    }


def deletion_finding(*, rule: HotspotRule, diff_stat: DiffStat) -> dict[str, Any]:
    return {
        "status": "allowed",
        "category": "deletion",
        "relative_path": rule.relative_path,
        "line": None,
        "policy_rule": "allow.deletion",
        "target_role": rule.target_role,
        "preferred_owner_modules": list(rule.preferred_owner_modules),
        "added_line_count": diff_stat.added_line_count,
        "deleted_line_count": diff_stat.deleted_line_count,
        "message": "deletion-only hotspot reduction is allowed",
        "added_line": None,
        "exception_id": None,
        "remediation": None,
    }


def classify_python_addition(
    *,
    rule: HotspotRule,
    changed_file: ChangedFile,
    line: ChangedLine,
) -> ClassifiedLine | None:
    path = changed_file.relative_path
    stripped = line.text.strip()
    hunk_lines = tuple(row.text for row in changed_file.added_lines if row.hunk_id == line.hunk_id)
    if is_comment_or_blank(line.text):
        return None
    if path == "app/schemas/agent_tasks.py":
        return classify_agent_task_schema_facade_addition(
            stripped=stripped,
            line=line,
            hunk_lines=hunk_lines,
        )
    import_category = allowed_category_for_import(rule)
    if import_category and (
        is_import_or_alias(line.text) or is_multiline_import_continuation(stripped, hunk_lines)
    ):
        return ClassifiedLine(
            line=line,
            status="allowed",
            category=import_category,
            message="facade import or alias maintenance is allowed",
            policy_rule=f"allow.{import_category}",
        )
    forwarding_category = allowed_category_for_forwarder(rule)
    is_forwarding_def = stripped.startswith(("def ", "async def ")) and is_forwarding_hunk(
        hunk_lines
    )
    if forwarding_category and is_forwarding_def:
        return ClassifiedLine(
            line=line,
            status="allowed",
            category=forwarding_category,
            message="narrow forwarding wrapper is allowed",
            policy_rule=f"allow.{forwarding_category}",
        )
    return classify_hotspot_implementation(path=path, stripped=stripped, line=line, rule=rule)


def classify_hotspot_implementation(
    *,
    path: str,
    stripped: str,
    line: ChangedLine,
    rule: HotspotRule,
) -> ClassifiedLine | None:
    if path == "app/cli.py":
        return classify_cli_addition(stripped=stripped, line=line, rule=rule)
    if path in RESIDUAL_TEST_COMPATIBILITY_PATHS:
        return classify_residual_test_addition(stripped=stripped, line=line)
    if path in LOCAL_TEST_SUPPORT_PATHS:
        return classify_local_test_support_addition(stripped=stripped, line=line)
    classifiers = {
        "app/db/models.py": classify_model_addition,
        "app/services/evidence.py": classify_evidence_addition,
        "app/services/evidence_provenance_exports.py": (
            classify_evidence_provenance_export_addition
        ),
        "app/services/agent_task_actions.py": classify_agent_action_addition,
        "app/services/agent_task_context.py": classify_agent_task_context_addition,
        "app/services/search.py": classify_search_addition,
        "app/services/semantics.py": classify_semantics_addition,
        "app/services/claim_support_policy_impacts.py": (
            classify_claim_support_policy_impact_addition
        ),
        "app/services/evaluations.py": classify_evaluations_addition,
        "tests/unit/test_cli.py": classify_cli_test_addition,
    }
    classifier = classifiers.get(path)
    return classifier(stripped=stripped, line=line) if classifier else None


def classify_model_addition(*, stripped: str, line: ChangedLine) -> ClassifiedLine | None:
    if "relationship(" in stripped:
        return blocked(
            line, "relationship_logic", "new relationship logic belongs in a model domain"
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


def classify_agent_task_schema_facade_addition(
    *,
    stripped: str,
    line: ChangedLine,
    hunk_lines: tuple[str, ...],
) -> ClassifiedLine | None:
    if is_agent_task_schema_registry_hunk(hunk_lines) or is_agent_task_schema_registry_line(
        stripped
    ):
        return ClassifiedLine(
            line=line,
            status="allowed",
            category="compatibility_registry_declaration",
            message="compact schema compatibility-registry declaration is allowed",
            policy_rule="allow.compatibility_registry_declaration",
        )
    if is_agent_task_schema_alias_line(stripped):
        return ClassifiedLine(
            line=line,
            status="allowed",
            category="schema_alias_forwarder",
            message="explicit schema alias forwarders are allowed on the facade",
            policy_rule="allow.schema_alias_forwarder",
        )
    if _CLASS_RE.match(stripped):
        return blocked(
            line,
            "schema_definition",
            "new schema definitions belong in the focused agent-task schema owner modules",
        )
    if stripped.startswith(("def ", "async def ")):
        return blocked(
            line,
            "export_sink_surface",
            "new schema-facade helpers or export sinks do not belong in app/schemas/agent_tasks.py",
        )
    if is_agent_task_schema_export_sink_line(stripped):
        return blocked(
            line,
            "export_sink_surface",
            "new export-sink surfaces do not belong in app/schemas/agent_tasks.py",
        )
    if is_agent_task_schema_broad_reexport_hunk(hunk_lines):
        return blocked(
            line,
            "broad_reexport_batch",
            "broad direct re-export batches do not belong in app/schemas/agent_tasks.py",
        )
    return blocked(
        line,
        "export_sink_surface",
        "new schema-facade behavior belongs in the focused owner modules or a "
        "compact registry declaration",
    )


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


def classify_cli_addition(
    *,
    stripped: str,
    line: ChangedLine,
    rule: HotspotRule,
) -> ClassifiedLine | None:
    parser_registration = "add_parser(" in stripped or ".set_defaults(" in stripped
    if parser_registration and "parser_registration" in rule.allow:
        return ClassifiedLine(
            line=line,
            status="allowed",
            category="parser_registration",
            message="parser registration is allowed on the CLI facade",
            policy_rule="allow.parser_registration",
        )
    if stripped.startswith(("def ", "async def ")):
        return blocked(
            line,
            "command_implementation",
            "new command bodies belong in app/cli_commands/",
        )
    if "ArgumentParser(" in stripped:
        return blocked(
            line,
            "broad_parser_logic",
            "broad parser logic belongs in app/cli_commands/",
        )
    if any(
        token in stripped
        for token in (
            "session_factory = get_session_factory()",
            "with session_factory() as session",
            "storage_service = StorageService(",
            "storage_service=StorageService(",
        )
    ):
        return blocked(
            line,
            "session_or_storage_wiring",
            "session or storage wiring belongs in app/cli_commands/",
        )
    if any(
        token in stripped
        for token in (
            "parser.add_argument(",
            "parser.parse_args(",
            "parser.error(",
            "json.dumps(",
            "model_dump(",
        )
    ):
        return blocked(
            line,
            "json_render_or_parser_body_scaffolding",
            "parser-body and JSON-render scaffolding belongs in app/cli_commands/",
        )
    return None


def classify_agent_action_addition(*, stripped: str, line: ChangedLine) -> ClassifiedLine | None:
    if stripped.startswith("class "):
        return blocked(
            line,
            "schema_builder",
            "new action schemas belong in app/services/agent_actions/",
        )
    if stripped.startswith(("def _", "async def _")):
        return blocked(
            line,
            "action_family_helper",
            "new action-family helpers belong in app/services/agent_actions/",
        )
    if stripped.startswith(("def ", "async def ")):
        return blocked(
            line,
            "executor_implementation",
            "new executor implementations belong in app/services/agent_actions/",
        )
    return None


def classify_agent_task_context_addition(
    *,
    stripped: str,
    line: ChangedLine,
) -> ClassifiedLine | None:
    if stripped.startswith("class "):
        return blocked(
            line,
            "context_builder_implementation",
            "new context contracts belong in app/services/agent_task_context_*.py",
        )
    if stripped.startswith(("def _build_", "async def _build_")):
        return blocked(
            line,
            "context_builder_implementation",
            "new context builders belong in app/services/agent_task_context_*.py",
        )
    if stripped.startswith(("def _", "async def _")):
        return blocked(
            line,
            "context_family_helper",
            "new context helpers belong in app/services/agent_task_context_*.py",
        )
    if stripped.startswith(("def ", "async def ")):
        return blocked(
            line,
            "context_builder_implementation",
            "new context composition belongs in app/services/agent_task_context_*.py",
        )
    return None


def classify_search_addition(*, stripped: str, line: ChangedLine) -> ClassifiedLine | None:
    lowered = stripped.lower()
    if re.match(r"(async def |def )_load_.*candidate", stripped):
        return blocked(line, "candidate_loading", "candidate loading belongs in search_* modules")
    if re.match(r"(async def |def )_build_search_execution_details", stripped):
        return blocked(line, "search_detail_payload_builder", "detail assembly belongs in search_*")
    is_execution_def = re.match(
        r"(async def |def )_(resolve_candidate_items|run_execution_|execute_search)",
        stripped,
    )
    if is_execution_def or any(
        token in stripped for token in ("build_search_execution_plan(", "SearchStage.")
    ):
        return blocked(line, "execution_orchestration", "execution flow belongs in search_*")
    if re.match(r"(async def |def )_persist_", stripped) or any(
        token in stripped
        for token in (
            "SearchRequestRecord(",
            "SearchRequestResult(",
            "SearchRequestResultSpan(",
        )
    ):
        return blocked(line, "persistence_logic", "search persistence belongs in search_* modules")
    if re.match(
        r"(async def |def )_((ranked|reranked)_result_evidence_payload|build_operator_trace_)",
        stripped,
    ) or any(
        token in lowered
        for token in (
            "record_knowledge_operator_run(",
            "output_payload",
            "selected_evidence",
            "knowledge_operator_runs",
        )
    ):
        return blocked(
            line,
            "operator_trace_payload_builder",
            "operator-trace payloads belong in search_* modules",
        )
    if stripped.startswith(("def _", "async def _")):
        return blocked(line, "query_feature_helper", "search helpers belong in search_* modules")
    if stripped.startswith(("def ", "async def ")):
        return blocked(line, "ranking_logic", "new search behavior belongs in search_* modules")
    if any(token in lowered for token in ("rank", "score", "hydrate", "telemetry")):
        return blocked(line, "ranking_logic", "new search logic belongs in search_* modules")
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


def classify_claim_support_policy_impact_addition(
    *,
    stripped: str,
    line: ChangedLine,
) -> ClassifiedLine | None:
    lowered = stripped.lower()
    closure_patterns = (
        r"(async def |def )_replay_closure_",
        r"(async def |def )_record_replay_closure_governance_event",
    )
    if any(re.match(pattern, stripped) for pattern in closure_patterns) or (
        "claim_support_policy_impact_replay_closure" in lowered
    ):
        return blocked(
            line,
            "replay_closure_receipt_logic",
            "replay closure receipts belong in claim_support_policy_impact_replay.py",
        )
    alert_patterns = (
        r"(async def |def )_(alert_|fresh_alert_worklist_item)",
        (
            r"(async def |def )_("
            r"record_alert_escalation_event|"
            r"refresh_existing_evidence_manifests_for_alert_item)"
        ),
        r"(async def |def )claim_support_policy_change_impact_alerts",
        r"(async def |def )record_claim_support_policy_change_impact_alert_escalations",
    )
    if any(re.match(pattern, stripped) for pattern in alert_patterns) or (
        "alert" in lowered and "worklist" in lowered
    ):
        return blocked(
            line,
            "alert_projection_or_escalation_logic",
            "alert projection and escalation logic belong in claim_support_policy_impact_views.py",
        )
    replay_patterns = (
        r"(async def |def )_(verify_replay_|replay_response|validated_replay_work_items)",
        r"(async def |def )_(recommended_source_task|created_task_spec|queue_agent_task)",
        r"(async def |def )queue_claim_support_policy_change_impact_replay_tasks",
        r"(async def |def )refresh_claim_support_policy_change_impact_replay_status",
        r"(async def |def )refresh_claim_support_policy_change_impacts_for_replay_task",
    )
    if any(re.match(pattern, stripped) for pattern in replay_patterns) or (
        "replay" in lowered and any(token in lowered for token in ("queue", "refresh", "closure"))
    ):
        return blocked(
            line,
            "replay_lifecycle_logic",
            "replay queueing and refresh logic belong in claim_support_policy_impact_replay.py",
        )
    read_model_patterns = (
        r"(async def |def )_(uuid_list|get_impact_row|impact_response|hours_since|worklist_)",
        r"(async def |def )list_claim_support_policy_change_impacts",
        r"(async def |def )summarize_claim_support_policy_change_impacts",
        r"(async def |def )claim_support_policy_change_impact_worklist",
        r"(async def |def )get_claim_support_policy_change_impact",
    )
    if any(re.match(pattern, stripped) for pattern in read_model_patterns):
        return blocked(
            line,
            "read_model_worklist_logic",
            "claim-support read-model logic belongs in claim_support_policy_impact_views.py",
        )
    if stripped.startswith(("def _", "async def _")):
        return blocked(
            line,
            "read_model_worklist_logic",
            "claim-support policy impact helpers belong in claim_support_policy_impact_*.py",
        )
    if stripped.startswith(("def ", "async def ")):
        return blocked(
            line,
            "read_model_worklist_logic",
            "claim-support policy impact service behavior belongs in "
            "claim_support_policy_impact_*.py",
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


def classify_cli_test_addition(*, stripped: str, line: ChangedLine) -> ClassifiedLine | None:
    return classified_surface_decision(
        line=line,
        decision=classify_cli_test_surface_addition(stripped=stripped),
    )


def classify_residual_test_addition(*, stripped: str, line: ChangedLine) -> ClassifiedLine | None:
    return classified_surface_decision(
        line=line,
        decision=classify_residual_test_surface_addition(stripped=stripped),
    )


def classify_local_test_support_addition(
    *, stripped: str, line: ChangedLine
) -> ClassifiedLine | None:
    return classified_surface_decision(
        line=line,
        decision=classify_local_test_support_surface_addition(stripped=stripped),
    )
