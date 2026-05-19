from __future__ import annotations

import app.services.agent_task_context as agent_task_context_module
from app.services.agent_task_context_technical_reports import (
    build_technical_report_context_builders,
)
from app.services.agent_task_context_technical_reports_claim_support import (
    build_technical_report_claim_support_context_builders,
)


def test_technical_report_context_builders_include_claim_support_owner_registry() -> None:
    builders = build_technical_report_context_builders(agent_task_context_module.__dict__)
    claim_support_builders = build_technical_report_claim_support_context_builders(
        agent_task_context_module.__dict__
    )

    assert set(builders) == {
        "plan_technical_report",
        "build_report_evidence_cards",
        "prepare_report_agent_harness",
        "evaluate_document_generation_context_pack",
        "draft_technical_report",
        "verify_technical_report",
        "evaluate_claim_support_judge",
    }
    for builder_name, builder in claim_support_builders.items():
        assert builders[builder_name] is builder
