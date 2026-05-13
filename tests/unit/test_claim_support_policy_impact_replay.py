from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import UUID, uuid4

from app.services import claim_support_policy_impact_replay as _impact_replay

_NOW = datetime(2026, 5, 13, 12, 0, tzinfo=UTC)


class _FakeSession:
    def __init__(self) -> None:
        self.added: list[object] = []
        self.commit_count = 0
        self.flush_count = 0

    def add(self, value) -> None:
        self.added.append(value)

    def commit(self) -> None:
        self.commit_count += 1

    def flush(self) -> None:
        self.flush_count += 1


def _impact_row(
    *,
    change_impact_id: UUID | None = None,
    replay_recommended_count: int = 1,
    replay_status: str = "pending",
) -> SimpleNamespace:
    impact_id = change_impact_id or uuid4()
    activation_task_id = uuid4()
    return SimpleNamespace(
        id=impact_id,
        activation_task_id=activation_task_id,
        activated_policy_id=uuid4(),
        previous_policy_id=None,
        semantic_governance_event_id=None,
        governance_artifact_id=None,
        impact_scope="claim_support_policy",
        policy_name="claim-support-default",
        policy_version="v2",
        activated_policy_sha256="policy-sha",
        previous_policy_sha256=None,
        affected_support_judgment_count=2,
        affected_generated_document_count=1,
        affected_verification_count=1,
        replay_recommended_count=replay_recommended_count,
        replay_status=replay_status,
        impacted_claim_derivation_ids_json=[],
        impacted_task_ids_json=[],
        impacted_verification_task_ids_json=[],
        impact_payload_sha256="impact-payload-sha",
        impact_payload_json={
            "replay_recommendations": [
                {
                    "action": "rerun_draft_technical_report",
                    "target_task_id": str(uuid4()),
                    "reason": "Rerun the draft task.",
                    "priority": "high",
                },
                {
                    "action": "rerun_verify_technical_report",
                    "target_task_id": str(uuid4()),
                    "prior_verification_task_id": str(uuid4()),
                    "reason": "Reverify the refreshed draft.",
                    "priority": "high",
                },
            ]
        },
        replay_task_ids_json=[],
        replay_task_plan_json={},
        replay_closure_json={},
        replay_closure_sha256=None,
        replay_status_updated_at=_NOW,
        replay_closed_at=None,
        created_at=_NOW,
    )


def test_queue_claim_support_policy_change_impact_replay_tasks_builds_plan(
    monkeypatch,
) -> None:
    session = _FakeSession()
    change_impact_id = uuid4()
    row = _impact_row(change_impact_id=change_impact_id)
    source_draft_task_id = uuid4()
    prior_verification_task_id = uuid4()
    source_draft_task = SimpleNamespace(
        priority=100,
        tool_version="tool-v1",
        prompt_version="prompt-v1",
        model="gpt-5",
        model_settings_json={"temperature": 0},
        input_json={"task": "draft"},
        result_json={"status": "done"},
    )
    source_verify_task = SimpleNamespace(
        priority=100,
        tool_version="tool-v1",
        prompt_version="prompt-v1",
        model="gpt-5",
        model_settings_json={"temperature": 0},
        input_json={"target_task_id": str(source_draft_task_id)},
        result_json={"verification": "passed"},
    )
    queued_tasks = iter(
        [
            SimpleNamespace(
                task_id=uuid4(),
                status="queued",
                dependency_task_ids=[],
                input={"task": "draft"},
            ),
            SimpleNamespace(
                task_id=uuid4(),
                status="queued",
                dependency_task_ids=[],
                input={"task": "verify"},
            ),
        ]
    )

    monkeypatch.setattr(
        _impact_replay,
        "get_impact_row",
        lambda *_args, **_kwargs: row,
    )
    monkeypatch.setattr(
        _impact_replay,
        "_verify_replay_plan_integrity",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        _impact_replay,
        "_verify_replay_closure_integrity",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        _impact_replay,
        "_validated_replay_work_items",
        lambda *_args, **_kwargs: [
            {
                "action": "rerun_draft_technical_report",
                "source_draft_task_id": source_draft_task_id,
                "source_draft_task": source_draft_task,
                "recommendation": {"reason": "Rerun the draft task.", "priority": "high"},
            },
            {
                "action": "rerun_verify_technical_report",
                "source_draft_task_id": source_draft_task_id,
                "prior_verification_task_id": prior_verification_task_id,
                "source_verify_task": source_verify_task,
                "recommendation": {
                    "reason": "Reverify the refreshed draft.",
                    "priority": "high",
                },
            },
        ],
    )
    monkeypatch.setattr(
        _impact_replay,
        "_queue_agent_task",
        lambda *_args, **_kwargs: next(queued_tasks),
    )

    response = _impact_replay.queue_claim_support_policy_change_impact_replay_tasks(
        session,
        change_impact_id,
        requested_by="unit-test",
    )

    assert session.commit_count == 1
    assert row.replay_status == "queued"
    assert len(row.replay_task_ids_json) == 2
    assert row.replay_task_plan_json["schema_name"] == (
        _impact_replay.CLAIM_SUPPORT_IMPACT_REPLAY_PLAN_SCHEMA
    )
    assert len(response.created_tasks) == 2
    assert response.replay_status == "queued"


def test_refresh_claim_support_policy_change_impact_replay_status_closes_no_action_rows(
    monkeypatch,
) -> None:
    session = _FakeSession()
    row = _impact_row(replay_recommended_count=0, replay_status="pending")
    recorded_rows: list[UUID] = []

    monkeypatch.setattr(
        _impact_replay,
        "get_impact_row",
        lambda *_args, **_kwargs: row,
    )
    monkeypatch.setattr(
        _impact_replay,
        "_verify_replay_plan_integrity",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        _impact_replay,
        "_verify_replay_closure_integrity",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        _impact_replay,
        "_record_replay_closure_governance_event",
        lambda *_args, **_kwargs: recorded_rows.append(row.id),
    )

    response = _impact_replay.refresh_claim_support_policy_change_impact_replay_status(
        session,
        row.id,
        commit=False,
    )

    assert session.flush_count == 1
    assert row.replay_status == "no_action_required"
    assert row.replay_closure_sha256
    assert response.replay_status == "no_action_required"
    assert response.replay_closure["status"] == "no_action_required"
    assert recorded_rows == [row.id]
