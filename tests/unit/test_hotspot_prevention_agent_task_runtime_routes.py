from __future__ import annotations

from pathlib import Path

from app.hotspot_prevention import build_hotspot_prevention_report, load_hotspot_policy
from tests.unit.hotspot_prevention_test_support import _diff_for


def test_agent_task_worker_hotspot_blocks_new_lease_logic() -> None:
    report = build_hotspot_prevention_report(
        _diff_for(
            "app/services/agent_task_worker.py",
            ["task.locked_by = worker_id"],
        ),
        policy=load_hotspot_policy(),
        project_root=Path.cwd(),
    )

    assert report["summary"]["blocked_count"] == 1
    assert report["findings"][0]["category"] == "lease_management_logic"


def test_agent_task_worker_hotspot_allows_forwarding_wrapper() -> None:
    report = build_hotspot_prevention_report(
        _diff_for(
            "app/services/agent_task_worker.py",
            [
                "def claim_next_agent_task(session, worker_id):",
                "    return lease_owner.claim_next_agent_task(session, worker_id)",
            ],
        ),
        policy=load_hotspot_policy(),
        project_root=Path.cwd(),
    )

    assert report["summary"]["blocked_count"] == 0
    assert report["findings"][0]["category"] == "explicit_forwarding_function"


def test_agent_task_verifications_hotspot_blocks_semantic_logic() -> None:
    report = build_hotspot_prevention_report(
        _diff_for(
            "app/services/agent_task_verifications.py",
            [
                "preview_registry_update_for_document_func=preview_semantic_registry_update_for_document,"
            ],
        ),
        policy=load_hotspot_policy(),
        project_root=Path.cwd(),
    )

    assert report["summary"]["blocked_count"] == 1
    assert report["findings"][0]["category"] == "semantic_verification_logic"


def test_agent_task_verifications_hotspot_allows_forwarding_wrapper() -> None:
    report = build_hotspot_prevention_report(
        _diff_for(
            "app/services/agent_task_verifications.py",
            [
                "def verify_semantic_grounded_document_task(session, verification_task, payload):",
                "    return semantics_owner.verify_semantic_grounded_document_task(",
                "        session,",
                "        verification_task,",
                "        payload,",
                "    )",
            ],
        ),
        policy=load_hotspot_policy(),
        project_root=Path.cwd(),
    )

    assert report["summary"]["blocked_count"] == 0
    assert report["findings"][0]["category"] == "explicit_forwarding_function"
