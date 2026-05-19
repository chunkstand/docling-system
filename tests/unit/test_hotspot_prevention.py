from __future__ import annotations

from pathlib import Path

from app.hotspot_prevention import build_hotspot_prevention_report, load_hotspot_policy
from tests.unit.hotspot_prevention_test_support import _diff_for


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
            "tests/integration/test_claim_support_judge_evaluation_roundtrip.py",
            ["def test_new_replay_alert_promotion_branch():", "    assert True"],
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
