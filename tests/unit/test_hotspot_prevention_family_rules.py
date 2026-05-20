from __future__ import annotations

from pathlib import Path

from app.hotspot_prevention import build_hotspot_prevention_report, load_hotspot_policy
from tests.unit.hotspot_prevention_test_support import _diff_for


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


def test_residual_test_hotspots_allow_smoke_compatibility_assertions() -> None:
    report = build_hotspot_prevention_report(
        _diff_for(
            "tests/integration/test_technical_report_harness_roundtrip.py",
            ["def test_roundtrip_smoke_contract():", "    assert True"],
        ),
        policy=load_hotspot_policy(),
        project_root=Path.cwd(),
    )

    assert report["summary"]["blocked_count"] == 0
    assert report["findings"][0]["category"] == "compatibility_assertion"


def test_support_hotspot_blocks_new_helper_sink_growth() -> None:
    report = build_hotspot_prevention_report(
        _diff_for(
            "tests/integration/retrieval_learning_ledger_support.py",
            ["def _build_unrelated_support_helper():", "    return {}"],
        ),
        policy=load_hotspot_policy(),
        project_root=Path.cwd(),
    )

    assert report["summary"]["blocked_count"] == 1
    assert report["findings"][0]["category"] == "broad_helper"


def test_classifier_dispatcher_hotspot_routes_entries_and_blocks_new_helpers() -> None:
    route_report = build_hotspot_prevention_report(
        _diff_for(
            "app/hotspot_prevention_classifier.py",
            ['"app/services/new_surface.py": _service_rules.classify_search_addition,'],
        ),
        policy=load_hotspot_policy(),
        project_root=Path.cwd(),
    )
    helper_report = build_hotspot_prevention_report(
        _diff_for(
            "app/hotspot_prevention_classifier.py",
            ["def _classify_new_surface():", "    return None"],
        ),
        policy=load_hotspot_policy(),
        project_root=Path.cwd(),
    )

    assert route_report["summary"]["blocked_count"] == 0
    assert route_report["findings"][0]["category"] == "registry_composition"
    assert helper_report["summary"]["blocked_count"] == 1
    assert helper_report["findings"][0]["category"] == "dispatcher_helper"


def test_classifier_support_hotspot_blocks_new_helper_growth() -> None:
    report = build_hotspot_prevention_report(
        _diff_for(
            "app/hotspot_prevention_classifier_support.py",
            ["def classify_unrelated_surface():", "    return None"],
        ),
        policy=load_hotspot_policy(),
        project_root=Path.cwd(),
    )

    assert report["summary"]["blocked_count"] == 1
    assert report["findings"][0]["category"] == "broad_helper"


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


def test_search_hotspot_blocks_harness_registry_retrieval_and_metadata_regrowth() -> None:
    harness_report = build_hotspot_prevention_report(
        _diff_for(
            "app/services/search.py",
            ["def build_search_harness_registry(overrides=None):", "    return {}"],
        ),
        policy=load_hotspot_policy(),
        project_root=Path.cwd(),
    )
    retrieval_report = build_hotspot_prevention_report(
        _diff_for(
            "app/services/search.py",
            ["def run_keyword_chunk_search(session, request):", "    return []"],
        ),
        policy=load_hotspot_policy(),
        project_root=Path.cwd(),
    )
    metadata_report = build_hotspot_prevention_report(
        _diff_for(
            "app/services/search.py",
            ["def run_prose_metadata_chunk_search(session, request):", "    return []"],
        ),
        policy=load_hotspot_policy(),
        project_root=Path.cwd(),
    )

    assert harness_report["summary"]["blocked_count"] == 1
    assert harness_report["findings"][0]["category"] == "harness_registry_logic"
    assert retrieval_report["summary"]["blocked_count"] == 1
    assert retrieval_report["findings"][0]["category"] == "retrieval_primitive_logic"
    assert metadata_report["summary"]["blocked_count"] == 1
    assert metadata_report["findings"][0]["category"] == "metadata_supplement_logic"


def test_semantics_hotspot_blocks_lifecycle_review_read_and_preview_growth() -> None:
    lifecycle_report = build_hotspot_prevention_report(
        _diff_for(
            "app/services/semantics.py",
            ["def execute_semantic_pass(session, document, run):", "    return None"],
        ),
        policy=load_hotspot_policy(),
        project_root=Path.cwd(),
    )
    review_report = build_hotspot_prevention_report(
        _diff_for(
            "app/services/semantics.py",
            [
                "def review_active_semantic_assertion(session, document_id, assertion_id):",
                "    return None",
            ],
        ),
        policy=load_hotspot_policy(),
        project_root=Path.cwd(),
    )
    read_report = build_hotspot_prevention_report(
        _diff_for(
            "app/services/semantics.py",
            ["def get_active_semantic_pass_detail(session, document_id):", "    return None"],
        ),
        policy=load_hotspot_policy(),
        project_root=Path.cwd(),
    )
    preview_report = build_hotspot_prevention_report(
        _diff_for(
            "app/services/semantics.py",
            [
                "introduced_expected_concepts = sorted(",
                "    candidate_concept_keys - current_concept_keys",
                ")",
            ],
        ),
        policy=load_hotspot_policy(),
        project_root=Path.cwd(),
    )

    assert lifecycle_report["summary"]["blocked_count"] == 1
    assert lifecycle_report["findings"][0]["category"] == "semantic_pass_lifecycle_logic"
    assert review_report["summary"]["blocked_count"] == 1
    assert review_report["findings"][0]["category"] == "projection_refresh_review_logic"
    assert read_report["summary"]["blocked_count"] == 1
    assert read_report["findings"][0]["category"] == "active_pass_read_logic"
    assert preview_report["summary"]["blocked_count"] == 1
    assert preview_report["findings"][0]["category"] == "registry_preview_expectation_logic"


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
    assert views_report["findings"][0]["category"] == "alert_projection_or_escalation_logic"
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
