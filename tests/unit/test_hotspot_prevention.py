from __future__ import annotations

import json
import tomllib
from datetime import date
from pathlib import Path

import yaml

from app.hotspot_prevention import (
    POLICY_SCHEMA_NAME,
    REPORT_SCHEMA_NAME,
    build_hotspot_policy,
    build_hotspot_prevention_report,
    collect_git_diff,
    collect_git_numstat,
    load_hotspot_policy,
    parse_numstat,
    run,
    validate_policy_payload,
)


def _diff_for(path: str, added_lines: list[str], *, deleted_lines: list[str] | None = None) -> str:
    deleted = deleted_lines or []
    lines = [
        f"diff --git a/{path} b/{path}",
        f"--- a/{path}",
        f"+++ b/{path}",
        f"@@ -1,{max(len(deleted), 1)} +1,{max(len(added_lines), 1)} @@",
    ]
    lines.extend(f"-{line}" for line in deleted)
    lines.extend(f"+{line}" for line in added_lines)
    return "\n".join(lines) + "\n"


def _policy_for(path: str, *, exceptions: list[dict] | None = None):
    return build_hotspot_policy(
        {
            "schema_name": POLICY_SCHEMA_NAME,
            "schema_version": "1.0",
            "known_hotspots": {
                path: {
                    "target_role": "compatibility facade",
                    "preferred_owner_modules": ["app/owner/"],
                    "block_new": [
                        "orm_class",
                        "private_helper",
                        "command_implementation",
                        "executor_implementation",
                        "ranking_logic",
                        "broad_new_test_group",
                        "broad_helper",
                        "artifact_assembly",
                    ],
                    "allow": [
                        "import_forwarder",
                        "alias_forwarder",
                        "explicit_forwarding_function",
                        "parser_registration",
                        "compatibility_assertion",
                        "deletion",
                    ],
                    "exceptions": exceptions or [],
                }
            },
        }
    )


def test_current_hotspot_policy_loads_expected_surfaces() -> None:
    policy = load_hotspot_policy()

    assert sorted(policy.known_hotspots) == [
        "app/cli.py",
        "app/db/models.py",
        "app/services/agent_task_actions.py",
        "app/services/agent_task_context.py",
        "app/services/claim_support_policy_impacts.py",
        "app/services/evaluations.py",
        "app/services/evidence.py",
        "app/services/evidence_provenance_exports.py",
        "app/services/search.py",
        "tests/unit/test_cli.py",
    ]
    for rule in policy.known_hotspots.values():
        assert rule.preferred_owner_modules
        assert rule.block_new


def test_policy_validation_rejects_missing_owner_and_unowned_exception() -> None:
    payload = {
        "schema_name": POLICY_SCHEMA_NAME,
        "schema_version": "1.0",
        "known_hotspots": {
            "app/services/evidence.py": {
                "target_role": "compatibility facade",
                "preferred_owner_modules": [],
                "block_new": ["private_helper"],
                "allow": ["import_forwarder"],
                "exceptions": [
                    {
                        "exception_id": "temporary",
                        "follow_up_condition": "remove after split",
                    }
                ],
            }
        },
    }

    issues = validate_policy_payload(payload)

    fields = {issue.field for issue in issues}
    assert "known_hotspots.app/services/evidence.py.preferred_owner_modules" in fields
    assert "known_hotspots.app/services/evidence.py.exceptions[0].case_id" in fields
    assert "known_hotspots.app/services/evidence.py.exceptions[0].owner_module" in fields


def test_policy_validation_rejects_expired_exceptions() -> None:
    payload = {
        "schema_name": POLICY_SCHEMA_NAME,
        "schema_version": "1.0",
        "known_hotspots": {
            "app/services/evidence.py": {
                "target_role": "compatibility facade",
                "preferred_owner_modules": ["app/services/evidence_new.py"],
                "block_new": ["private_helper"],
                "allow": ["import_forwarder"],
                "exceptions": [
                    {
                        "exception_id": "temporary",
                        "milestone_id": "residual-weakness-milestone-1",
                        "owner_module": "app/services/evidence_new.py",
                        "expires_on": "2026-05-01",
                    }
                ],
            }
        },
    }

    issues = validate_policy_payload(payload, today=date(2026, 5, 10))

    assert (
        "known_hotspots.app/services/evidence.py.exceptions[0].expires_on",
        "is expired",
    ) in {(issue.field, issue.message) for issue in issues}


def test_analyzer_flags_obvious_implementation_growth_for_each_hotspot() -> None:
    cases = [
        ("app/db/models.py", ["class NewRuntimeRow(Base):", "    pass"], "orm_class"),
        (
            "app/services/evidence.py",
            ["def _assemble_payload():", "    return {}"],
            "private_helper",
        ),
        ("app/cli.py", ["def run_new_command():", "    print('x')"], "command_implementation"),
        (
            "app/services/agent_task_actions.py",
            ["def execute_new_action():", "    return None"],
            "executor_implementation",
        ),
        (
            "app/services/agent_task_context.py",
            ["def _build_new_context(session, task, payload, *, action):", "    return {}"],
            "context_builder_implementation",
        ),
        ("app/services/search.py", ["def _rank_new():", "    return 1"], "query_feature_helper"),
        (
            "app/services/claim_support_policy_impacts.py",
            ["def _build_replay_alert_worklist():", "    return []"],
            "alert_projection_or_escalation_logic",
        ),
        (
            "app/services/evaluations.py",
            ["def load_evaluation_fixtures(corpus_path=None):", "    return []"],
            "fixture_corpus_logic",
        ),
        (
            "app/services/evidence_provenance_exports.py",
            ["def _build_agent_task_provenance_export(session, task_id):", "    return {}"],
            "provenance_graph_logic",
        ),
        (
            "tests/unit/test_cli.py",
            ["def test_new_command_group():", "    assert True"],
            "broad_new_test_group",
        ),
    ]
    for path, added_lines, category in cases:
        report = build_hotspot_prevention_report(
            _diff_for(path, added_lines),
            policy=load_hotspot_policy(),
            project_root=Path.cwd(),
        )

        assert report["summary"]["blocked_count"] == 1
        assert report["findings"][0]["relative_path"] == path
        assert report["findings"][0]["category"] == category
        assert report["findings"][0]["preferred_owner_modules"]


def test_context_hotspot_blocks_private_helper_growth() -> None:
    report = build_hotspot_prevention_report(
        _diff_for(
            "app/services/agent_task_context.py",
            ["def _resolve_new_context_dependency():", "    return {}"],
        ),
        policy=load_hotspot_policy(),
        project_root=Path.cwd(),
    )

    assert report["summary"]["blocked_count"] == 1
    assert report["findings"][0]["category"] == "context_family_helper"


def test_search_hotspot_blocks_persistence_and_operator_trace_growth() -> None:
    persistence_report = build_hotspot_prevention_report(
        _diff_for(
            "app/services/search.py",
            ["def _persist_more_search_rows(session):", "    return None"],
        ),
        policy=load_hotspot_policy(),
        project_root=Path.cwd(),
    )
    operator_trace_report = build_hotspot_prevention_report(
        _diff_for(
            "app/services/search.py",
            ["def _build_operator_trace_payload():", "    return {'selected_evidence': []}"],
        ),
        policy=load_hotspot_policy(),
        project_root=Path.cwd(),
    )

    assert persistence_report["summary"]["blocked_count"] == 1
    assert persistence_report["findings"][0]["category"] == "persistence_logic"
    assert operator_trace_report["summary"]["blocked_count"] >= 1
    assert "operator_trace_payload_builder" in {
        finding["category"] for finding in operator_trace_report["findings"]
    }
    assert "query_feature_helper" not in {
        finding["category"] for finding in operator_trace_report["findings"]
    }


def test_search_hotspot_blocks_orchestration_candidate_loading_and_detail_growth() -> None:
    orchestration_report = build_hotspot_prevention_report(
        _diff_for(
            "app/services/search.py",
            ["def _run_execution_stage():", "    return None"],
        ),
        policy=load_hotspot_policy(),
        project_root=Path.cwd(),
    )
    candidate_report = build_hotspot_prevention_report(
        _diff_for(
            "app/services/search.py",
            ["def _load_candidate_items():", "    return []"],
        ),
        policy=load_hotspot_policy(),
        project_root=Path.cwd(),
    )
    detail_report = build_hotspot_prevention_report(
        _diff_for(
            "app/services/search.py",
            ["def _build_search_execution_details():", "    return {}"],
        ),
        policy=load_hotspot_policy(),
        project_root=Path.cwd(),
    )

    assert orchestration_report["summary"]["blocked_count"] == 1
    assert orchestration_report["findings"][0]["category"] == "execution_orchestration"
    assert candidate_report["summary"]["blocked_count"] == 1
    assert candidate_report["findings"][0]["category"] == "candidate_loading"
    assert detail_report["summary"]["blocked_count"] == 1
    assert detail_report["findings"][0]["category"] == "search_detail_payload_builder"


def test_claim_support_hotspot_blocks_views_replay_and_closure_growth() -> None:
    views_report = build_hotspot_prevention_report(
        _diff_for(
            "app/services/claim_support_policy_impacts.py",
            ["def _build_replay_alert_worklist():", "    return []"],
        ),
        policy=load_hotspot_policy(),
        project_root=Path.cwd(),
    )
    replay_report = build_hotspot_prevention_report(
        _diff_for(
            "app/services/claim_support_policy_impacts.py",
            ["def _queue_more_replay_tasks():", "    return []"],
        ),
        policy=load_hotspot_policy(),
        project_root=Path.cwd(),
    )
    closure_report = build_hotspot_prevention_report(
        _diff_for(
            "app/services/claim_support_policy_impacts.py",
            ["def _replay_closure_receipt_payload():", "    return {}"],
        ),
        policy=load_hotspot_policy(),
        project_root=Path.cwd(),
    )

    assert views_report["summary"]["blocked_count"] == 1
    assert (
        views_report["findings"][0]["category"]
        == "alert_projection_or_escalation_logic"
    )
    assert replay_report["summary"]["blocked_count"] == 1
    assert replay_report["findings"][0]["category"] == "replay_lifecycle_logic"
    assert closure_report["summary"]["blocked_count"] == 1
    assert closure_report["findings"][0]["category"] == "replay_closure_receipt_logic"


def test_evaluations_hotspot_blocks_fixture_scoring_structural_and_latest_read_growth() -> None:
    fixture_report = build_hotspot_prevention_report(
        _diff_for(
            "app/services/evaluations.py",
            ["def ensure_auto_evaluation_fixture(session, document, run):", "    return None"],
        ),
        policy=load_hotspot_policy(),
        project_root=Path.cwd(),
    )
    scoring_report = build_hotspot_prevention_report(
        _diff_for(
            "app/services/evaluations.py",
            ["def _evaluate_answer_case(question, answer):", "    return {}"],
        ),
        policy=load_hotspot_policy(),
        project_root=Path.cwd(),
    )
    structural_report = build_hotspot_prevention_report(
        _diff_for(
            "app/services/evaluations.py",
            ["def _summarize_structural_checks(tables, figures, thresholds):", "    return {}"],
        ),
        policy=load_hotspot_policy(),
        project_root=Path.cwd(),
    )
    latest_read_report = build_hotspot_prevention_report(
        _diff_for(
            "app/services/evaluations.py",
            ["def get_latest_document_evaluation(session, document):", "    return None"],
        ),
        policy=load_hotspot_policy(),
        project_root=Path.cwd(),
    )

    assert fixture_report["summary"]["blocked_count"] == 1
    assert fixture_report["findings"][0]["category"] == "fixture_corpus_logic"
    assert scoring_report["summary"]["blocked_count"] == 1
    assert scoring_report["findings"][0]["category"] == "scoring_logic"
    assert structural_report["summary"]["blocked_count"] == 1
    assert structural_report["findings"][0]["category"] == "structural_check_logic"
    assert latest_read_report["summary"]["blocked_count"] == 1
    assert latest_read_report["findings"][0]["category"] == "latest_read_logic"


def test_provenance_export_hotspot_blocks_graph_lineage_lifecycle_and_governance_growth() -> None:
    graph_report = build_hotspot_prevention_report(
        _diff_for(
            "app/services/evidence_provenance_exports.py",
            ["def _build_agent_task_provenance_export(session, task_id):", "    return {}"],
        ),
        policy=load_hotspot_policy(),
        project_root=Path.cwd(),
    )
    lineage_report = build_hotspot_prevention_report(
        _diff_for(
            "app/services/evidence_provenance_exports.py",
            ["feedback = report_trace.get('claim_retrieval_feedback')"],
        ),
        policy=load_hotspot_policy(),
        project_root=Path.cwd(),
    )
    lifecycle_report = build_hotspot_prevention_report(
        _diff_for(
            "app/services/evidence_provenance_exports.py",
            ["def persist_agent_task_provenance_export(session, task_id):", "    return None"],
        ),
        policy=load_hotspot_policy(),
        project_root=Path.cwd(),
    )
    governance_report = build_hotspot_prevention_report(
        _diff_for(
            "app/services/evidence_provenance_exports.py",
            ["change_impact = technical_report_change_impact_for_governance(session, task_id)"],
        ),
        policy=load_hotspot_policy(),
        project_root=Path.cwd(),
    )

    assert graph_report["summary"]["blocked_count"] == 1
    assert graph_report["findings"][0]["category"] == "provenance_graph_logic"
    assert lineage_report["summary"]["blocked_count"] == 1
    assert lineage_report["findings"][0]["category"] == "report_trace_lineage_logic"
    assert lifecycle_report["summary"]["blocked_count"] == 1
    assert lifecycle_report["findings"][0]["category"] == "export_lifecycle_logic"
    assert governance_report["summary"]["blocked_count"] == 1
    assert governance_report["findings"][0]["category"] == "governance_change_impact_logic"


def test_analyzer_allows_import_forwarding_and_deletion_only_reductions() -> None:
    import_report = build_hotspot_prevention_report(
        _diff_for(
            "app/services/evidence.py",
            ["from app.services.evidence_new import build_new_payload"],
        ),
        policy=load_hotspot_policy(),
        project_root=Path.cwd(),
    )
    deletion_report = build_hotspot_prevention_report(
        _diff_for(
            "app/services/evidence.py",
            [],
            deleted_lines=["def _old_helper():", "    return {}"],
        ),
        policy=load_hotspot_policy(),
        project_root=Path.cwd(),
    )

    assert import_report["summary"]["blocked_count"] == 0
    assert import_report["findings"][0]["category"] == "import_forwarder"
    assert deletion_report["summary"]["blocked_count"] == 0
    assert deletion_report["findings"][0]["category"] == "deletion"


def test_analyzer_allows_agent_task_registry_composition() -> None:
    action_report = build_hotspot_prevention_report(
        _diff_for(
            "app/services/agent_task_actions.py",
            [
                "_ACTION_REGISTRY = compose_action_registries(",
                "    _EVALUATION_ACTION_REGISTRY,",
                "    _SEMANTIC_ANALYSIS_ACTION_REGISTRY,",
                "    _SEMANTIC_GOVERNANCE_ACTION_REGISTRY,",
                ")",
            ],
        ),
        policy=load_hotspot_policy(),
        project_root=Path.cwd(),
    )
    context_report = build_hotspot_prevention_report(
        _diff_for(
            "app/services/agent_task_context.py",
            [
                "_CONTEXT_BUILDERS = compose_context_builder_registries(",
                "    build_core_context_builders(globals()),",
                "    build_semantic_context_builders(globals()),",
                "    build_semantic_governance_context_builders(globals()),",
                ")",
            ],
        ),
        policy=load_hotspot_policy(),
        project_root=Path.cwd(),
    )

    assert action_report["summary"]["blocked_count"] == 0
    assert action_report["findings"][0]["category"] == "registry_composition"
    assert context_report["summary"]["blocked_count"] == 0
    assert context_report["findings"][0]["category"] == "registry_composition"

def test_analyzer_allows_parenthesized_alias_forwarding_hunks() -> None:
    report = build_hotspot_prevention_report(
        _diff_for(
            "app/services/evidence.py",
            [
                "_claim_derivation_payload = (",
                "    report_exports.claim_derivation_payload",
                ")",
                "attach_artifact_to_evidence_export = (",
                "    report_exports.attach_artifact_to_evidence_export",
                ")",
            ],
        ),
        policy=load_hotspot_policy(),
        project_root=Path.cwd(),
    )

    assert report["summary"]["blocked_count"] == 0
    assert report["findings"][0]["category"] == "import_forwarder"


def test_report_includes_numstat_line_counts() -> None:
    numstat = "2\t1\tapp/services/evidence.py\n"

    report = build_hotspot_prevention_report(
        _diff_for(
            "app/services/evidence.py",
            ["def _assemble_payload():", "    return {}"],
            deleted_lines=["def _old_helper():"],
        ),
        numstat_text=numstat,
        policy=load_hotspot_policy(),
        project_root=Path.cwd(),
    )

    assert parse_numstat(numstat)["app/services/evidence.py"].added_line_count == 2
    assert report["summary"]["added_line_count"] == 2
    assert report["summary"]["deleted_line_count"] == 1
    assert report["changed_files"] == [
        {
            "relative_path": "app/services/evidence.py",
            "added_line_count": 2,
            "deleted_line_count": 1,
            "source": "numstat",
            "known_hotspot": True,
        }
    ]
    assert report["findings"][0]["added_line_count"] == 2
    assert report["findings"][0]["deleted_line_count"] == 1


def test_cli_forwarding_wrapper_is_allowed() -> None:
    report = build_hotspot_prevention_report(
        _diff_for(
            "app/cli.py",
            [
                "def run_new_command():",
                "    return run_new_command_impl()",
            ],
        ),
        policy=load_hotspot_policy(),
        project_root=Path.cwd(),
    )

    assert report["summary"]["blocked_count"] == 0
    assert report["findings"][0]["category"] == "explicit_forwarding_function"


def test_search_forwarding_wrapper_with_execution_type_is_allowed() -> None:
    report = build_hotspot_prevention_report(
        _diff_for(
            "app/services/search.py",
            [
                "def execute_search(session, request, embedding_provider=None):",
                "    return _search_execution_orchestration.execute_search(",
                "        session=session,",
                "        request=request,",
                "        embedding_provider=embedding_provider,",
                "        execution_type=SearchExecution,",
                "    )",
            ],
        ),
        policy=load_hotspot_policy(),
        project_root=Path.cwd(),
    )

    assert report["summary"]["blocked_count"] == 0
    assert report["findings"][0]["category"] == "explicit_forwarding_function"


def test_claim_support_forwarding_wrapper_is_allowed() -> None:
    report = build_hotspot_prevention_report(
        _diff_for(
            "app/services/claim_support_policy_impacts.py",
            [
                "def claim_support_policy_change_impact_alerts(",
                "    session, *, stale_after_hours=24, limit=50",
                "):",
                "    return _impact_views.claim_support_policy_change_impact_alerts(",
                "        session,",
                "        stale_after_hours=stale_after_hours,",
                "        limit=limit,",
                "    )",
            ],
        ),
        policy=load_hotspot_policy(),
        project_root=Path.cwd(),
    )

    assert report["summary"]["blocked_count"] == 0
    assert report["findings"][0]["category"] == "explicit_forwarding_function"


def test_evaluations_forwarding_wrapper_is_allowed() -> None:
    report = build_hotspot_prevention_report(
        _diff_for(
            "app/services/evaluations.py",
            [
                "def get_latest_evaluation_summary(session, run_id):",
                "    return _evaluation_reads.get_latest_evaluation_summary(",
                "        session,",
                "        run_id,",
                "    )",
            ],
        ),
        policy=load_hotspot_policy(),
        project_root=Path.cwd(),
    )

    assert report["summary"]["blocked_count"] == 0
    assert report["findings"][0]["category"] == "explicit_forwarding_function"


def test_provenance_export_forwarding_wrapper_is_allowed() -> None:
    report = build_hotspot_prevention_report(
        _diff_for(
            "app/services/evidence_provenance_exports.py",
            [
                "def get_agent_task_provenance_export(session, task_id, *, storage_service=None):",
                "    return _lifecycle.get_agent_task_provenance_export(",
                "        session,",
                "        task_id,",
                "        storage_service=storage_service,",
                "    )",
            ],
        ),
        policy=load_hotspot_policy(),
        project_root=Path.cwd(),
    )

    assert report["summary"]["blocked_count"] == 0
    assert report["findings"][0]["category"] == "explicit_forwarding_function"


def test_provenance_export_multiline_import_reexport_is_allowed() -> None:
    report = build_hotspot_prevention_report(
        _diff_for(
            "app/services/evidence_provenance_exports.py",
            [
                "from app.services.evidence_provenance_export_lifecycle import (",
                "    existing_prov_export_artifact as _existing_prov_export_artifact,",
                "    get_agent_task_provenance_export,",
                "    persist_agent_task_provenance_export,",
            ],
        ),
        policy=load_hotspot_policy(),
        project_root=Path.cwd(),
    )

    assert report["summary"]["blocked_count"] == 0
    assert report["findings"][0]["category"] == "import_forwarder"


def test_cli_forwarding_wrapper_cluster_with_keyword_dependencies_is_allowed() -> None:
    report = build_hotspot_prevention_report(
        _diff_for(
            "app/cli.py",
            [
                "def run_ingest_file() -> None:",
                "    return ingest_commands.run_ingest_file(",
                "        ingest_local_file_func=ingest_local_file,",
                "        session_factory_func=get_session_factory,",
                "        storage_service_factory=StorageService,",
                "    )",
                "",
                "def run_ingest_dir() -> None:",
                "    return ingest_commands.run_ingest_dir(",
                "        queue_local_ingest_directory_func=queue_local_ingest_directory,",
                "        session_factory_func=get_session_factory,",
                "        storage_service_factory=StorageService,",
                "    )",
            ],
        ),
        policy=load_hotspot_policy(),
        project_root=Path.cwd(),
    )

    assert report["summary"]["blocked_count"] == 0
    assert {finding["category"] for finding in report["findings"]} == {
        "explicit_forwarding_function"
    }


def test_cli_replaced_command_body_with_keyword_forwarding_is_allowed() -> None:
    report = build_hotspot_prevention_report(
        _diff_for(
            "app/cli.py",
            [
                "    return ingest_commands.run_ingest_file(",
                "        ingest_local_file_func=ingest_local_file,",
                "        session_factory_func=get_session_factory,",
                "        storage_service_factory=StorageService,",
                "    )",
                "    return ingest_commands.run_ingest_dir(",
                "        queue_local_ingest_directory_func=queue_local_ingest_directory,",
                "        session_factory_func=get_session_factory,",
                "        storage_service_factory=StorageService,",
                "    )",
            ],
            deleted_lines=[
                "    parser = argparse.ArgumentParser(description='Queue PDFs')",
                "    parser.parse_args()",
            ],
        ),
        policy=load_hotspot_policy(),
        project_root=Path.cwd(),
    )

    assert report["summary"]["blocked_count"] == 0
    assert report["findings"][0]["category"] == "explicit_forwarding_function"


def test_policy_exception_requires_ownership_and_allows_marked_growth() -> None:
    policy = _policy_for(
        "app/services/evidence.py",
        exceptions=[
            {
                "exception_id": "HPG-TEST-1",
                "milestone_id": "residual-weakness-milestone-1",
                "owner_module": "app/services/evidence_new.py",
                "follow_up_condition": "remove after the facade split lands",
            }
        ],
    )
    report = build_hotspot_prevention_report(
        _diff_for(
            "app/services/evidence.py",
            [
                "# hotspot-exception: HPG-TEST-1",
                "def _assemble_payload():",
                "    return {}",
            ],
        ),
        policy=policy,
        project_root=Path.cwd(),
    )

    assert report["summary"]["blocked_count"] == 0
    assert report["summary"]["exception_count"] == 1
    assert report["findings"][0]["status"] == "allowed_exception"


def test_json_report_shape_and_cli_strict_exit(tmp_path: Path, capsys) -> None:
    policy_path = tmp_path / "policy.yaml"
    policy_path.write_text(
        yaml.safe_dump(
            {
                "schema_name": POLICY_SCHEMA_NAME,
                "schema_version": "1.0",
                "known_hotspots": {
                    "app/services/evidence.py": {
                        "target_role": "compatibility facade",
                        "preferred_owner_modules": ["app/services/evidence_new.py"],
                        "block_new": ["private_helper"],
                        "allow": ["import_forwarder", "deletion"],
                    }
                },
            },
            sort_keys=False,
        )
    )
    diff_path = tmp_path / "blocked.diff"
    diff_path.write_text(
        _diff_for(
            "app/services/evidence.py",
            ["def _assemble_payload():", "    return {}"],
        )
    )

    exit_code = run(
        [
            "--policy-path",
            str(policy_path),
            "--diff-file",
            str(diff_path),
            "--strict",
            "--format",
            "json",
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 1
    assert payload["schema_name"] == REPORT_SCHEMA_NAME
    assert payload["summary"]["blocked_count"] == 1
    assert payload["summary"]["added_line_count"] == 2
    assert payload["findings"][0]["policy_rule"] == "block_new.private_helper"


def test_git_diff_collectors_wire_base_and_staged(monkeypatch, tmp_path: Path) -> None:
    commands: list[list[str]] = []

    class Completed:
        returncode = 0
        stdout = ""
        stderr = ""

    def fake_run(command, *, cwd, capture_output, text):
        commands.append(command)
        assert cwd == tmp_path
        assert capture_output is True
        assert text is True
        return Completed()

    monkeypatch.setattr("app.hotspot_prevention_diff.subprocess.run", fake_run)

    collect_git_diff(project_root=tmp_path, base="HEAD~1")
    collect_git_numstat(project_root=tmp_path, staged=True)

    assert commands == [
        ["git", "diff", "--no-ext-diff", "--unified=3", "HEAD~1"],
        ["git", "diff", "--no-ext-diff", "--numstat", "--cached"],
    ]


def test_git_diff_collectors_reject_base_with_staged(tmp_path: Path) -> None:
    try:
        collect_git_diff(project_root=tmp_path, base="HEAD", staged=True)
    except ValueError as exc:
        assert "--base and --staged cannot be used together" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_pyproject_exposes_hotspot_prevention_entrypoint() -> None:
    scripts = tomllib.loads(Path("pyproject.toml").read_text())["project"]["scripts"]

    assert scripts["docling-system-hotspot-prevention-check"] == "app.hotspot_prevention:run"
