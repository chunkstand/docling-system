from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from app.hotspot_prevention_diff import ChangedFile, ChangedLine, DiffStat
from app.hotspot_prevention_policy import HotspotException, HotspotRule


@dataclass(frozen=True)
class ClassifiedLine:
    line: ChangedLine
    status: str
    category: str
    message: str
    policy_rule: str
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
    classified_lines: list[ClassifiedLine] = []
    forwarding_hunk_ids: set[int] = set()
    reported_alias_hunks: set[int] = set()
    reported_registry_hunks: set[int] = set()
    reported_forwarding_body_hunks: set[int] = set()
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
            if (
                line.hunk_id not in reported_forwarding_body_hunks
                and is_forwarding_call_line(line.text.strip())
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
        ignored_hunk_ids=forwarding_hunk_ids | alias_hunk_ids | registry_hunk_ids,
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
    return set() if allowed_category_for_forwarder(rule) is None else hunk_ids_matching(
        changed_file, is_forwarding_hunk
    )
def alias_only_hunk_ids(rule: HotspotRule, changed_file: ChangedFile) -> set[int]:
    return set() if allowed_category_for_import(rule) is None else hunk_ids_matching(
        changed_file, is_alias_only_hunk
    )
def registry_composition_hunk_ids(rule: HotspotRule, changed_file: ChangedFile) -> set[int]:
    return (
        set()
        if "registry_composition" not in rule.allow
        else hunk_ids_matching(changed_file, is_registry_composition_hunk)
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
        "added_line": None, "exception_id": None, "remediation": None,
    }
def classify_python_addition(
    *,
    rule: HotspotRule,
    changed_file: ChangedFile,
    line: ChangedLine,
) -> ClassifiedLine | None:
    path = changed_file.relative_path
    stripped = line.text.strip()
    hunk_lines = tuple(
        row.text for row in changed_file.added_lines if row.hunk_id == line.hunk_id
    )
    if is_comment_or_blank(line.text):
        return None
    import_category = allowed_category_for_import(rule)
    if import_category and (
        is_import_or_alias(line.text)
        or is_multiline_import_continuation(stripped, hunk_lines)
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
        return blocked(line, "latest_read_logic", "latest-evaluation reads belong in app/services/evaluation_reads.py")  # noqa: E501
    if re.match(r"(async def |def )_((summarize|evaluate)_structural_checks|table_matches_merge_expectation|figure_(provenance|artifact)_count)", stripped) or any(token in lowered for token in ("structural_passed", "expected_merged_tables", "overlay_family_key", "minimum_figures_with_provenance", "maximum_unexpected_merges")):  # noqa: E501
        return blocked(line, "structural_check_logic", "structural evaluation checks belong in app/services/evaluation_scoring.py")  # noqa: E501
    if re.match(r"(async def |def )_((evaluate_(retrieval|answer)_case)|summarize_retrieval_rank_metrics|retrieval_failure_kind|rank_delta|classify_delta|reciprocal_rank)", stripped) or any(token in lowered for token in ("retrieval_rank_metrics", "candidate_rank", "baseline_rank", "rank_delta", "minimum_citation_count", "maximum_foreign_citations")):  # noqa: E501
        return blocked(line, "scoring_logic", "evaluation scoring belongs in app/services/evaluation_scoring.py")  # noqa: E501
    if re.match(r"(async def |def )(_(load_corpus_documents|write_corpus_documents|normalize_fixture_|fixture_|auto_|source_filename_queries)|load_evaluation_fixtures|fixture_for_document|build_auto_evaluation_fixture_document|ensure_auto_evaluation_fixture)", stripped) or any(token in lowered for token in ("fixture", "corpus_path", "yaml.safe_dump", "load_corpus_documents_cached(", "auto_generated_document")):  # noqa: E501
        return blocked(line, "fixture_corpus_logic", "fixture and corpus logic belong in app/services/evaluation_fixtures.py")  # noqa: E501
    if stripped.startswith(("def _", "async def _")):
        return blocked(line, "fixture_corpus_logic", "new evaluation helpers belong in focused evaluation owner modules")  # noqa: E501
    return blocked(line, "latest_read_logic", "new evaluation service behavior belongs in focused evaluation owner modules") if stripped.startswith(("def ", "async def ")) else None  # noqa: E501
def classify_cli_test_addition(*, stripped: str, line: ChangedLine) -> ClassifiedLine | None:
    if not stripped.startswith("def test_"):
        return None
    lowered = stripped.lower()
    if any(token in lowered for token in ("compat", "entrypoint", "forward")):
        return ClassifiedLine(
            line=line,
            status="allowed",
            category="compatibility_assertion",
            message="legacy CLI compatibility assertion is allowed",
            policy_rule="allow.compatibility_assertion",
        )
    return blocked(
        line,
        "broad_new_test_group",
        "new CLI command tests belong in focused tests/unit/test_cli_*.py files",
    )
def is_comment_or_blank(text: str) -> bool:
    stripped = text.strip()
    return not stripped or stripped.startswith("#")
def is_import_or_alias(text: str) -> bool:
    stripped = text.strip()
    return stripped.startswith(("from ", "import ", "__all__")) or bool(
        re.match(r"[A-Za-z_][A-Za-z0-9_]*\s*=\s*[A-Za-z_][A-Za-z0-9_.]*$", stripped)
    )


def is_multiline_import_continuation(text: str, hunk_lines: tuple[str, ...]) -> bool:
    if not re.match(
        r"[A-Za-z_][A-Za-z0-9_]*(\s+as\s+[A-Za-z_][A-Za-z0-9_]*)?,?$",
        text,
    ):
        return False
    return any(
        re.match(r"(from\s+[A-Za-z_][A-Za-z0-9_.]*\s+import|import)\s+\($", raw.strip())
        for raw in hunk_lines
    )
def is_alias_only_hunk(lines: tuple[str, ...]) -> bool:
    significant = [text.strip() for text in lines if not is_comment_or_blank(text)]
    saw_alias = False
    index = 0
    while index < len(significant):
        stripped = significant[index]
        if is_import_or_alias(stripped):
            saw_alias = True
            index += 1
            continue
        if re.match(r"from\s+[A-Za-z_][A-Za-z0-9_.]*\s+import\s+\($", stripped):
            saw_alias = True
            index += 1
            while index < len(significant) and significant[index] != ")":
                if not re.match(
                    r"[A-Za-z_][A-Za-z0-9_]*(\s+as\s+[A-Za-z_][A-Za-z0-9_]*)?,?$",
                    significant[index],
                ):
                    return False
                index += 1
            if index >= len(significant) or significant[index] != ")":
                return False
            index += 1
            continue
        if not re.match(r"[A-Za-z_][A-Za-z0-9_]*\s*=\s*\($", stripped):
            return False
        if index + 2 >= len(significant):
            return False
        target = significant[index + 1]
        closing = significant[index + 2]
        if not re.match(r"[A-Za-z_][A-Za-z0-9_.]*,?$", target):
            return False
        if closing != ")":
            return False
        saw_alias = True
        index += 3
    return saw_alias
def is_forwarding_hunk(lines: tuple[str, ...]) -> bool:
    significant: list[str] = []
    in_signature = False
    for text in lines:
        stripped = text.strip()
        if (
            not stripped
            or stripped.startswith(("#", "@"))
            or stripped in {'"""', "'''", ")"}
            or is_import_or_alias(text)
        ):
            continue
        if stripped.startswith(("def ", "async def ")):
            in_signature = not stripped.endswith(":")
            continue
        if in_signature:
            if stripped.endswith(":") or stripped == "):":
                in_signature = False
            continue
        significant.append(stripped)
    has_forwarding_call = False
    for stripped in significant:
        if re.match(r"\)(\s*->\s*[^:]+)?:", stripped):
            continue
        if re.match(r"return\s+[A-Za-z_][A-Za-z0-9_.]*\(", stripped):
            has_forwarding_call = True
            continue
        if stripped.startswith("raise SystemExit("):
            has_forwarding_call = True
            continue
        if re.match(r"[A-Za-z_][A-Za-z0-9_.]*,?$", stripped):
            continue
        if re.match(
            r"[A-Za-z_][A-Za-z0-9_]*\s*=\s*[A-Za-z_][A-Za-z0-9_.]*,?$",
            stripped,
        ):
            continue
        return False
    return has_forwarding_call
def is_forwarding_call_line(stripped: str) -> bool:
    return bool(re.match(r"return\s+[A-Za-z_][A-Za-z0-9_.]*\(", stripped)) or stripped.startswith(
        "raise SystemExit("
    )
def is_significant_added_text(text: str) -> bool:
    return not is_comment_or_blank(text) and not is_import_or_alias(text)
def is_registry_composition_hunk(lines: tuple[str, ...]) -> bool:
    significant = [raw.strip() for raw in lines if is_significant_added_text(raw)]
    if not significant:
        return False
    has_composition_marker = False
    allowed_tokens = ("compose_action_registries(", "compose_context_builder_registries(",
        "build_", "_REGISTRY", "_BUILDERS", "_executor", "globals()", "build_generic_task_context")
    for stripped in significant:
        if stripped.startswith(("def ", "async def ", "class ")):
            return False
        if stripped in {"(", ")", "),"}:
            continue
        if any(token in stripped for token in allowed_tokens):
            has_composition_marker = True
            continue
        return False
    return has_composition_marker
def allowed_category_for_import(rule: HotspotRule) -> str | None:
    return first_allowed_category(rule, "import_forwarder", "alias_forwarder", "registry_composition")  # noqa: E501
def allowed_category_for_forwarder(rule: HotspotRule) -> str | None:
    return first_allowed_category(rule, "explicit_forwarding_function", "alias_forwarder", "import_forwarder")  # noqa: E501
def first_allowed_category(rule: HotspotRule, *categories: str) -> str | None:
    return next((category for category in categories if category in rule.allow), None)
def significant_unclassified_lines(
    lines: tuple[ChangedLine, ...],
    classified_lines: list[ClassifiedLine],
    *,
    ignored_hunk_ids: set[int] | None = None,
) -> list[ChangedLine]:
    ignored_hunk_ids = ignored_hunk_ids or set()
    classified_keys = {
        (classified.line.new_lineno, classified.line.text)
        for classified in classified_lines
    }
    return [
        line
        for line in lines
        if line.hunk_id not in ignored_hunk_ids
        and (line.new_lineno, line.text) not in classified_keys
        and is_significant_added_text(line.text)
    ]
def fallback_block_category(rule: HotspotRule) -> str:
    return next(
        (category for category in (
            "broad_helper", "artifact_assembly", "broad_parser_logic",
            "executor_implementation", "ranking_logic", "broad_new_test_group",
        ) if category in rule.block_new),
        rule.block_new[0],
    )
def exception_for_additions(
    rule: HotspotRule,
    added_lines: tuple[ChangedLine, ...],
) -> HotspotException | None:
    raw_lines = tuple(line.text for line in added_lines)
    return next((exception for exception in rule.exceptions if exception.matches(raw_lines)), None)
def blocked(line: ChangedLine, category: str, message: str) -> ClassifiedLine:
    return ClassifiedLine(line, "blocked", category, message, f"block_new.{category}")
def finding_payload(
    *,
    classified: ClassifiedLine,
    rule: HotspotRule,
    diff_stat: DiffStat,
    exception: HotspotException | None = None,
) -> dict[str, Any]:
    status = (
        "allowed_exception"
        if exception is not None and classified.status == "blocked"
        else classified.status
    )
    message = classified.message
    if exception is not None and classified.status == "blocked":
        message = f"{message}; allowed by exception {exception.exception_id}"
    return {
        "status": status,
        "category": classified.category,
        "relative_path": rule.relative_path,
        "line": classified.line.new_lineno,
        "policy_rule": classified.policy_rule,
        "target_role": rule.target_role,
        "preferred_owner_modules": list(rule.preferred_owner_modules),
        "added_line_count": diff_stat.added_line_count,
        "deleted_line_count": diff_stat.deleted_line_count,
        "message": message,
        "added_line": classified.line.text.strip(),
        "exception_id": exception.exception_id if exception else None,
        "remediation": (
            f"Move the implementation to {', '.join(rule.preferred_owner_modules)} "
            f"and keep {rule.relative_path} as {rule.target_role}."
        ),
    }
