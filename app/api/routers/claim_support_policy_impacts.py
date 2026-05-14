from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

import app.api.capabilities as api_capabilities
from app.api.deps import (
    get_storage_service,
    require_api_capability,
    require_api_key_for_mutations,
)
from app.api.routers.agent_task_route_services import service_from_parent
from app.db.session import get_db_session
from app.schemas.agent_task_claim_support import (
    ClaimSupportPolicyChangeImpactAlertEscalationRequest,
    ClaimSupportPolicyChangeImpactAlertResponse,
    ClaimSupportPolicyChangeImpactFixtureCandidateListResponse,
    ClaimSupportPolicyChangeImpactFixturePromotionRequest,
    ClaimSupportPolicyChangeImpactFixturePromotionResponse,
    ClaimSupportPolicyChangeImpactReplayRequest,
    ClaimSupportPolicyChangeImpactReplayResponse,
    ClaimSupportPolicyChangeImpactResponse,
    ClaimSupportPolicyChangeImpactSummaryResponse,
    ClaimSupportPolicyChangeImpactWorklistResponse,
)
from app.services.claim_support_policy_impacts import (
    claim_support_policy_change_impact_alerts,
    claim_support_policy_change_impact_fixture_candidates,
    claim_support_policy_change_impact_worklist,
    get_claim_support_policy_change_impact,
    list_claim_support_policy_change_impacts,
    promote_claim_support_policy_change_impact_fixture_candidates,
    queue_claim_support_policy_change_impact_replay_tasks,
    record_claim_support_policy_change_impact_alert_escalations,
    refresh_claim_support_policy_change_impact_replay_status,
    summarize_claim_support_policy_change_impacts,
)
from app.services.storage import StorageService

router = APIRouter()
DbSession = Annotated[Session, Depends(get_db_session)]
StorageDep = Annotated[StorageService, Depends(get_storage_service)]


@router.get(
    "/agent-tasks/claim-support-policy-change-impacts",
    response_model=list[ClaimSupportPolicyChangeImpactResponse],
    dependencies=[Depends(require_api_capability(api_capabilities.AGENT_TASKS_READ))],
)
def read_claim_support_policy_change_impacts(
    session: DbSession,
    policy_name: str | None = None,
    replay_status: str | None = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> list[ClaimSupportPolicyChangeImpactResponse]:
    return service_from_parent(
        "list_claim_support_policy_change_impacts",
        list_claim_support_policy_change_impacts,
    )(
        session,
        policy_name=policy_name,
        replay_status=replay_status,
        limit=limit,
    )


@router.get(
    "/agent-tasks/claim-support-policy-change-impacts/summary",
    response_model=ClaimSupportPolicyChangeImpactSummaryResponse,
    dependencies=[Depends(require_api_capability(api_capabilities.AGENT_TASKS_READ))],
)
def read_claim_support_policy_change_impact_summary(
    session: DbSession,
    policy_name: str | None = None,
    stale_after_hours: Annotated[int, Query(ge=1, le=720)] = 24,
) -> ClaimSupportPolicyChangeImpactSummaryResponse:
    return service_from_parent(
        "summarize_claim_support_policy_change_impacts",
        summarize_claim_support_policy_change_impacts,
    )(
        session,
        policy_name=policy_name,
        stale_after_hours=stale_after_hours,
    )


@router.get(
    "/agent-tasks/claim-support-policy-change-impacts/worklist",
    response_model=ClaimSupportPolicyChangeImpactWorklistResponse,
    dependencies=[Depends(require_api_capability(api_capabilities.AGENT_TASKS_READ))],
)
def read_claim_support_policy_change_impact_worklist(
    session: DbSession,
    policy_name: str | None = None,
    stale_after_hours: Annotated[int, Query(ge=1, le=720)] = 24,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    include_closed: bool = False,
) -> ClaimSupportPolicyChangeImpactWorklistResponse:
    return service_from_parent(
        "claim_support_policy_change_impact_worklist",
        claim_support_policy_change_impact_worklist,
    )(
        session,
        policy_name=policy_name,
        stale_after_hours=stale_after_hours,
        limit=limit,
        include_closed=include_closed,
    )


@router.get(
    "/agent-tasks/claim-support-policy-change-impacts/alerts",
    response_model=ClaimSupportPolicyChangeImpactAlertResponse,
    dependencies=[Depends(require_api_capability(api_capabilities.AGENT_TASKS_READ))],
)
def read_claim_support_policy_change_impact_alerts(
    session: DbSession,
    policy_name: str | None = None,
    stale_after_hours: Annotated[int, Query(ge=1, le=720)] = 24,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> ClaimSupportPolicyChangeImpactAlertResponse:
    return service_from_parent(
        "claim_support_policy_change_impact_alerts",
        claim_support_policy_change_impact_alerts,
    )(
        session,
        policy_name=policy_name,
        stale_after_hours=stale_after_hours,
        limit=limit,
    )


@router.post(
    "/agent-tasks/claim-support-policy-change-impacts/alerts/escalations",
    response_model=ClaimSupportPolicyChangeImpactAlertResponse,
    dependencies=[
        Depends(require_api_key_for_mutations),
        Depends(require_api_capability(api_capabilities.AGENT_TASKS_WRITE)),
    ],
)
def record_claim_support_policy_change_impact_alert_escalations_route(
    session: DbSession,
    storage_service: StorageDep,
    payload: ClaimSupportPolicyChangeImpactAlertEscalationRequest,
    policy_name: str | None = None,
    stale_after_hours: Annotated[int, Query(ge=1, le=720)] = 24,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> ClaimSupportPolicyChangeImpactAlertResponse:
    return service_from_parent(
        "record_claim_support_policy_change_impact_alert_escalations",
        record_claim_support_policy_change_impact_alert_escalations,
    )(
        session,
        policy_name=policy_name,
        stale_after_hours=stale_after_hours,
        limit=limit,
        requested_by=payload.requested_by,
        storage_service=storage_service,
    )


@router.get(
    "/agent-tasks/claim-support-policy-change-impacts/alerts/fixture-candidates",
    response_model=ClaimSupportPolicyChangeImpactFixtureCandidateListResponse,
    dependencies=[Depends(require_api_capability(api_capabilities.AGENT_TASKS_READ))],
)
def read_claim_support_policy_change_impact_fixture_candidates(
    session: DbSession,
    policy_name: str | None = None,
    stale_after_hours: Annotated[int, Query(ge=1, le=720)] = 24,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    include_unescalated: bool = False,
    include_promoted: bool = True,
) -> ClaimSupportPolicyChangeImpactFixtureCandidateListResponse:
    return service_from_parent(
        "claim_support_policy_change_impact_fixture_candidates",
        claim_support_policy_change_impact_fixture_candidates,
    )(
        session,
        policy_name=policy_name,
        stale_after_hours=stale_after_hours,
        limit=limit,
        include_unescalated=include_unescalated,
        include_promoted=include_promoted,
    )


@router.post(
    "/agent-tasks/claim-support-policy-change-impacts/alerts/fixture-promotions",
    response_model=ClaimSupportPolicyChangeImpactFixturePromotionResponse,
    dependencies=[
        Depends(require_api_key_for_mutations),
        Depends(require_api_capability(api_capabilities.AGENT_TASKS_WRITE)),
    ],
)
def promote_claim_support_policy_change_impact_fixture_candidates_route(
    session: DbSession,
    storage_service: StorageDep,
    payload: ClaimSupportPolicyChangeImpactFixturePromotionRequest,
    policy_name: str | None = None,
    stale_after_hours: Annotated[int, Query(ge=1, le=720)] = 24,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> ClaimSupportPolicyChangeImpactFixturePromotionResponse:
    return service_from_parent(
        "promote_claim_support_policy_change_impact_fixture_candidates",
        promote_claim_support_policy_change_impact_fixture_candidates,
    )(
        session,
        policy_name=policy_name,
        stale_after_hours=stale_after_hours,
        limit=limit,
        fixture_set_name=payload.fixture_set_name,
        fixture_set_version=payload.fixture_set_version,
        requested_by=payload.requested_by,
        include_unescalated=payload.include_unescalated,
        storage_service=storage_service,
    )


@router.get(
    "/agent-tasks/claim-support-policy-change-impacts/{change_impact_id}",
    response_model=ClaimSupportPolicyChangeImpactResponse,
    dependencies=[Depends(require_api_capability(api_capabilities.AGENT_TASKS_READ))],
)
def read_claim_support_policy_change_impact(
    session: DbSession,
    change_impact_id: UUID,
) -> ClaimSupportPolicyChangeImpactResponse:
    return service_from_parent(
        "get_claim_support_policy_change_impact",
        get_claim_support_policy_change_impact,
    )(session, change_impact_id)


@router.post(
    "/agent-tasks/claim-support-policy-change-impacts/{change_impact_id}/replay-tasks",
    response_model=ClaimSupportPolicyChangeImpactReplayResponse,
    dependencies=[
        Depends(require_api_key_for_mutations),
        Depends(require_api_capability(api_capabilities.AGENT_TASKS_WRITE)),
    ],
)
def create_claim_support_policy_change_impact_replay_tasks(
    session: DbSession,
    change_impact_id: UUID,
    payload: ClaimSupportPolicyChangeImpactReplayRequest,
) -> ClaimSupportPolicyChangeImpactReplayResponse:
    return service_from_parent(
        "queue_claim_support_policy_change_impact_replay_tasks",
        queue_claim_support_policy_change_impact_replay_tasks,
    )(
        session,
        change_impact_id,
        requested_by=payload.requested_by,
    )


@router.post(
    "/agent-tasks/claim-support-policy-change-impacts/{change_impact_id}/replay-status",
    response_model=ClaimSupportPolicyChangeImpactReplayResponse,
    dependencies=[
        Depends(require_api_key_for_mutations),
        Depends(require_api_capability(api_capabilities.AGENT_TASKS_WRITE)),
    ],
)
def refresh_claim_support_policy_change_impact_replay_status_route(
    session: DbSession,
    change_impact_id: UUID,
    storage_service: StorageDep,
) -> ClaimSupportPolicyChangeImpactReplayResponse:
    return service_from_parent(
        "refresh_claim_support_policy_change_impact_replay_status",
        refresh_claim_support_policy_change_impact_replay_status,
    )(
        session,
        change_impact_id,
        storage_service=storage_service,
    )


__all__ = ["router"]
