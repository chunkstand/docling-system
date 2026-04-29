from __future__ import annotations

from datetime import datetime

from app.db.models import AgentTask, AgentTaskAttempt


def duration_ms(started_at: datetime | None, completed_at: datetime | None) -> float | None:
    if started_at is None or completed_at is None:
        return None
    return max(0.0, (completed_at - started_at).total_seconds() * 1000.0)


def evaluation_query_count_from_evaluation(evaluation: dict) -> int:
    return int(evaluation.get("total_shared_query_count") or 0)


def replay_query_count_from_evaluation(evaluation: dict) -> int:
    return sum(
        int(source.get("baseline_query_count") or 0) + int(source.get("candidate_query_count") or 0)
        for source in (evaluation.get("sources") or [])
        if isinstance(source, dict)
    )


def derive_attempt_cost(task: AgentTask, result: dict) -> dict:
    payload = (result or {}).get("payload") or result or {}
    evaluation = payload.get("evaluation") or {}
    verification = payload.get("verification") or {}
    replay_run = payload.get("replay_run") or {}
    replay = payload.get("replay") or {}

    replay_query_count = 0
    evaluation_query_count = 0
    embedding_count = 0
    call_count = 0

    if task.task_type == "run_search_replay_suite":
        replay_query_count = int(replay_run.get("query_count") or 0)
        call_count = 1
    elif task.task_type == "evaluate_search_harness":
        replay_query_count = replay_query_count_from_evaluation(evaluation)
        evaluation_query_count = evaluation_query_count_from_evaluation(evaluation)
        call_count = max(len(evaluation.get("sources") or []), 1)
    elif task.task_type == "triage_replay_regression":
        replay_query_count = replay_query_count_from_evaluation(evaluation)
        evaluation_query_count = evaluation_query_count_from_evaluation(evaluation)
        call_count = max(len(evaluation.get("sources") or []), 1)
    elif task.task_type == "triage_semantic_pass":
        metrics = verification.get("metrics") or {}
        evaluation_query_count = int(metrics.get("issue_count") or 0)
        call_count = 1 if verification else 0
    elif task.task_type == "export_semantic_supervision_corpus":
        corpus = payload.get("corpus") or {}
        evaluation_query_count = int(corpus.get("row_count") or 0)
        call_count = 1
    elif task.task_type == "evaluate_semantic_candidate_extractor":
        summary = payload.get("summary") or {}
        evaluation_query_count = int(summary.get("expected_concept_count") or 0)
        call_count = max(int(summary.get("document_count") or 0), 1)
    elif task.task_type == "build_shadow_semantic_graph":
        graph_payload = payload.get("shadow_graph") or {}
        evaluation_query_count = int(graph_payload.get("edge_count") or 0)
        call_count = max(int(graph_payload.get("document_count") or 0), 1)
    elif task.task_type == "evaluate_semantic_relation_extractor":
        summary = payload.get("summary") or {}
        evaluation_query_count = int(summary.get("expected_edge_count") or 0)
        call_count = max(int(summary.get("document_count") or 0), 1)
    elif task.task_type == "triage_semantic_candidate_disagreements":
        report = payload.get("disagreement_report") or {}
        metrics = verification.get("metrics") or {}
        evaluation_query_count = int(metrics.get("issue_count") or report.get("issue_count") or 0)
        call_count = 1 if report or verification else 0
    elif task.task_type == "triage_semantic_graph_disagreements":
        report = payload.get("disagreement_report") or {}
        metrics = verification.get("metrics") or {}
        evaluation_query_count = int(metrics.get("issue_count") or report.get("issue_count") or 0)
        call_count = 1 if report or verification else 0
    elif task.task_type == "prepare_semantic_generation_brief":
        brief = payload.get("brief") or {}
        evaluation_query_count = int(len(brief.get("claim_candidates") or []))
        call_count = 1
    elif task.task_type == "plan_technical_report":
        plan = payload.get("plan") or {}
        evaluation_query_count = int(len(plan.get("expected_claims") or []))
        call_count = 1
    elif task.task_type == "build_report_evidence_cards":
        evidence_bundle = payload.get("evidence_bundle") or {}
        evaluation_query_count = int(len(evidence_bundle.get("evidence_cards") or []))
        call_count = 1
    elif task.task_type == "prepare_report_agent_harness":
        harness = payload.get("harness") or {}
        evaluation_query_count = int(len(harness.get("claim_contract") or []))
        call_count = 1
    elif task.task_type == "evaluate_document_generation_context_pack":
        evaluation = payload.get("evaluation") or {}
        summary = evaluation.get("summary") or {}
        evaluation_query_count = int(summary.get("check_count") or 0)
        call_count = 1 if evaluation else 0
    elif task.task_type == "initialize_workspace_ontology":
        snapshot = payload.get("snapshot") or {}
        evaluation_query_count = int(snapshot.get("concept_count") or 0)
        call_count = 1
    elif task.task_type == "get_active_ontology_snapshot":
        snapshot = payload.get("snapshot") or {}
        evaluation_query_count = int(snapshot.get("concept_count") or 0)
        call_count = 1 if snapshot else 0
    elif task.task_type == "draft_ontology_extension":
        draft = payload.get("draft") or {}
        evaluation_query_count = int(len(draft.get("operations") or []))
        call_count = 1
    elif task.task_type == "draft_graph_promotions":
        draft = payload.get("draft") or {}
        evaluation_query_count = int(len(draft.get("promoted_edges") or []))
        call_count = 1
    elif task.task_type == "verify_draft_ontology_extension":
        verification = payload.get("verification") or {}
        metrics = verification.get("metrics") or {}
        evaluation_query_count = int(metrics.get("document_count") or 0)
        call_count = max(int(metrics.get("document_count") or 0), 1) if metrics else 0
    elif task.task_type == "verify_draft_graph_promotions":
        metrics = verification.get("metrics") or {}
        evaluation_query_count = int(metrics.get("promoted_edge_count") or 0)
        call_count = max(int(metrics.get("promoted_edge_count") or 0), 1) if metrics else 0
    elif task.task_type == "apply_ontology_extension":
        apply_payload = payload
        evaluation_query_count = int(len(apply_payload.get("applied_operations") or []))
        call_count = 1
    elif task.task_type == "apply_graph_promotions":
        apply_payload = payload
        evaluation_query_count = int(apply_payload.get("applied_edge_count") or 0)
        call_count = 1
    elif task.task_type == "build_document_fact_graph":
        evaluation_query_count = int(payload.get("fact_count") or 0)
        call_count = 1
    elif task.task_type == "draft_semantic_grounded_document":
        draft = payload.get("draft") or {}
        evaluation_query_count = int(len(draft.get("claims") or []))
        call_count = 1
    elif task.task_type == "draft_technical_report":
        draft = payload.get("draft") or {}
        evaluation_query_count = int(len(draft.get("claims") or []))
        call_count = 1
    elif task.task_type in {
        "verify_search_harness_evaluation",
        "verify_draft_harness_config",
        "verify_draft_semantic_registry_update",
        "verify_semantic_grounded_document",
        "verify_technical_report",
    }:
        metrics = verification.get("metrics") or {}
        if task.task_type == "verify_draft_semantic_registry_update":
            evaluation_query_count = int(metrics.get("document_count") or 0)
            call_count = max(int(metrics.get("document_count") or 0), 1) if metrics else 0
        elif task.task_type == "verify_semantic_grounded_document":
            evaluation_query_count = int(metrics.get("claim_count") or 0)
            call_count = 1 if metrics else 0
        elif task.task_type == "verify_technical_report":
            evaluation_query_count = int(metrics.get("claim_count") or 0)
            call_count = 1 if metrics else 0
        else:
            evaluation_query_count = int(metrics.get("total_shared_query_count") or 0)
            call_count = max(int(metrics.get("source_count") or 0), 1) if metrics else 0
    elif task.task_type == "replay_search_request":
        replay_query_count = 1 if replay else 0
        call_count = 1 if replay else 0

    return {
        "provider": None,
        "model": task.model,
        "billing_status": "model_pricing_not_integrated",
        "call_count": call_count,
        "input_tokens": None,
        "output_tokens": None,
        "embedding_count": embedding_count,
        "replay_query_count": replay_query_count,
        "evaluation_query_count": evaluation_query_count,
        "estimated_usd": 0.0,
    }


def derive_attempt_performance(
    task: AgentTask,
    attempt: AgentTaskAttempt,
    completed_at: datetime,
) -> dict:
    execution_latency_ms = duration_ms(attempt.started_at, completed_at)
    verification_latency_ms = (
        execution_latency_ms
        if task.task_type.startswith("verify_")
        or task.task_type
        in {
            "triage_replay_regression",
            "triage_semantic_pass",
            "triage_semantic_candidate_disagreements",
        }
        else None
    )
    return {
        "queue_latency_ms": duration_ms(task.created_at, attempt.started_at),
        "execution_latency_ms": execution_latency_ms,
        "approval_latency_ms": duration_ms(task.created_at, task.approved_at),
        "verification_latency_ms": verification_latency_ms,
        "end_to_end_latency_ms": duration_ms(task.created_at, completed_at),
    }
