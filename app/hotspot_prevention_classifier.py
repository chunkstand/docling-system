from __future__ import annotations

from pathlib import Path
from typing import Any

import app.hotspot_prevention_classifier_boundary_rules as _boundary_rules
import app.hotspot_prevention_classifier_schema_facades as _schema_facades
import app.hotspot_prevention_classifier_service_rules as _service_rules
from app.hotspot_prevention_claim_support_rules import (
    classify_claim_support_evaluations_addition,
    classify_claim_support_policy_governance_addition,
    classify_claim_support_policy_impact_replay_addition,
    classify_claim_support_policy_impact_views_addition,
    classify_claim_support_policy_impacts_addition,
    classify_claim_support_replay_alert_fixture_corpus_addition,
    classify_claim_support_replay_alert_promotions_addition,
)
from app.hotspot_prevention_classifier_support import (
    LOCAL_TEST_SUPPORT_PATHS,
    RESIDUAL_TEST_COMPATIBILITY_PATHS,
    ClassifiedLine,
    alias_only_hunk_ids,
    allowed_category_for_forwarder,
    allowed_category_for_import,
    blocked,
    compatibility_test_only_hunk_ids,
    deletion_finding,
    exception_for_additions,
    fallback_block_category,
    finding_payload,
    forwarding_only_body_hunk_ids,
    is_comment_or_blank,
    is_forwarding_call_line,
    is_forwarding_hunk,
    is_import_or_alias,
    is_multiline_import_continuation,
    registry_composition_hunk_ids,
    significant_unclassified_lines,
    test_signature_continuation_hunk_ids,
)
from app.hotspot_prevention_diff import ChangedFile, ChangedLine, DiffStat
from app.hotspot_prevention_policy import HotspotRule

_CLAIM_SUPPORT_COMPACT_SURFACE_PATHS = {
    "app/services/claim_support_evaluations.py",
    "app/services/claim_support_policy_governance.py",
    "app/services/claim_support_policy_impact_views.py",
    "app/services/claim_support_policy_impact_replay.py",
    "app/services/claim_support_replay_alert_fixture_corpus.py",
    "app/services/claim_support_replay_alert_promotions.py",
}
_COMPACT_SURFACE_MAX_LINES = 600
_SCHEMA_FACADE_CLASSIFIERS = {
    "app/schemas/agent_tasks.py": _schema_facades.classify_agent_task_schema_facade_addition,
    "app/schemas/search.py": _schema_facades.classify_search_schema_facade_addition,
}

def classify_changed_file(
    *,
    rule: HotspotRule,
    changed_file: ChangedFile,
    diff_stat: DiffStat,
) -> list[dict[str, Any]]:
    if not changed_file.added_lines and changed_file.deleted_line_count:
        return [deletion_finding(rule=rule, diff_stat=diff_stat)]
    if _allow_claim_support_compact_surface_reduction(changed_file, diff_stat):
        classified = ClassifiedLine(
            line=changed_file.added_lines[0],
            status="allowed",
            category="net_reduction_refactor",
            message="substantial reduction to a compact claim-support surface is allowed",
            policy_rule="allow.net_reduction_refactor",
        )
        return [
            finding_payload(
                classified=classified,
                rule=rule,
                diff_stat=diff_stat,
                exception=None,
            )
        ]
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


def _allow_claim_support_compact_surface_reduction(
    changed_file: ChangedFile,
    diff_stat: DiffStat,
) -> bool:
    if changed_file.relative_path not in _CLAIM_SUPPORT_COMPACT_SURFACE_PATHS:
        return False
    if diff_stat.deleted_line_count < max(25, diff_stat.added_line_count):
        return False
    path = Path(changed_file.relative_path)
    if not path.exists():
        return False
    return sum(1 for _ in path.open()) <= _COMPACT_SURFACE_MAX_LINES


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
    schema_classifier = _SCHEMA_FACADE_CLASSIFIERS.get(path)
    if schema_classifier is not None:
        return schema_classifier(stripped=stripped, line=line, hunk_lines=hunk_lines)
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
        return _boundary_rules.classify_cli_addition(stripped=stripped, line=line, rule=rule)
    if path in RESIDUAL_TEST_COMPATIBILITY_PATHS:
        return _boundary_rules.classify_residual_test_addition(stripped=stripped, line=line)
    if path in LOCAL_TEST_SUPPORT_PATHS:
        return _boundary_rules.classify_local_test_support_addition(
            stripped=stripped,
            line=line,
        )
    if path == "app/api/routers/agent_tasks.py":
        return _boundary_rules.classify_agent_task_router_addition(
            stripped=stripped,
            line=line,
            rule=rule,
        )
    classifiers = {
        "app/db/models.py": _service_rules.classify_model_addition,
        "app/services/evidence.py": _service_rules.classify_evidence_addition,
        "app/services/evidence_provenance_exports.py": (
            _service_rules.classify_evidence_provenance_export_addition
        ),
        "app/services/agent_task_actions.py": _boundary_rules.classify_agent_action_addition,
        "app/services/agent_task_context.py": _boundary_rules.classify_agent_task_context_addition,
        "app/services/search.py": _service_rules.classify_search_addition,
        "app/services/semantics.py": _service_rules.classify_semantics_addition,
        "app/services/claim_support_policy_impacts.py": (
            classify_claim_support_policy_impacts_addition
        ),
        "app/services/claim_support_policy_impact_views.py": (
            classify_claim_support_policy_impact_views_addition
        ),
        "app/services/claim_support_policy_impact_replay.py": (
            classify_claim_support_policy_impact_replay_addition
        ),
        "app/services/claim_support_replay_alert_promotions.py": (
            classify_claim_support_replay_alert_promotions_addition
        ),
        "app/services/claim_support_evaluations.py": (
            classify_claim_support_evaluations_addition
        ),
        "app/services/claim_support_policy_governance.py": (
            classify_claim_support_policy_governance_addition
        ),
        "app/services/claim_support_replay_alert_fixture_corpus.py": (
            classify_claim_support_replay_alert_fixture_corpus_addition
        ),
        "app/services/evaluations.py": _service_rules.classify_evaluations_addition,
        "tests/unit/test_cli.py": _boundary_rules.classify_cli_test_addition,
    }
    classifier = classifiers.get(path)
    return classifier(stripped=stripped, line=line) if classifier else None
