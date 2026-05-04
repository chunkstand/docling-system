from __future__ import annotations

from typing import Protocol

from app.services.capabilities.retrieval_audit_learning_contract import (
    RetrievalAuditLearningCapability,
)
from app.services.capabilities.retrieval_chat_feedback_contract import (
    RetrievalChatFeedbackCapability,
)
from app.services.capabilities.retrieval_evidence_contract import RetrievalEvidenceCapability
from app.services.capabilities.retrieval_harness_contract import RetrievalHarnessCapability
from app.services.capabilities.retrieval_replay_contract import RetrievalReplayCapability
from app.services.capabilities.retrieval_search_contract import RetrievalSearchCapability


class RetrievalCapability(
    RetrievalSearchCapability,
    RetrievalEvidenceCapability,
    RetrievalChatFeedbackCapability,
    RetrievalReplayCapability,
    RetrievalHarnessCapability,
    RetrievalAuditLearningCapability,
    Protocol,
):
    pass
