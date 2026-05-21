"""Expected public ORM model contract for data-model boundary work."""

from __future__ import annotations

from tests.db_model_contract_domains import (
    agent_tasks as _agent_tasks,
)
from tests.db_model_contract_domains import (
    audit_and_evidence as _audit_and_evidence,
)
from tests.db_model_contract_domains import (
    claim_support as _claim_support,
)
from tests.db_model_contract_domains import (
    common as _common,
)
from tests.db_model_contract_domains import (
    document_artifacts as _document_artifacts,
)
from tests.db_model_contract_domains import (
    evaluation_feedback as _evaluation_feedback,
)
from tests.db_model_contract_domains import (
    ingest as _ingest,
)
from tests.db_model_contract_domains import (
    platform_support as _platform_support,
)
from tests.db_model_contract_domains import (
    retrieval as _retrieval,
)
from tests.db_model_contract_domains import (
    semantic_memory as _semantic_memory,
)

DB_MODELS_ENUM_SUPPORT_MODULE = _common.DB_MODELS_ENUM_SUPPORT_MODULE
ENUM_SYMBOLS = _common.ENUM_SYMBOLS
FACADE_CONSTANT_SYMBOLS = _common.FACADE_CONSTANT_SYMBOLS
ALLOWED_DB_MODELS_SUPPORT_SYMBOLS = _common.ALLOWED_DB_MODELS_SUPPORT_SYMBOLS
PUBLIC_DB_FACADE_EXPORT_SYMBOLS = {
    "agent_tasks": _common.AGENT_TASK_ENUM_SYMBOLS + _agent_tasks.MODEL_SYMBOLS,
    "audit_and_evidence": _common.AUDIT_AND_EVIDENCE_ENUM_SYMBOLS
    + _audit_and_evidence.MODEL_SYMBOLS,
    "claim_support": _claim_support.MODEL_SYMBOLS,
    "document_artifacts": _document_artifacts.MODEL_SYMBOLS,
    "evaluation_feedback": _evaluation_feedback.MODEL_SYMBOLS,
    "ingest": _common.INGEST_ENUM_SYMBOLS + FACADE_CONSTANT_SYMBOLS + _ingest.MODEL_SYMBOLS,
    "platform": _platform_support.MODEL_SYMBOLS,
    "retrieval": _common.RETRIEVAL_ENUM_SYMBOLS + _retrieval.MODEL_SYMBOLS,
    "semantic_memory": _common.SEMANTIC_MEMORY_ENUM_SYMBOLS + _semantic_memory.MODEL_SYMBOLS,
}
PUBLIC_DB_FACADE_SYMBOL_TO_MODULE = {
    symbol_name: module_name
    for module_name, module_symbols in PUBLIC_DB_FACADE_EXPORT_SYMBOLS.items()
    for symbol_name in module_symbols
}

MODEL_DOMAIN_SYMBOLS = {
    "ingest": _ingest.MODEL_SYMBOLS,
    "document_artifacts": _document_artifacts.MODEL_SYMBOLS,
    "retrieval": _retrieval.MODEL_SYMBOLS,
    "semantic_memory": _semantic_memory.MODEL_SYMBOLS,
    "agent_tasks": _agent_tasks.MODEL_SYMBOLS,
    "audit_and_evidence": _audit_and_evidence.MODEL_SYMBOLS,
    "claim_support": _claim_support.MODEL_SYMBOLS,
    "evaluation_feedback": _evaluation_feedback.MODEL_SYMBOLS,
    "platform_support": _platform_support.MODEL_SYMBOLS,
}

MODEL_SYMBOLS = tuple(
    symbol for domain_symbols in MODEL_DOMAIN_SYMBOLS.values() for symbol in domain_symbols
)

PUBLIC_MODEL_IMPORT_SYMBOLS = ENUM_SYMBOLS + MODEL_SYMBOLS
PUBLIC_DB_MODELS_EXPORT_SYMBOLS = FACADE_CONSTANT_SYMBOLS + PUBLIC_MODEL_IMPORT_SYMBOLS

INGEST_DOMAIN_TABLE_COLUMNS = _ingest.INGEST_DOMAIN_TABLE_COLUMNS
DOCUMENT_ARTIFACT_DOMAIN_TABLE_COLUMNS = _document_artifacts.DOCUMENT_ARTIFACT_DOMAIN_TABLE_COLUMNS
RETRIEVAL_INTERACTION_DOMAIN_TABLE_COLUMNS = _retrieval.RETRIEVAL_INTERACTION_DOMAIN_TABLE_COLUMNS
RETRIEVAL_REPLAY_GOVERNANCE_DOMAIN_TABLE_COLUMNS = (
    _retrieval.RETRIEVAL_REPLAY_GOVERNANCE_DOMAIN_TABLE_COLUMNS
)
RETRIEVAL_LEARNING_DOMAIN_TABLE_COLUMNS = _retrieval.RETRIEVAL_LEARNING_DOMAIN_TABLE_COLUMNS
SEMANTIC_MEMORY_DOMAIN_TABLE_COLUMNS = _semantic_memory.SEMANTIC_MEMORY_DOMAIN_TABLE_COLUMNS
AGENT_TASK_DOMAIN_TABLE_COLUMNS = _agent_tasks.AGENT_TASK_DOMAIN_TABLE_COLUMNS
CLAIM_SUPPORT_DOMAIN_TABLE_COLUMNS = _claim_support.CLAIM_SUPPORT_DOMAIN_TABLE_COLUMNS
AUDIT_AND_EVIDENCE_DOMAIN_TABLE_COLUMNS = (
    _audit_and_evidence.AUDIT_AND_EVIDENCE_DOMAIN_TABLE_COLUMNS
)
EVALUATION_FEEDBACK_DOMAIN_TABLE_COLUMNS = (
    _evaluation_feedback.EVALUATION_FEEDBACK_DOMAIN_TABLE_COLUMNS
)
PLATFORM_SUPPORT_TABLE_COLUMNS = _platform_support.PLATFORM_SUPPORT_TABLE_COLUMNS

EXPECTED_TABLE_NAMES = frozenset(
    {
        *INGEST_DOMAIN_TABLE_COLUMNS,
        *DOCUMENT_ARTIFACT_DOMAIN_TABLE_COLUMNS,
        *RETRIEVAL_INTERACTION_DOMAIN_TABLE_COLUMNS,
        *RETRIEVAL_REPLAY_GOVERNANCE_DOMAIN_TABLE_COLUMNS,
        *RETRIEVAL_LEARNING_DOMAIN_TABLE_COLUMNS,
        *SEMANTIC_MEMORY_DOMAIN_TABLE_COLUMNS,
        *AGENT_TASK_DOMAIN_TABLE_COLUMNS,
        *CLAIM_SUPPORT_DOMAIN_TABLE_COLUMNS,
        *AUDIT_AND_EVIDENCE_DOMAIN_TABLE_COLUMNS,
        *EVALUATION_FEEDBACK_DOMAIN_TABLE_COLUMNS,
        *PLATFORM_SUPPORT_TABLE_COLUMNS,
    }
)

REQUIRED_TABLE_INDEX_NAMES = {
    **_ingest.REQUIRED_TABLE_INDEX_NAMES,
    **_document_artifacts.REQUIRED_TABLE_INDEX_NAMES,
    **_retrieval.REQUIRED_TABLE_INDEX_NAMES,
    **_semantic_memory.REQUIRED_TABLE_INDEX_NAMES,
    **_agent_tasks.REQUIRED_TABLE_INDEX_NAMES,
    **_claim_support.REQUIRED_TABLE_INDEX_NAMES,
    **_audit_and_evidence.REQUIRED_TABLE_INDEX_NAMES,
    **_evaluation_feedback.REQUIRED_TABLE_INDEX_NAMES,
    **_platform_support.REQUIRED_TABLE_INDEX_NAMES,
}
REQUIRED_TABLE_INDEX_COLUMNS = {
    **_ingest.REQUIRED_TABLE_INDEX_COLUMNS,
    **_document_artifacts.REQUIRED_TABLE_INDEX_COLUMNS,
    **_retrieval.REQUIRED_TABLE_INDEX_COLUMNS,
    **_semantic_memory.REQUIRED_TABLE_INDEX_COLUMNS,
    **_agent_tasks.REQUIRED_TABLE_INDEX_COLUMNS,
    **_claim_support.REQUIRED_TABLE_INDEX_COLUMNS,
    **_audit_and_evidence.REQUIRED_TABLE_INDEX_COLUMNS,
    **_evaluation_feedback.REQUIRED_TABLE_INDEX_COLUMNS,
    **_platform_support.REQUIRED_TABLE_INDEX_COLUMNS,
}
REQUIRED_TABLE_UNIQUE_CONSTRAINT_NAMES = {
    **_ingest.REQUIRED_TABLE_UNIQUE_CONSTRAINT_NAMES,
    **_document_artifacts.REQUIRED_TABLE_UNIQUE_CONSTRAINT_NAMES,
    **_retrieval.REQUIRED_TABLE_UNIQUE_CONSTRAINT_NAMES,
    **_semantic_memory.REQUIRED_TABLE_UNIQUE_CONSTRAINT_NAMES,
    **_agent_tasks.REQUIRED_TABLE_UNIQUE_CONSTRAINT_NAMES,
    **_claim_support.REQUIRED_TABLE_UNIQUE_CONSTRAINT_NAMES,
    **_audit_and_evidence.REQUIRED_TABLE_UNIQUE_CONSTRAINT_NAMES,
    **_evaluation_feedback.REQUIRED_TABLE_UNIQUE_CONSTRAINT_NAMES,
    **_platform_support.REQUIRED_TABLE_UNIQUE_CONSTRAINT_NAMES,
}
REQUIRED_TABLE_UNIQUE_CONSTRAINT_COLUMNS = {
    **_ingest.REQUIRED_TABLE_UNIQUE_CONSTRAINT_COLUMNS,
    **_document_artifacts.REQUIRED_TABLE_UNIQUE_CONSTRAINT_COLUMNS,
    **_retrieval.REQUIRED_TABLE_UNIQUE_CONSTRAINT_COLUMNS,
    **_semantic_memory.REQUIRED_TABLE_UNIQUE_CONSTRAINT_COLUMNS,
    **_agent_tasks.REQUIRED_TABLE_UNIQUE_CONSTRAINT_COLUMNS,
    **_claim_support.REQUIRED_TABLE_UNIQUE_CONSTRAINT_COLUMNS,
    **_audit_and_evidence.REQUIRED_TABLE_UNIQUE_CONSTRAINT_COLUMNS,
    **_evaluation_feedback.REQUIRED_TABLE_UNIQUE_CONSTRAINT_COLUMNS,
    **_platform_support.REQUIRED_TABLE_UNIQUE_CONSTRAINT_COLUMNS,
}
REQUIRED_VECTOR_DIMENSIONS = {
    **_ingest.REQUIRED_VECTOR_DIMENSIONS,
    **_document_artifacts.REQUIRED_VECTOR_DIMENSIONS,
    **_retrieval.REQUIRED_VECTOR_DIMENSIONS,
    **_semantic_memory.REQUIRED_VECTOR_DIMENSIONS,
    **_agent_tasks.REQUIRED_VECTOR_DIMENSIONS,
    **_claim_support.REQUIRED_VECTOR_DIMENSIONS,
    **_audit_and_evidence.REQUIRED_VECTOR_DIMENSIONS,
    **_evaluation_feedback.REQUIRED_VECTOR_DIMENSIONS,
    **_platform_support.REQUIRED_VECTOR_DIMENSIONS,
}
REQUIRED_COMPUTED_SQL = {
    **_ingest.REQUIRED_COMPUTED_SQL,
    **_document_artifacts.REQUIRED_COMPUTED_SQL,
    **_retrieval.REQUIRED_COMPUTED_SQL,
    **_semantic_memory.REQUIRED_COMPUTED_SQL,
    **_agent_tasks.REQUIRED_COMPUTED_SQL,
    **_claim_support.REQUIRED_COMPUTED_SQL,
    **_audit_and_evidence.REQUIRED_COMPUTED_SQL,
    **_evaluation_feedback.REQUIRED_COMPUTED_SQL,
    **_platform_support.REQUIRED_COMPUTED_SQL,
}
