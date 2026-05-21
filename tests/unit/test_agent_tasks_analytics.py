from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from app.db.public.agent_tasks import AgentTask, AgentTaskAttempt, AgentTaskOutcome, AgentTaskStatus
from app.services.agent_task_analytics_summary import (
    get_agent_approval_trends,
    get_agent_task_trends,
    get_agent_verification_trends,
)
from app.services.agent_task_cost_performance import (
    get_agent_task_cost_summary,
    get_agent_task_performance_summary,
)
from app.services.agent_task_recommendation_metrics import (
    get_agent_task_recommendation_summary,
    get_agent_task_value_density,
)
from tests.unit.agent_task_service_support import FakeSession


def test_agent_task_trends_bucket_attempt_metrics_with_attempt_task() -> None:
    first_created = datetime(2026, 4, 12, 10, 0, tzinfo=UTC)
    second_created = datetime(2026, 4, 13, 10, 0, tzinfo=UTC)
    first_task = AgentTask(
        id=uuid4(),
        task_type="triage_replay_regression",
        status=AgentTaskStatus.COMPLETED.value,
        priority=100,
        side_effect_level="read_only",
        requires_approval=False,
        input_json={},
        result_json={},
        workflow_version="v1",
        model_settings_json={},
        created_at=first_created,
        updated_at=first_created,
    )
    second_task = AgentTask(
        id=uuid4(),
        task_type="triage_replay_regression",
        status=AgentTaskStatus.COMPLETED.value,
        priority=100,
        side_effect_level="read_only",
        requires_approval=False,
        input_json={},
        result_json={},
        workflow_version="v1",
        model_settings_json={},
        created_at=second_created,
        updated_at=second_created,
    )
    first_attempt = AgentTaskAttempt(
        id=uuid4(),
        task_id=first_task.id,
        attempt_number=1,
        status="completed",
        input_json={},
        result_json={},
        cost_json={},
        performance_json={"queue_latency_ms": 5.0, "execution_latency_ms": 10.0},
        created_at=first_created,
    )
    second_attempt = AgentTaskAttempt(
        id=uuid4(),
        task_id=second_task.id,
        attempt_number=1,
        status="completed",
        input_json={},
        result_json={},
        cost_json={},
        performance_json={"queue_latency_ms": 7.0, "execution_latency_ms": 14.0},
        created_at=second_created,
    )
    session = FakeSession(
        task_rows=[first_task, second_task],
        attempt_rows=[first_attempt, second_attempt],
    )

    response = get_agent_task_trends(session)

    assert len(response.series) == 2
    assert response.series[0].median_execution_latency_ms == 10.0
    assert response.series[1].median_execution_latency_ms == 14.0


def test_agent_verification_trends_counts_outcomes_by_bucket() -> None:
    created_at = datetime(2026, 4, 12, 10, 0, tzinfo=UTC)
    verification_rows = [
        type("VerificationRow", (), {"created_at": created_at, "outcome": "passed"})(),
        type("VerificationRow", (), {"created_at": created_at, "outcome": "failed"})(),
    ]
    session = FakeSession(verification_rows=verification_rows)

    response = get_agent_verification_trends(session)

    assert len(response.series) == 1
    assert response.series[0].passed_count == 1
    assert response.series[0].failed_count == 1
    assert response.series[0].error_count == 0


def test_agent_approval_trends_counts_approved_and_rejected_tasks() -> None:
    approved_at = datetime(2026, 4, 12, 10, 0, tzinfo=UTC)
    rejected_at = datetime(2026, 4, 13, 9, 0, tzinfo=UTC)
    session = FakeSession(
        task_rows=[
            AgentTask(
                id=uuid4(),
                task_type="apply_harness_config_update",
                status=AgentTaskStatus.COMPLETED.value,
                priority=100,
                side_effect_level="promotable",
                requires_approval=True,
                input_json={},
                result_json={},
                workflow_version="v1",
                model_settings_json={},
                approved_at=approved_at,
                created_at=approved_at,
                updated_at=approved_at,
            ),
            AgentTask(
                id=uuid4(),
                task_type="apply_harness_config_update",
                status=AgentTaskStatus.REJECTED.value,
                priority=100,
                side_effect_level="promotable",
                requires_approval=True,
                input_json={},
                result_json={},
                workflow_version="v1",
                model_settings_json={},
                rejected_at=rejected_at,
                created_at=rejected_at,
                updated_at=rejected_at,
            ),
        ]
    )

    response = get_agent_approval_trends(session)

    assert len(response.series) == 2
    assert response.series[0].approval_count == 1
    assert response.series[1].rejection_count == 1


def test_agent_task_cost_summary_aggregates_attempt_costs() -> None:
    now = datetime.now(UTC)
    task = AgentTask(
        id=uuid4(),
        task_type="triage_replay_regression",
        status=AgentTaskStatus.COMPLETED.value,
        priority=100,
        side_effect_level="read_only",
        requires_approval=False,
        input_json={},
        result_json={},
        workflow_version="v1",
        model_settings_json={},
        created_at=now,
        updated_at=now,
    )
    attempts = [
        AgentTaskAttempt(
            id=uuid4(),
            task_id=task.id,
            attempt_number=1,
            status="completed",
            input_json={},
            result_json={},
            cost_json={"estimated_usd": 1.25, "call_count": 2, "embedding_count": 1},
            performance_json={},
            created_at=now,
        ),
        AgentTaskAttempt(
            id=uuid4(),
            task_id=task.id,
            attempt_number=2,
            status="completed",
            input_json={},
            result_json={},
            cost_json={"estimated_usd": 0.75, "call_count": 1, "replay_query_count": 3},
            performance_json={},
            created_at=now,
        ),
    ]
    session = FakeSession(task_rows=[task], attempt_rows=attempts)

    summary = get_agent_task_cost_summary(session, task_type="triage_replay_regression")

    assert summary.attempt_count == 2
    assert summary.instrumented_attempt_count == 2
    assert summary.estimated_usd_total == 2.0
    assert summary.model_call_count == 3
    assert summary.embedding_count == 1
    assert summary.replay_query_count == 3


def test_agent_task_performance_summary_aggregates_attempt_latencies() -> None:
    now = datetime.now(UTC)
    task = AgentTask(
        id=uuid4(),
        task_type="triage_replay_regression",
        status=AgentTaskStatus.COMPLETED.value,
        priority=100,
        side_effect_level="read_only",
        requires_approval=False,
        input_json={},
        result_json={},
        workflow_version="v1",
        model_settings_json={},
        created_at=now,
        updated_at=now,
    )
    attempts = [
        AgentTaskAttempt(
            id=uuid4(),
            task_id=task.id,
            attempt_number=1,
            status="completed",
            input_json={},
            result_json={},
            cost_json={},
            performance_json={
                "queue_latency_ms": 5.0,
                "execution_latency_ms": 20.0,
                "end_to_end_latency_ms": 40.0,
            },
            created_at=now,
        ),
        AgentTaskAttempt(
            id=uuid4(),
            task_id=task.id,
            attempt_number=2,
            status="completed",
            input_json={},
            result_json={},
            cost_json={},
            performance_json={
                "queue_latency_ms": 15.0,
                "execution_latency_ms": 30.0,
                "end_to_end_latency_ms": 60.0,
            },
            created_at=now,
        ),
    ]
    session = FakeSession(task_rows=[task], attempt_rows=attempts)

    summary = get_agent_task_performance_summary(session, task_type="triage_replay_regression")

    assert summary.attempt_count == 2
    assert summary.instrumented_attempt_count == 2
    assert summary.median_queue_latency_ms == 5.0
    assert summary.median_execution_latency_ms == 20.0
    assert summary.median_end_to_end_latency_ms == 40.0


def test_recommendation_summary_task_type_filter_keeps_linked_tasks() -> None:
    now = datetime.now(UTC)
    triage_task = AgentTask(
        id=uuid4(),
        task_type="triage_replay_regression",
        status=AgentTaskStatus.COMPLETED.value,
        priority=100,
        side_effect_level="read_only",
        requires_approval=False,
        result_json={"recommendation": {"next_action": "candidate_ready_for_review"}},
        input_json={},
        workflow_version="v1",
        model_settings_json={},
        created_at=now,
        updated_at=now,
    )
    draft_task = AgentTask(
        id=uuid4(),
        task_type="draft_harness_config_update",
        status=AgentTaskStatus.COMPLETED.value,
        priority=100,
        side_effect_level="draft_change",
        requires_approval=False,
        input_json={"source_task_id": str(triage_task.id)},
        result_json={},
        workflow_version="v1",
        model_settings_json={},
        created_at=now,
        updated_at=now,
    )
    session = FakeSession(task_rows=[triage_task, draft_task])

    summary = get_agent_task_recommendation_summary(
        session,
        task_type="triage_replay_regression",
        workflow_version="v1",
    )

    assert summary.recommendation_task_count == 1
    assert summary.draft_count == 1


def test_value_density_includes_linked_workflow_attempt_costs() -> None:
    now = datetime.now(UTC)
    triage_task = AgentTask(
        id=uuid4(),
        task_type="triage_replay_regression",
        status=AgentTaskStatus.COMPLETED.value,
        priority=100,
        side_effect_level="read_only",
        requires_approval=False,
        result_json={"recommendation": {"next_action": "candidate_ready_for_review"}},
        input_json={},
        workflow_version="v1",
        model_settings_json={},
        created_at=now,
        updated_at=now,
    )
    draft_task = AgentTask(
        id=uuid4(),
        task_type="draft_harness_config_update",
        status=AgentTaskStatus.COMPLETED.value,
        priority=100,
        side_effect_level="draft_change",
        requires_approval=False,
        input_json={"source_task_id": str(triage_task.id)},
        result_json={},
        workflow_version="v1",
        model_settings_json={},
        created_at=now,
        updated_at=now,
    )
    triage_attempt = AgentTaskAttempt(
        id=uuid4(),
        task_id=triage_task.id,
        attempt_number=1,
        status="completed",
        input_json={},
        result_json={},
        cost_json={"estimated_usd": 1.0},
        performance_json={"end_to_end_latency_ms": 1000.0},
        created_at=now,
    )
    draft_attempt = AgentTaskAttempt(
        id=uuid4(),
        task_id=draft_task.id,
        attempt_number=1,
        status="completed",
        input_json={},
        result_json={},
        cost_json={"estimated_usd": 2.0},
        performance_json={"end_to_end_latency_ms": 2000.0},
        created_at=now,
    )
    useful_outcome = AgentTaskOutcome(
        id=uuid4(),
        task_id=triage_task.id,
        outcome_label="useful",
        created_by="operator@example.com",
        created_at=now,
    )
    session = FakeSession(
        task_rows=[triage_task, draft_task],
        attempt_rows=[triage_attempt, draft_attempt],
        outcome_rows=[useful_outcome],
    )

    rows = get_agent_task_value_density(session)

    assert len(rows) == 1
    assert rows[0].estimated_usd_total == 3.0
