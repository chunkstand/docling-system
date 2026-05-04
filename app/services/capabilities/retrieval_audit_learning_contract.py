from __future__ import annotations

from typing import Protocol

from app.services.capabilities.retrieval_audit_contract import RetrievalAuditCapability
from app.services.capabilities.retrieval_learning_contract import (
    RetrievalLearningCapability,
)


class RetrievalAuditLearningCapability(
    RetrievalAuditCapability,
    RetrievalLearningCapability,
    Protocol,
):
    pass
