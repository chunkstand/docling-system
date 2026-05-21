from __future__ import annotations

import argparse
from uuid import UUID

from app.schemas.agent_task_search_workflows import VerifySearchHarnessEvaluationTaskInput

_MATERIALIZE_SOURCE_TYPE_CHOICES = (
    "feedback",
    "replay",
    "claim_support_replay_alert_corpus",
    "technical_report_claim_feedback",
)
_REPLAY_SOURCE_TYPE_CHOICES = (
    "evaluation_queries",
    "feedback",
    "live_search_gaps",
    "cross_document_prose_regressions",
    "technical_report_claim_feedback",
)
_DEFAULT_REPLAY_SOURCE_TYPES = [
    "evaluation_queries",
    "feedback",
    "live_search_gaps",
    "cross_document_prose_regressions",
]


def replay_source_types_or_default(source_types: list[str] | None) -> list[str]:
    return source_types or list(_DEFAULT_REPLAY_SOURCE_TYPES)


def add_replay_source_type_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--source-type",
        action="append",
        dest="source_types",
        choices=list(_REPLAY_SOURCE_TYPE_CHOICES),
        help="Replay source type to include. Can be passed multiple times.",
    )


def add_release_gate_threshold_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--max-total-regressed-count",
        type=int,
        default=0,
        help="Maximum allowed regressed query count across any source.",
    )
    parser.add_argument(
        "--max-mrr-drop",
        type=float,
        default=0.0,
        help="Maximum allowed per-source MRR drop.",
    )
    parser.add_argument(
        "--max-zero-result-count-increase",
        type=int,
        default=0,
        help="Maximum allowed per-source increase in zero-result queries.",
    )
    parser.add_argument(
        "--max-foreign-top-result-count-increase",
        type=int,
        default=0,
        help="Maximum allowed per-source increase in foreign top results.",
    )
    parser.add_argument(
        "--min-total-shared-query-count",
        type=int,
        default=1,
        help="Minimum number of shared replay queries required for a valid gate.",
    )


def build_gate_request(args: argparse.Namespace) -> VerifySearchHarnessEvaluationTaskInput:
    return VerifySearchHarnessEvaluationTaskInput(
        target_task_id=UUID(int=0),
        max_total_regressed_count=args.max_total_regressed_count,
        max_mrr_drop=args.max_mrr_drop,
        max_zero_result_count_increase=args.max_zero_result_count_increase,
        max_foreign_top_result_count_increase=args.max_foreign_top_result_count_increase,
        min_total_shared_query_count=args.min_total_shared_query_count,
    )
