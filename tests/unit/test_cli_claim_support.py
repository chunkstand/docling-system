from __future__ import annotations

import sys
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.claim_support_replay_cli import (
    run_claim_support_replay_alerts,
    run_claim_support_replay_fixture_candidates,
)


def test_claim_support_replay_alerts_cli_prints_table_and_records(
    monkeypatch,
    capsys,
) -> None:
    change_impact_id = uuid4()
    captured = {}

    class FakeSession:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    def fake_record_alerts(
        session,
        *,
        policy_name=None,
        stale_after_hours=24,
        limit=50,
        requested_by="docling-system",
        storage_service=None,
    ):
        captured.update(
            {
                "policy_name": policy_name,
                "stale_after_hours": stale_after_hours,
                "limit": limit,
                "requested_by": requested_by,
                "storage_service": storage_service,
            }
        )
        return SimpleNamespace(
            model_dump=lambda mode="json": {
                "matching_count": 1,
                "recorded_escalation_count": 1,
                "items": [
                    {
                        "change_impact": {
                            "change_impact_id": str(change_impact_id),
                        },
                        "alert_kind": "blocked",
                        "severity": "critical",
                        "replay_status": "blocked",
                        "status_age_hours": 3.5,
                        "recommended_action": "inspect_blockers",
                        "escalation_events": [{"event_id": str(uuid4())}],
                    }
                ],
            }
        )

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "docling-system-claim-support-replay-alerts",
            "--record-escalations",
            "--requested-by",
            "ops@example.com",
            "--policy-name",
            "claim_support_judge_calibration_policy",
            "--stale-after-hours",
            "6",
            "--limit",
            "2",
            "--format",
            "table",
        ],
    )
    monkeypatch.setattr(
        "app.claim_support_replay_cli.get_session_factory",
        lambda: lambda: FakeSession(),
    )
    monkeypatch.setattr(
        "app.claim_support_replay_cli.record_claim_support_policy_change_impact_alert_escalations",
        fake_record_alerts,
    )
    monkeypatch.setattr("app.claim_support_replay_cli.StorageService", lambda: object())

    run_claim_support_replay_alerts()

    output = capsys.readouterr().out
    assert "change_impact_id\talert_kind\tseverity" in output
    assert f"{change_impact_id}\tblocked\tcritical" in output
    captured_storage_service = captured.pop("storage_service")
    assert captured == {
        "policy_name": "claim_support_judge_calibration_policy",
        "stale_after_hours": 6,
        "limit": 2,
        "requested_by": "ops@example.com",
    }
    assert captured_storage_service is not None


def test_claim_support_replay_fixture_candidates_cli_promotes_and_prints_table(
    monkeypatch,
    capsys,
) -> None:
    candidate_id = "candidate-sha"
    change_impact_id = uuid4()
    captured = {}

    class FakeSession:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    class FakePayload:
        def model_dump(self, mode=None):
            return {
                "fixture_set_id": str(uuid4()),
                "fixture_set_name": "replay_alerts",
                "fixture_set_version": "v1",
                "fixture_set_sha256": "fixture-sha",
                "fixture_count": 7,
                "promoted_candidate_count": 1,
                "skipped_candidate_count": 0,
                "source_change_impact_ids": [str(change_impact_id)],
                "source_escalation_event_ids": [str(uuid4())],
                "promotion_event_id": str(uuid4()),
                "promotion_receipt_sha256": "receipt-sha",
                "artifact_id": None,
                "artifact_kind": None,
                "artifact_path": None,
                "created": True,
                "candidates": [
                    {
                        "candidate_id": candidate_id,
                        "change_impact_id": str(change_impact_id),
                        "alert_kind": "blocked",
                        "case_id": "case-1",
                        "expected_verdict": "supported",
                        "already_promoted": True,
                        "promotion_events": [{"event_id": str(uuid4())}],
                    }
                ],
            }

    def fake_promote(session, **kwargs):
        captured.update(kwargs)
        return FakePayload()

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "docling-system-claim-support-replay-fixtures",
            "--promote",
            "--requested-by",
            "ops@example.com",
            "--policy-name",
            "claim_support_judge_calibration_policy",
            "--stale-after-hours",
            "6",
            "--limit",
            "2",
            "--fixture-set-name",
            "replay_alerts",
            "--fixture-set-version",
            "v1",
            "--format",
            "table",
        ],
    )
    monkeypatch.setattr(
        "app.claim_support_replay_cli.get_session_factory",
        lambda: lambda: FakeSession(),
    )
    monkeypatch.setattr(
        "app.claim_support_replay_cli.promote_claim_support_policy_change_impact_fixture_candidates",
        fake_promote,
    )
    monkeypatch.setattr("app.claim_support_replay_cli.StorageService", lambda: object())

    run_claim_support_replay_fixture_candidates()

    output = capsys.readouterr().out
    assert "candidate_id\tchange_impact_id\talert_kind" in output
    assert f"{candidate_id}\t{change_impact_id}\tblocked" in output
    captured_storage_service = captured.pop("storage_service")
    assert captured == {
        "policy_name": "claim_support_judge_calibration_policy",
        "stale_after_hours": 6,
        "limit": 2,
        "fixture_set_name": "replay_alerts",
        "fixture_set_version": "v1",
        "requested_by": "ops@example.com",
        "include_unescalated": False,
    }
    assert captured_storage_service is not None


def test_claim_support_replay_alerts_cli_rejects_invalid_limit(
    monkeypatch,
    capsys,
) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        ["docling-system-claim-support-replay-alerts", "--limit", "0"],
    )

    with pytest.raises(SystemExit):
        run_claim_support_replay_alerts()

    assert "--limit must be between 1 and 200." in capsys.readouterr().err


def test_claim_support_replay_fixture_candidates_cli_rejects_invalid_stale_window(
    monkeypatch,
    capsys,
) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "docling-system-claim-support-replay-fixtures",
            "--stale-after-hours",
            "0",
        ],
    )

    with pytest.raises(SystemExit):
        run_claim_support_replay_fixture_candidates()

    assert "--stale-after-hours must be between 1 and 720." in capsys.readouterr().err
