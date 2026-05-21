from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime, timedelta

from sqlalchemy import Date, case, cast, func, select
from sqlalchemy.orm import Session

from app.db.public.retrieval import (
    ChatAnswerFeedback,
    SearchFeedback,
    SearchReplayRun,
    SearchRequestRecord,
)
from app.schemas.quality import (
    QualityFeedbackTypeCountResponse,
    QualityReplayRunTrendResponse,
    QualitySearchTrendPointResponse,
    QualityTrendsResponse,
)
from app.services.session_utils import uses_in_memory_session


def _get_quality_trends_in_memory(
    session: Session, *, day_count: int = 7, replay_limit: int = 8
) -> QualityTrendsResponse:
    search_requests = (
        session.execute(
            select(SearchRequestRecord).where(SearchRequestRecord.origin.in_(("api", "chat")))
        )
        .scalars()
        .all()
    )
    feedback_rows = session.execute(select(SearchFeedback)).scalars().all()
    answer_feedback_rows = session.execute(select(ChatAnswerFeedback)).scalars().all()
    replay_runs = (
        session.execute(select(SearchReplayRun).order_by(SearchReplayRun.created_at.desc()))
        .scalars()
        .all()
    )

    today = datetime.now(UTC).date()
    day_buckets = {
        (today - timedelta(days=offset)).isoformat(): {
            "request_count": 0,
            "zero_result_count": 0,
            "table_hit_requests": 0,
        }
        for offset in reversed(range(day_count))
    }

    for row in search_requests:
        bucket_key = row.created_at.date().isoformat()
        bucket = day_buckets.get(bucket_key)
        if bucket is None:
            continue
        bucket["request_count"] += 1
        bucket["zero_result_count"] += int(row.result_count == 0)
        bucket["table_hit_requests"] += int(row.table_hit_count > 0)

    feedback_counts = Counter(row.feedback_type for row in feedback_rows)
    answer_feedback_counts = Counter(row.feedback_type for row in answer_feedback_rows)

    return QualityTrendsResponse(
        search_request_days=[
            QualitySearchTrendPointResponse(
                bucket_date=bucket_date,
                request_count=values["request_count"],
                zero_result_count=values["zero_result_count"],
                table_hit_rate=(
                    values["table_hit_requests"] / values["request_count"]
                    if values["request_count"]
                    else 0.0
                ),
            )
            for bucket_date, values in day_buckets.items()
        ],
        feedback_counts=[
            QualityFeedbackTypeCountResponse(feedback_type=feedback_type, count=count)
            for feedback_type, count in sorted(
                feedback_counts.items(),
                key=lambda item: (-item[1], item[0]),
            )
        ],
        answer_feedback_counts=[
            QualityFeedbackTypeCountResponse(feedback_type=feedback_type, count=count)
            for feedback_type, count in sorted(
                answer_feedback_counts.items(),
                key=lambda item: (-item[1], item[0]),
            )
        ],
        recent_replay_runs=[
            QualityReplayRunTrendResponse(
                replay_run_id=row.id,
                source_type=row.source_type,
                status=row.status,
                query_count=row.query_count,
                passed_count=row.passed_count,
                failed_count=row.failed_count,
                created_at=row.created_at,
            )
            for row in replay_runs[:replay_limit]
        ],
    )

def get_quality_trends(
    session: Session, *, day_count: int = 7, replay_limit: int = 8
) -> QualityTrendsResponse:
    if uses_in_memory_session(session):
        return _get_quality_trends_in_memory(
            session,
            day_count=day_count,
            replay_limit=replay_limit,
        )

    today = datetime.now(UTC).date()
    cutoff = datetime.combine(
        today - timedelta(days=day_count - 1),
        datetime.min.time(),
        tzinfo=UTC,
    )
    bucket_date = cast(func.timezone("UTC", SearchRequestRecord.created_at), Date)
    search_request_days = session.execute(
        select(
            bucket_date.label("bucket_date"),
            func.count().label("request_count"),
            func.sum(case((SearchRequestRecord.result_count == 0, 1), else_=0)).label(
                "zero_result_count"
            ),
            func.sum(case((SearchRequestRecord.table_hit_count > 0, 1), else_=0)).label(
                "table_hit_requests"
            ),
        )
        .where(
            SearchRequestRecord.origin.in_(("api", "chat")),
            SearchRequestRecord.created_at >= cutoff,
        )
        .group_by(bucket_date)
    ).all()
    feedback_counts = session.execute(
        select(SearchFeedback.feedback_type, func.count().label("count")).group_by(
            SearchFeedback.feedback_type
        )
    ).all()
    answer_feedback_counts = session.execute(
        select(ChatAnswerFeedback.feedback_type, func.count().label("count")).group_by(
            ChatAnswerFeedback.feedback_type
        )
    ).all()
    replay_runs = (
        session.execute(
            select(SearchReplayRun).order_by(SearchReplayRun.created_at.desc()).limit(replay_limit)
        )
        .scalars()
        .all()
    )

    day_buckets = {
        (today - timedelta(days=offset)).isoformat(): {
            "request_count": 0,
            "zero_result_count": 0,
            "table_hit_requests": 0,
        }
        for offset in reversed(range(day_count))
    }
    for bucket_row in search_request_days:
        bucket = day_buckets.get(bucket_row.bucket_date.isoformat())
        if bucket is None:
            continue
        bucket["request_count"] = int(bucket_row.request_count)
        bucket["zero_result_count"] = int(bucket_row.zero_result_count or 0)
        bucket["table_hit_requests"] = int(bucket_row.table_hit_requests or 0)

    return QualityTrendsResponse(
        search_request_days=[
            QualitySearchTrendPointResponse(
                bucket_date=bucket_date,
                request_count=values["request_count"],
                zero_result_count=values["zero_result_count"],
                table_hit_rate=(
                    values["table_hit_requests"] / values["request_count"]
                    if values["request_count"]
                    else 0.0
                ),
            )
            for bucket_date, values in day_buckets.items()
        ],
        feedback_counts=[
            QualityFeedbackTypeCountResponse(feedback_type=feedback_type, count=int(count))
            for feedback_type, count in sorted(
                feedback_counts,
                key=lambda item: (-int(item[1]), item[0]),
            )
        ],
        answer_feedback_counts=[
            QualityFeedbackTypeCountResponse(feedback_type=feedback_type, count=int(count))
            for feedback_type, count in sorted(
                answer_feedback_counts,
                key=lambda item: (-int(item[1]), item[0]),
            )
        ],
        recent_replay_runs=[
            QualityReplayRunTrendResponse(
                replay_run_id=row.id,
                source_type=row.source_type,
                status=row.status,
                query_count=row.query_count,
                passed_count=row.passed_count,
                failed_count=row.failed_count,
                created_at=row.created_at,
            )
            for row in replay_runs
        ],
    )
