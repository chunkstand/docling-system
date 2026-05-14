from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.errors import api_error
from app.api.main import app


def test_claim_support_policy_change_impact_detail_route_returns_error_code(
    monkeypatch,
) -> None:
    change_impact_id = uuid4()

    def fake_get_claim_support_policy_change_impact(session, requested_change_impact_id):
        raise api_error(
            404,
            "claim_support_policy_change_impact_not_found",
            "Claim support policy change impact row was not found.",
            change_impact_id=str(requested_change_impact_id),
        )

    monkeypatch.setattr(
        "app.api.routers.agent_tasks.get_claim_support_policy_change_impact",
        fake_get_claim_support_policy_change_impact,
    )

    client = TestClient(app)
    response = client.get(f"/agent-tasks/claim-support-policy-change-impacts/{change_impact_id}")

    assert response.status_code == 404
    assert response.json()["error_code"] == "claim_support_policy_change_impact_not_found"
    assert response.json()["error_context"]["change_impact_id"] == str(change_impact_id)


def test_claim_support_policy_change_impact_worklist_route_uses_service(
    monkeypatch,
) -> None:
    captured = {}
    now = datetime(2026, 4, 12, tzinfo=UTC)

    def fake_claim_support_policy_change_impact_worklist(
        session,
        *,
        policy_name=None,
        stale_after_hours=24,
        limit=50,
        include_closed=False,
    ):
        captured.update(
            {
                "policy_name": policy_name,
                "stale_after_hours": stale_after_hours,
                "limit": limit,
                "include_closed": include_closed,
            }
        )
        return {
            "summary": {
                "total_count": 1,
                "replay_status_counts": {"queued": 1},
                "open_count": 1,
                "stale_open_count": 0,
                "stale_after_hours": stale_after_hours,
                "stale_cutoff": now,
            },
            "generated_at": now,
            "stale_after_hours": stale_after_hours,
            "limit": limit,
            "matching_count": 3,
            "item_count": 0,
            "has_more": True,
            "items": [],
        }

    monkeypatch.setattr(
        "app.api.routers.agent_tasks.claim_support_policy_change_impact_worklist",
        fake_claim_support_policy_change_impact_worklist,
    )

    client = TestClient(app)
    response = client.get(
        "/agent-tasks/claim-support-policy-change-impacts/worklist"
        "?policy_name=claim_support_judge_calibration_policy"
        "&stale_after_hours=12&limit=2&include_closed=true"
    )

    assert response.status_code == 200
    assert response.json()["summary"]["open_count"] == 1
    assert response.json()["limit"] == 2
    assert response.json()["matching_count"] == 3
    assert response.json()["has_more"] is True
    assert captured == {
        "policy_name": "claim_support_judge_calibration_policy",
        "stale_after_hours": 12,
        "limit": 2,
        "include_closed": True,
    }


def test_claim_support_policy_change_impact_worklist_rejects_invalid_query() -> None:
    client = TestClient(app)
    response = client.get(
        "/agent-tasks/claim-support-policy-change-impacts/worklist?stale_after_hours=0"
    )

    assert response.status_code == 422


def test_claim_support_policy_change_impact_alerts_route_uses_service(
    monkeypatch,
) -> None:
    captured = {}
    now = datetime(2026, 4, 12, tzinfo=UTC)

    def fake_claim_support_policy_change_impact_alerts(
        session,
        *,
        policy_name=None,
        stale_after_hours=24,
        limit=50,
    ):
        captured.update(
            {
                "policy_name": policy_name,
                "stale_after_hours": stale_after_hours,
                "limit": limit,
            }
        )
        return {
            "summary": {
                "total_count": 2,
                "replay_status_counts": {"blocked": 1, "pending": 1},
                "open_count": 2,
                "stale_open_count": 1,
                "stale_after_hours": stale_after_hours,
                "stale_cutoff": now,
            },
            "generated_at": now,
            "stale_after_hours": stale_after_hours,
            "limit": limit,
            "matching_count": 2,
            "item_count": 0,
            "has_more": False,
            "recorded_escalation_count": 0,
            "items": [],
        }

    monkeypatch.setattr(
        "app.api.routers.agent_tasks.claim_support_policy_change_impact_alerts",
        fake_claim_support_policy_change_impact_alerts,
    )

    client = TestClient(app)
    response = client.get(
        "/agent-tasks/claim-support-policy-change-impacts/alerts"
        "?policy_name=claim_support_judge_calibration_policy"
        "&stale_after_hours=6&limit=3"
    )

    assert response.status_code == 200
    assert response.json()["matching_count"] == 2
    assert captured == {
        "policy_name": "claim_support_judge_calibration_policy",
        "stale_after_hours": 6,
        "limit": 3,
    }


def test_claim_support_policy_change_impact_alerts_rejects_invalid_query() -> None:
    client = TestClient(app)
    response = client.get("/agent-tasks/claim-support-policy-change-impacts/alerts?limit=0")

    assert response.status_code == 422


def test_claim_support_policy_change_impact_alert_escalation_route_uses_service(
    monkeypatch,
) -> None:
    captured = {}
    now = datetime(2026, 4, 12, tzinfo=UTC)

    def fake_record_claim_support_policy_change_impact_alert_escalations(
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
        return {
            "summary": {
                "total_count": 1,
                "replay_status_counts": {"blocked": 1},
                "open_count": 1,
                "stale_open_count": 0,
                "stale_after_hours": stale_after_hours,
                "stale_cutoff": now,
            },
            "generated_at": now,
            "stale_after_hours": stale_after_hours,
            "limit": limit,
            "matching_count": 1,
            "item_count": 0,
            "has_more": False,
            "recorded_escalation_count": 1,
            "items": [],
        }

    monkeypatch.setattr(
        "app.api.routers.agent_tasks.record_claim_support_policy_change_impact_alert_escalations",
        fake_record_claim_support_policy_change_impact_alert_escalations,
    )

    client = TestClient(app)
    response = client.post(
        "/agent-tasks/claim-support-policy-change-impacts/alerts/escalations"
        "?policy_name=claim_support_judge_calibration_policy"
        "&stale_after_hours=6&limit=3",
        json={"requested_by": "ops@example.com"},
    )

    assert response.status_code == 200
    assert response.json()["recorded_escalation_count"] == 1
    captured_storage_service = captured.pop("storage_service")
    assert captured == {
        "policy_name": "claim_support_judge_calibration_policy",
        "stale_after_hours": 6,
        "limit": 3,
        "requested_by": "ops@example.com",
    }
    assert captured_storage_service is not None


def test_claim_support_policy_change_impact_alert_escalation_rejects_invalid_query() -> None:
    client = TestClient(app)
    response = client.post(
        "/agent-tasks/claim-support-policy-change-impacts/alerts/escalations?stale_after_hours=0",
        json={"requested_by": "ops@example.com"},
    )

    assert response.status_code == 422


def test_claim_support_policy_change_impact_fixture_candidates_route_uses_service(
    monkeypatch,
) -> None:
    captured = {}
    now = datetime(2026, 4, 12, tzinfo=UTC)

    def fake_fixture_candidates(
        session,
        *,
        policy_name=None,
        stale_after_hours=24,
        limit=50,
        include_unescalated=False,
        include_promoted=True,
    ):
        captured.update(
            {
                "policy_name": policy_name,
                "stale_after_hours": stale_after_hours,
                "limit": limit,
                "include_unescalated": include_unescalated,
                "include_promoted": include_promoted,
            }
        )
        return {
            "summary": {
                "alert_matching_count": 1,
                "candidate_count": 1,
                "promoted_candidate_count": 0,
                "unpromoted_candidate_count": 1,
                "source_escalation_event_count": 1,
                "stale_after_hours": stale_after_hours,
            },
            "generated_at": now,
            "stale_after_hours": stale_after_hours,
            "limit": limit,
            "matching_count": 1,
            "item_count": 0,
            "has_more": False,
            "items": [],
        }

    monkeypatch.setattr(
        "app.api.routers.agent_tasks.claim_support_policy_change_impact_fixture_candidates",
        fake_fixture_candidates,
    )

    client = TestClient(app)
    response = client.get(
        "/agent-tasks/claim-support-policy-change-impacts/alerts/fixture-candidates"
        "?policy_name=claim_support_judge_calibration_policy"
        "&stale_after_hours=6&limit=3&include_unescalated=true&include_promoted=false"
    )

    assert response.status_code == 200
    assert response.json()["summary"]["candidate_count"] == 1
    assert captured == {
        "policy_name": "claim_support_judge_calibration_policy",
        "stale_after_hours": 6,
        "limit": 3,
        "include_unescalated": True,
        "include_promoted": False,
    }


def test_claim_support_policy_change_impact_fixture_candidates_rejects_invalid_query() -> None:
    client = TestClient(app)
    response = client.get(
        "/agent-tasks/claim-support-policy-change-impacts/alerts/fixture-candidates?limit=0"
    )

    assert response.status_code == 422


def test_claim_support_policy_change_impact_fixture_promotion_route_uses_service(
    monkeypatch,
) -> None:
    captured = {}

    def fake_promote_fixture_candidates(
        session,
        *,
        policy_name=None,
        stale_after_hours=24,
        limit=50,
        fixture_set_name="claim_support_replay_alert_promotions",
        fixture_set_version="v1",
        requested_by="docling-system",
        include_unescalated=False,
        storage_service=None,
    ):
        captured.update(
            {
                "policy_name": policy_name,
                "stale_after_hours": stale_after_hours,
                "limit": limit,
                "fixture_set_name": fixture_set_name,
                "fixture_set_version": fixture_set_version,
                "requested_by": requested_by,
                "include_unescalated": include_unescalated,
                "storage_service": storage_service,
            }
        )
        return {
            "fixture_set_id": uuid4(),
            "fixture_set_name": fixture_set_name,
            "fixture_set_version": fixture_set_version,
            "fixture_set_sha256": "fixture-sha",
            "fixture_count": 7,
            "promoted_candidate_count": 1,
            "skipped_candidate_count": 0,
            "source_change_impact_ids": [],
            "source_escalation_event_ids": [],
            "promotion_event_id": uuid4(),
            "promotion_receipt_sha256": "receipt-sha",
            "artifact_id": None,
            "artifact_kind": None,
            "artifact_path": None,
            "created": True,
            "candidates": [],
        }

    monkeypatch.setattr(
        "app.api.routers.agent_tasks.promote_claim_support_policy_change_impact_fixture_candidates",
        fake_promote_fixture_candidates,
    )

    client = TestClient(app)
    response = client.post(
        "/agent-tasks/claim-support-policy-change-impacts/alerts/fixture-promotions"
        "?policy_name=claim_support_judge_calibration_policy"
        "&stale_after_hours=6&limit=3",
        json={
            "fixture_set_name": "replay_alerts_v1",
            "fixture_set_version": "v7",
            "requested_by": "ops@example.com",
            "include_unescalated": True,
        },
    )

    assert response.status_code == 200
    assert response.json()["promoted_candidate_count"] == 1
    captured_storage_service = captured.pop("storage_service")
    assert captured == {
        "policy_name": "claim_support_judge_calibration_policy",
        "stale_after_hours": 6,
        "limit": 3,
        "fixture_set_name": "replay_alerts_v1",
        "fixture_set_version": "v7",
        "requested_by": "ops@example.com",
        "include_unescalated": True,
    }
    assert captured_storage_service is not None


def test_claim_support_policy_change_impact_fixture_promotion_rejects_invalid_query() -> None:
    client = TestClient(app)
    response = client.post(
        "/agent-tasks/claim-support-policy-change-impacts/alerts/fixture-promotions?limit=0",
        json={"requested_by": "ops@example.com"},
    )

    assert response.status_code == 422
