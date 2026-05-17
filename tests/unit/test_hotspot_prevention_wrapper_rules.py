from __future__ import annotations

from pathlib import Path

from app.hotspot_prevention import build_hotspot_prevention_report, load_hotspot_policy
from tests.unit.hotspot_prevention_test_support import _diff_for


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


def test_semantics_forwarding_wrapper_is_allowed() -> None:
    report = build_hotspot_prevention_report(
        _diff_for(
            "app/services/semantics.py",
            [
                "def get_active_semantic_pass_detail(session, document_id):",
                "    return _semantic_pass_reads.get_active_semantic_pass_detail(",
                "        session,",
                "        document_id,",
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


def test_claim_support_compact_surface_reduction_is_allowed() -> None:
    report = build_hotspot_prevention_report(
        _diff_for(
            "app/services/claim_support_evaluations.py",
            [
                "def ensure_claim_support_fixture_set(session, *, fixture_set_name):",
                "    return import_module(",
                '        "app.services.claim_support_evaluation_fixtures"',
                "    ).ensure_claim_support_fixture_set(",
                "        session,",
                "        fixture_set_name=fixture_set_name,",
                "    )",
            ],
            deleted_lines=[
                "def _source_card(*, case_id, excerpt, concept_keys):",
                "    return {}",
                "def _draft_fixture(*, case_id, rendered_text, concept_keys):",
                "    return {}",
                "def _graph_fixture_case(case_id):",
                "    return {}",
                "def default_claim_support_evaluation_fixtures():",
                "    return []",
                "def _thresholds_payload(**kwargs):",
                "    return {}",
                "def _fixture_set_payload(**kwargs):",
                "    return {}",
                "def build_claim_support_calibration_policy_payload(**kwargs):",
                "    return {}",
                "def ensure_claim_support_calibration_policy(session, **kwargs):",
                "    return None",
                "def evaluate_claim_support_judge_fixture_set(**kwargs):",
                "    return {}",
                "def persist_claim_support_judge_evaluation(session, payload):",
                "    return None",
                "def mine_claim_support_failure_fixtures(session, *, limit=20):",
                "    return []",
                "def resolve_claim_support_calibration_policy(session):",
                "    return None",
                "def activate_claim_support_calibration_policy(session, *, policy_id):",
                "    return None",
            ]
            * 3,
        ),
        policy=load_hotspot_policy(),
        project_root=Path.cwd(),
    )

    assert report["summary"]["blocked_count"] == 0
    assert report["findings"][0]["category"] == "net_reduction_refactor"


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


def test_cli_direct_session_or_storage_wiring_is_blocked() -> None:
    report = build_hotspot_prevention_report(
        _diff_for(
            "app/cli.py",
            [
                "session_factory = get_session_factory()",
                "with session_factory() as session:",
                "storage_service = StorageService()",
            ],
        ),
        policy=load_hotspot_policy(),
        project_root=Path.cwd(),
    )

    assert report["summary"]["blocked_count"] == 3
    assert {finding["category"] for finding in report["findings"]} == {"session_or_storage_wiring"}


def test_cli_parser_body_and_json_render_scaffolding_is_blocked() -> None:
    report = build_hotspot_prevention_report(
        _diff_for(
            "app/cli.py",
            [
                "parser.add_argument('--limit', type=int, default=5)",
                "args = parser.parse_args()",
                "print(json.dumps({'limit': args.limit}))",
            ],
        ),
        policy=load_hotspot_policy(),
        project_root=Path.cwd(),
    )

    assert report["summary"]["blocked_count"] == 3
    assert {finding["category"] for finding in report["findings"]} == {
        "json_render_or_parser_body_scaffolding"
    }
