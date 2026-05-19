from __future__ import annotations

import json
import tomllib
from datetime import date
from pathlib import Path

import yaml

from app.hotspot_prevention import (
    POLICY_SCHEMA_NAME,
    REPORT_SCHEMA_NAME,
    build_hotspot_prevention_report,
    collect_git_diff,
    collect_git_numstat,
    load_hotspot_policy,
    parse_numstat,
    run,
    validate_policy_payload,
)
from tests.unit.hotspot_prevention_test_support import _diff_for, _policy_for


def test_current_hotspot_policy_loads_expected_surfaces() -> None:
    policy = load_hotspot_policy()

    assert sorted(policy.known_hotspots) == [
        "app/cli.py",
        "app/db/models.py",
        "app/schemas/agent_tasks.py",
        "app/services/agent_actions/search_harness.py",
        "app/services/agent_actions/semantic_governance_actions.py",
        "app/services/agent_task_actions.py",
        "app/services/agent_task_context.py",
        "app/services/agent_task_context_search_harness.py",
        "app/services/agent_task_context_semantic_governance.py",
        "app/services/agent_tasks.py",
        "app/services/claim_support_evaluations.py",
        "app/services/claim_support_policy_governance.py",
        "app/services/claim_support_policy_impact_replay.py",
        "app/services/claim_support_policy_impact_views.py",
        "app/services/claim_support_policy_impacts.py",
        "app/services/claim_support_replay_alert_fixture_corpus.py",
        "app/services/claim_support_replay_alert_promotions.py",
        "app/services/evaluations.py",
        "app/services/evidence.py",
        "app/services/evidence_provenance_exports.py",
        "app/services/search.py",
        "app/services/semantics.py",
        "tests/db_model_contract.py",
        "tests/integration/retrieval_learning_ledger_support.py",
        "tests/integration/technical_report_harness_support.py",
        "tests/integration/test_retrieval_learning_ledger.py",
        "tests/integration/test_technical_report_harness_roundtrip.py",
        "tests/unit/test_agent_task_context.py",
        "tests/unit/test_agent_tasks_api.py",
        "tests/unit/test_cli.py",
        "tests/unit/test_evaluation_service.py",
        "tests/unit/test_search_service.py",
    ]
    for rule in policy.known_hotspots.values():
        assert rule.preferred_owner_modules
        assert rule.block_new
    assert policy.known_hotspots["app/db/models.py"].routing is not None
    assert (
        policy.known_hotspots["app/db/models.py"].routing.status
        == "compatibility_facade_trap"
    )
    assert policy.known_hotspots["app/cli.py"].routing is not None
    assert (
        policy.known_hotspots["app/cli.py"].routing.status == "deferred_reduced_facade"
    )
    assert policy.known_hotspots["tests/unit/test_cli.py"].routing is not None
    assert policy.known_hotspots["app/services/search.py"].routing is not None


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


def test_policy_validation_rejects_trap_routing_without_successors() -> None:
    payload = {
        "schema_name": POLICY_SCHEMA_NAME,
        "schema_version": "1.0",
        "known_hotspots": {
            "app/services/evidence.py": {
                "target_role": "compatibility facade",
                "preferred_owner_modules": ["app/services/evidence_*.py"],
                "routing": {
                    "status": "compatibility_facade_trap",
                    "reason": "Facade is already reduced.",
                },
                "block_new": ["private_helper"],
                "allow": ["import_forwarder"],
            }
        },
    }

    issues = validate_policy_payload(payload)

    assert {
        (
            "known_hotspots.app/services/evidence.py.routing.route_to_case_ids",
            "must contain at least one routed case id",
        ),
        (
            "known_hotspots.app/services/evidence.py.routing.route_to_paths",
            "must contain at least one routed path",
        ),
        (
            "known_hotspots.app/services/evidence.py.routing.route_to_plan_paths",
            "must contain at least one routed plan path",
        ),
    } <= {(issue.field, issue.message) for issue in issues}


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
            "app/services/claim_support_policy_impact_views.py",
            ["def claim_support_policy_change_impact_worklist(session):", "    return {}"],
            "worklist_assembly_logic",
        ),
        (
            "app/services/claim_support_policy_impact_replay.py",
            [
                (
                    "def queue_claim_support_policy_change_impact_replay_tasks("
                    "session, change_impact_id):"
                ),
                "    return {}",
            ],
            "replay_queueing_logic",
        ),
        (
            "app/services/claim_support_replay_alert_promotions.py",
            ["def _candidate_from_derivation(item, derivation, draft_task):", "    return {}"],
            "fixture_candidate_derivation_logic",
        ),
        (
            "app/services/claim_support_evaluations.py",
            [
                "def ensure_claim_support_fixture_set("
                "session, *, fixture_set_name):",
                "    return None",
            ],
            "fixture_authoring_logic",
        ),
        (
            "app/services/claim_support_policy_governance.py",
            [
                (
                    "def build_claim_support_policy_change_impact_payload("
                    "session, *, task, activated_policy):"
                ),
                "    return {}",
            ],
            "change_impact_governance_logic",
        ),
        (
            "app/services/claim_support_replay_alert_fixture_corpus.py",
            ["def build_replay_alert_fixture_corpus(session):", "    return None"],
            "corpus_build_logic",
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
            "app/services/semantics.py",
            [
                "def _prepare_semantic_pass_row(session, document, run, registry):",
                "    return None",
            ],
            "semantic_pass_lifecycle_logic",
        ),
        (
            "app/schemas/agent_tasks.py",
            ["class NewTaskInput(BaseModel):"],
            "schema_definition",
        ),
        (
            "tests/unit/test_cli.py",
            ["def test_new_command_group():", "    assert True"],
            "broad_new_test_group",
        ),
        (
            "tests/db_model_contract.py",
            ["def _build_contract_group():", "    return []"],
            "broad_helper",
        ),
        (
            "tests/unit/test_agent_tasks_api.py",
            ["def test_new_route_family_case():", "    assert True"],
            "broad_new_test_group",
        ),
        (
            "tests/integration/test_technical_report_harness_roundtrip.py",
            ["def test_new_audit_branch():", "    assert True"],
            "broad_new_test_group",
        ),
        (
            "tests/integration/technical_report_harness_support.py",
            ["def _build_extra_support_fixture():", "    return {}"],
            "broad_helper",
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


def test_analyzer_allows_agent_task_schema_registry_composition() -> None:
    report = build_hotspot_prevention_report(
        _diff_for(
            "app/schemas/agent_tasks.py",
            [
                "_OWNER_MODULES = (",
                "    _agent_task_core,",
                "    _agent_task_claim_support,",
                ")",
                "__all__ = [",
                "    *_agent_task_core.__all__,",
                "    *_agent_task_claim_support.__all__,",
                "]",
            ],
        ),
        policy=load_hotspot_policy(),
        project_root=Path.cwd(),
    )

    assert report["summary"]["blocked_count"] == 0
    assert {finding["category"] for finding in report["findings"]} == {
        "compatibility_registry_declaration"
    }


def test_analyzer_allows_compact_agent_task_schema_facade_hunk() -> None:
    report = build_hotspot_prevention_report(
        _diff_for(
            "app/schemas/agent_tasks.py",
            [
                "from typing import Any as _Any",
                "_OWNER_MODULES: tuple[object, ...] = (",
                "    _agent_task_core,",
                "    _agent_task_claim_support,",
                ")",
                "_EXPORT_REGISTRY = {",
                "    name: module for module in _OWNER_MODULES "
                'for name in getattr(module, "__all__", ())',
                "}",
                "__all__ = sorted(_EXPORT_REGISTRY)",
                "def __getattr__(name: str) -> _Any:",
                "    module = _EXPORT_REGISTRY.get(name)",
                "    if module is None:",
                '        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")',
                "    value = getattr(module, name)",
                "    globals()[name] = value",
                "    return value",
                "def __dir__() -> list[str]:",
                "    return sorted(set(globals()) | set(__all__))",
            ],
        ),
        policy=load_hotspot_policy(),
        project_root=Path.cwd(),
    )

    assert report["summary"]["blocked_count"] == 0
    assert {finding["category"] for finding in report["findings"]} == {
        "compatibility_registry_declaration"
    }


def test_analyzer_allows_agent_task_schema_alias_forwarders() -> None:
    report = build_hotspot_prevention_report(
        _diff_for(
            "app/schemas/agent_tasks.py",
            [
                "import app.schemas.agent_task_core as _agent_task_core",
                "from app.schemas import agent_task_claim_support as _agent_task_claim_support",
                "AgentTaskCreateRequest = _agent_task_core.AgentTaskCreateRequest",
            ],
        ),
        policy=load_hotspot_policy(),
        project_root=Path.cwd(),
    )

    assert report["summary"]["blocked_count"] == 0
    assert {finding["category"] for finding in report["findings"]} == {"schema_alias_forwarder"}


def test_agent_task_schema_facade_blocks_broad_reexport_batches() -> None:
    report = build_hotspot_prevention_report(
        _diff_for(
            "app/schemas/agent_tasks.py",
            [
                "from app.schemas.agent_task_core import (",
                "    AgentTaskCreateRequest,",
                "    AgentTaskSummaryResponse,",
                ")",
            ],
        ),
        policy=load_hotspot_policy(),
        project_root=Path.cwd(),
    )

    assert report["summary"]["blocked_count"] == 4
    assert {finding["category"] for finding in report["findings"]} == {"broad_reexport_batch"}


def test_agent_task_schema_facade_blocks_new_export_sink_surfaces() -> None:
    report = build_hotspot_prevention_report(
        _diff_for(
            "app/schemas/agent_tasks.py",
            [
                "from app.schemas._agent_task_schema_exports import SCHEMA_EXPORTS",
                "def _load_schema_exports():",
                "    return SCHEMA_EXPORTS",
            ],
        ),
        policy=load_hotspot_policy(),
        project_root=Path.cwd(),
    )

    assert report["summary"]["blocked_count"] == 3
    assert {finding["category"] for finding in report["findings"]} == {"export_sink_surface"}


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
