from __future__ import annotations

import uuid
from collections import Counter

from sqlalchemy.orm import Session

from app.core.files import source_filename_matches
from app.core.time import utcnow
from app.db.public.retrieval import SearchReplayQuery, SearchReplayRun
from app.schemas.search import SearchReplayRunDetailResponse, SearchReplayRunRequest, SearchRequest
from app.services import search_replay_cases as replay_cases
from app.services import search_replay_claim_feedback_cases as claim_feedback_cases
from app.services import search_replay_common as replay_common
from app.services import search_replay_rank_metrics as replay_rank_metrics
from app.services.search import execute_search as _execute_search
from app.services.search import get_search_harness
from app.services.search_history import build_search_replay_diff as _build_search_replay_diff
from app.services.search_history import get_search_request_detail as _get_search_request_detail
from app.services.search_replay_resolver import resolve_search_replays_service

ReplayCase = replay_common.ReplayCase
TECHNICAL_REPORT_CLAIM_FEEDBACK_SOURCE_TYPE = (
    replay_common.TECHNICAL_REPORT_CLAIM_FEEDBACK_SOURCE_TYPE
)


def _evaluate_case_passed(case: ReplayCase, execution) -> tuple[bool, dict]:
    if case.evaluation_query_id is not None:
        matching_rank = replay_rank_metrics.matching_rank(
            execution.results,
            case.expected_result_type,
            expected_source_filename=case.expected_source_filename,
        )
        top_result_source_filename = (
            execution.results[0].source_filename if execution.results else None
        )
        expected_source_hit_count = replay_rank_metrics.top_n_source_hit_count(
            execution.results,
            case.expected_source_filename,
            case.expected_top_n,
        )
        foreign_results_before_first_expected_hit = (
            replay_rank_metrics.foreign_results_before_first_expected_hit(
                execution.results,
                case.expected_result_type,
                expected_source_filename=case.expected_source_filename,
            )
        )
        passed = matching_rank is not None and matching_rank <= (case.expected_top_n or 0)
        if case.expected_top_result_source_filename is not None:
            passed = passed and source_filename_matches(
                top_result_source_filename,
                case.expected_top_result_source_filename,
            )
        if case.minimum_top_n_hits_from_expected_document is not None:
            passed = passed and (
                (expected_source_hit_count or 0) >= case.minimum_top_n_hits_from_expected_document
            )
        if case.maximum_foreign_results_before_first_expected_hit is not None:
            passed = passed and (
                foreign_results_before_first_expected_hit is not None
                and foreign_results_before_first_expected_hit
                <= case.maximum_foreign_results_before_first_expected_hit
            )
        return passed, {
            "matching_rank": matching_rank,
            "expected_source_filename": case.expected_source_filename,
            "expected_top_result_source_filename": case.expected_top_result_source_filename,
            "minimum_top_n_hits_from_expected_document": (
                case.minimum_top_n_hits_from_expected_document
            ),
            "maximum_foreign_results_before_first_expected_hit": (
                case.maximum_foreign_results_before_first_expected_hit
            ),
            "top_result_source_filename": top_result_source_filename,
            "expected_source_hit_count": expected_source_hit_count,
            "foreign_results_before_first_expected_hit": (
                foreign_results_before_first_expected_hit
            ),
        }

    if case.source_reason == TECHNICAL_REPORT_CLAIM_FEEDBACK_SOURCE_TYPE:
        metadata = case.source_metadata or {}
        learning_label = metadata.get("learning_label")
        target_rank = replay_rank_metrics.target_rank(
            execution.results,
            case.target_result_type,
            case.target_result_id,
        )
        target_key = replay_rank_metrics.string_result_key(
            case.target_result_type,
            case.target_result_id,
        )
        expected_top_n = case.expected_top_n or 0
        traceability_issues = claim_feedback_cases.claim_feedback_traceability_issues(
            case,
            metadata,
        )
        if learning_label == "positive":
            passed = target_rank is not None and target_rank <= expected_top_n
            verdict = (
                "positive_target_within_expected_top_n" if passed else "positive_target_missed"
            )
        elif learning_label == "negative":
            has_target = case.target_result_type is not None and case.target_result_id is not None
            passed = has_target and (target_rank is None or target_rank > expected_top_n)
            verdict = (
                "negative_target_excluded"
                if passed
                else "negative_target_still_prominent"
                if has_target
                else "negative_target_missing_from_feedback"
            )
        elif learning_label == "missing":
            passed = len(execution.results) > 0
            verdict = (
                "missing_evidence_query_recovered" if passed else "missing_evidence_still_empty"
            )
        else:
            passed = False
            verdict = "unsupported_claim_feedback_label"
        if traceability_issues:
            passed = False
            verdict = "claim_feedback_traceability_incomplete"
        return passed, {
            "target_key": [target_key[0], target_key[1]],
            "target_rank": target_rank,
            "matching_rank": target_rank if learning_label == "positive" else None,
            "expected_top_n": case.expected_top_n,
            "claim_feedback_replay_verdict": verdict,
            "claim_feedback_traceability_complete": not traceability_issues,
            "claim_feedback_traceability_issues": traceability_issues,
            "result_count": len(execution.results),
            "table_hit_count": execution.table_hit_count,
        }

    if case.feedback_type is not None:
        replay_keys = {
            replay_common._request_result_key(
                result.result_type,
                result.table_id if result.result_type == "table" else result.chunk_id,
            )
            for result in execution.results
        }
        target_key = replay_common._request_result_key(
            case.target_result_type,
            case.target_result_id,
        )
        if case.feedback_type == "relevant":
            return target_key in replay_keys, {
                "target_key": [str(target_key[0]), str(target_key[1])]
            }
        if case.feedback_type == "irrelevant":
            return target_key not in replay_keys, {
                "target_key": [str(target_key[0]), str(target_key[1])]
            }
        if case.feedback_type == "missing_table":
            return execution.table_hit_count > 0, {"table_hit_count": execution.table_hit_count}
        if case.feedback_type == "missing_chunk":
            chunk_hit_count = sum(
                1 for result in execution.results if result.result_type == "chunk"
            )
            return any(result.result_type == "chunk" for result in execution.results), {
                "chunk_hit_count": chunk_hit_count
            }
        if case.feedback_type == "no_answer":
            return len(execution.results) == 0, {"result_count": len(execution.results)}

    if case.source_reason == "zero_result_gap":
        return len(execution.results) > 0, {"result_count": len(execution.results)}
    if case.source_reason == "missing_table_gap":
        return execution.table_hit_count > 0, {"table_hit_count": execution.table_hit_count}
    return False, {}


def run_search_replay_suite(
    session: Session,
    request: SearchReplayRunRequest,
    *,
    harness_overrides: dict[str, dict] | None = None,
) -> SearchReplayRunDetailResponse:
    harness = get_search_harness(request.harness_name, harness_overrides)
    replay_run = SearchReplayRun(
        id=uuid.uuid4(),
        source_type=request.source_type,
        status="failed",
        harness_name=harness.name,
        created_at=utcnow(),
        summary_json={},
    )
    session.add(replay_run)
    session.flush()

    try:
        cases = replay_cases._build_replay_cases(session, request)
        created_at = utcnow()
        summary_counter: Counter[str] = Counter()
        rank_metrics = replay_rank_metrics.empty_replay_rank_metrics()
        last_execution = None

        for case in cases:
            filters = SearchRequest.model_validate(
                {
                    "query": case.query_text,
                    "mode": case.mode,
                    "filters": case.filters,
                    "limit": case.limit,
                    "harness_name": request.harness_name,
                }
            )
            execution = resolve_search_replays_service("execute_search", _execute_search)(
                session,
                filters,
                origin="replay_suite",
                parent_request_id=case.source_search_request_id,
                harness_overrides=harness_overrides,
            )
            last_execution = execution
            get_search_request_detail = resolve_search_replays_service(
                "get_search_request_detail",
                _get_search_request_detail,
            )
            replay_detail = (
                get_search_request_detail(session, execution.request_id)
                if execution.request_id is not None
                else None
            )
            diff = None
            if case.source_search_request_id is not None and replay_detail is not None:
                original_detail = get_search_request_detail(
                    session,
                    case.source_search_request_id,
                )
                build_search_replay_diff = resolve_search_replays_service(
                    "build_search_replay_diff",
                    _build_search_replay_diff,
                )
                diff = build_search_replay_diff(original_detail, replay_detail)

            passed, pass_details = _evaluate_case_passed(case, execution)
            summary_counter["query_count"] += 1
            summary_counter["passed_count"] += int(passed)
            summary_counter["failed_count"] += int(not passed)
            summary_counter["zero_result_count"] += int(len(execution.results) == 0)
            summary_counter["table_hit_count"] += int(execution.table_hit_count > 0)
            summary_counter["top_result_changes"] += int(bool(diff and diff.top_result_changed))
            summary_counter["max_rank_shift"] = max(
                summary_counter["max_rank_shift"],
                diff.max_rank_shift if diff else 0,
            )
            if replay_rank_metrics.is_rank_metric_case(case):
                rank_metrics["query_count"] += 1
                matching_rank = pass_details.get("matching_rank")
                if matching_rank:
                    rank_metrics["reciprocal_rank_sum"] = float(
                        rank_metrics.get("reciprocal_rank_sum") or 0.0
                    ) + (1.0 / matching_rank)
                if any(
                    (
                        case.expected_source_filename,
                        case.expected_top_result_source_filename,
                        case.minimum_top_n_hits_from_expected_document,
                        case.maximum_foreign_results_before_first_expected_hit,
                    )
                ):
                    rank_metrics["source_constrained_query_count"] += 1
                if case.expected_top_result_source_filename is not None:
                    rank_metrics["foreign_top_result_count"] += int(
                        not source_filename_matches(
                            pass_details.get("top_result_source_filename"),
                            case.expected_top_result_source_filename,
                        )
                    )

            details_json = {
                "source_reason": case.source_reason,
                "feedback_type": case.feedback_type,
                "embedding_status": execution.embedding_status,
                "harness_name": execution.harness_name,
                "reranker_name": execution.reranker_name,
                "reranker_version": execution.reranker_version,
                "retrieval_profile_name": execution.retrieval_profile_name,
                **(case.source_metadata or {}),
                **pass_details,
            }
            session.add(
                SearchReplayQuery(
                    id=uuid.uuid4(),
                    replay_run_id=replay_run.id,
                    source_search_request_id=case.source_search_request_id,
                    replay_search_request_id=execution.request_id,
                    feedback_id=case.feedback_id,
                    evaluation_query_id=case.evaluation_query_id,
                    query_text=case.query_text,
                    mode=case.mode,
                    filters_json=case.filters,
                    expected_result_type=case.expected_result_type,
                    expected_top_n=case.expected_top_n,
                    passed=passed,
                    result_count=len(execution.results),
                    table_hit_count=execution.table_hit_count,
                    overlap_count=diff.overlap_count if diff else 0,
                    added_count=diff.added_count if diff else 0,
                    removed_count=diff.removed_count if diff else 0,
                    top_result_changed=diff.top_result_changed if diff else False,
                    max_rank_shift=diff.max_rank_shift if diff else 0,
                    details_json=details_json,
                    created_at=created_at,
                )
            )

        replay_run.status = "completed"
        replay_run.harness_name = harness.name
        if last_execution is not None:
            replay_run.reranker_name = last_execution.reranker_name
            replay_run.reranker_version = last_execution.reranker_version
            replay_run.retrieval_profile_name = last_execution.retrieval_profile_name
            replay_run.harness_config_json = last_execution.harness_config
        else:
            replay_run.reranker_name = harness.reranker_name
            replay_run.reranker_version = harness.reranker_version
            replay_run.retrieval_profile_name = harness.retrieval_profile_name
            replay_run.harness_config_json = harness.config_snapshot
        replay_run.query_count = summary_counter["query_count"]
        replay_run.passed_count = summary_counter["passed_count"]
        replay_run.failed_count = summary_counter["failed_count"]
        replay_run.zero_result_count = summary_counter["zero_result_count"]
        replay_run.table_hit_count = summary_counter["table_hit_count"]
        replay_run.top_result_changes = summary_counter["top_result_changes"]
        replay_run.max_rank_shift = summary_counter["max_rank_shift"]
        replay_run.summary_json = {
            "source_type": request.source_type,
            "source_limit": request.limit,
            "harness_name": replay_run.harness_name,
            "reranker_name": replay_run.reranker_name,
            "reranker_version": replay_run.reranker_version,
            "retrieval_profile_name": replay_run.retrieval_profile_name,
            "query_count": replay_run.query_count,
            "passed_count": replay_run.passed_count,
            "failed_count": replay_run.failed_count,
            "zero_result_count": replay_run.zero_result_count,
            "table_hit_count": replay_run.table_hit_count,
            "top_result_changes": replay_run.top_result_changes,
            "max_rank_shift": replay_run.max_rank_shift,
            "rank_metrics": replay_rank_metrics.finalize_replay_rank_metrics(rank_metrics),
        }
        replay_run.completed_at = utcnow()
        session.flush()
        get_replay_run_detail = resolve_search_replays_service(
            "get_search_replay_run_detail",
            replay_common.get_search_replay_run_detail,
        )
        return get_replay_run_detail(session, replay_run.id)
    except Exception as exc:
        replay_run.status = "failed"
        replay_run.error_message = str(exc)
        replay_run.summary_json = {
            "source_type": request.source_type,
            "source_limit": request.limit,
            "harness_name": request.harness_name or "default_v1",
            "error": str(exc),
        }
        replay_run.completed_at = utcnow()
        session.flush()
        get_replay_run_detail = resolve_search_replays_service(
            "get_search_replay_run_detail",
            replay_common.get_search_replay_run_detail,
        )
        return get_replay_run_detail(session, replay_run.id)
