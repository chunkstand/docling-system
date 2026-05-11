from __future__ import annotations

from enum import StrEnum

import pytest
from sqlalchemy import UniqueConstraint

import app.db.models as model_module
from app.db.base import Base
from tests.db_model_contract import (
    AGENT_TASK_DOMAIN_TABLE_COLUMNS,
    ALLOWED_DB_MODELS_SUPPORT_SYMBOLS,
    AUDIT_AND_EVIDENCE_DOMAIN_TABLE_COLUMNS,
    CLAIM_SUPPORT_DOMAIN_TABLE_COLUMNS,
    DOCUMENT_ARTIFACT_DOMAIN_TABLE_COLUMNS,
    ENUM_SYMBOLS,
    EVALUATION_FEEDBACK_DOMAIN_TABLE_COLUMNS,
    EXPECTED_TABLE_NAMES,
    FACADE_CONSTANT_SYMBOLS,
    INGEST_DOMAIN_TABLE_COLUMNS,
    MODEL_DOMAIN_SYMBOLS,
    MODEL_SYMBOLS,
    PUBLIC_DB_MODELS_EXPORT_SYMBOLS,
    PUBLIC_MODEL_IMPORT_SYMBOLS,
    REQUIRED_COMPUTED_SQL,
    REQUIRED_TABLE_INDEX_COLUMNS,
    REQUIRED_TABLE_INDEX_NAMES,
    REQUIRED_TABLE_UNIQUE_CONSTRAINT_COLUMNS,
    REQUIRED_TABLE_UNIQUE_CONSTRAINT_NAMES,
    REQUIRED_VECTOR_DIMENSIONS,
    RETRIEVAL_INTERACTION_DOMAIN_TABLE_COLUMNS,
    RETRIEVAL_LEARNING_DOMAIN_TABLE_COLUMNS,
    RETRIEVAL_REPLAY_GOVERNANCE_DOMAIN_TABLE_COLUMNS,
    SEMANTIC_MEMORY_DOMAIN_TABLE_COLUMNS,
)


@pytest.mark.parametrize("symbol_name", PUBLIC_MODEL_IMPORT_SYMBOLS)
def test_public_model_symbol_remains_importable(symbol_name: str) -> None:
    module = __import__("app.db.models", fromlist=[symbol_name])

    symbol = getattr(module, symbol_name)

    assert symbol.__name__ == symbol_name


@pytest.mark.parametrize("symbol_name", FACADE_CONSTANT_SYMBOLS)
def test_public_model_constant_remains_importable(symbol_name: str) -> None:
    module = __import__("app.db.models", fromlist=[symbol_name])

    symbol = getattr(module, symbol_name)

    assert isinstance(symbol, str)
    assert symbol


@pytest.mark.parametrize("symbol_name", ENUM_SYMBOLS)
def test_public_model_enum_remains_str_enum(symbol_name: str) -> None:
    symbol = getattr(model_module, symbol_name)

    assert issubclass(symbol, StrEnum)


@pytest.mark.parametrize("symbol_name", MODEL_SYMBOLS)
def test_public_model_class_remains_registered_orm_model(symbol_name: str) -> None:
    symbol = getattr(model_module, symbol_name)

    assert issubclass(symbol, Base)
    assert symbol.__table__.name in EXPECTED_TABLE_NAMES
    assert symbol.__table__ is Base.metadata.tables[symbol.__table__.name]


def test_public_model_domain_contract_is_complete() -> None:
    assert len(MODEL_SYMBOLS) == 80
    assert len(set(MODEL_SYMBOLS)) == len(MODEL_SYMBOLS)
    assert len(PUBLIC_MODEL_IMPORT_SYMBOLS) == 109
    assert len(FACADE_CONSTANT_SYMBOLS) == 2
    assert len(PUBLIC_DB_MODELS_EXPORT_SYMBOLS) == 111
    assert set(MODEL_DOMAIN_SYMBOLS) == {
        "agent_tasks",
        "audit_and_evidence",
        "claim_support",
        "document_artifacts",
        "evaluation_feedback",
        "ingest",
        "platform_support",
        "retrieval",
        "semantic_memory",
    }
    assert ALLOWED_DB_MODELS_SUPPORT_SYMBOLS == ("annotations",)


def test_platform_support_model_is_owned_by_domain_module() -> None:
    from app.db.model_domains.platform import ApiIdempotencyKey

    assert model_module.ApiIdempotencyKey is ApiIdempotencyKey
    assert model_module.ApiIdempotencyKey.__module__ == "app.db.model_domains.platform"


def test_ingest_models_are_owned_by_domain_module() -> None:
    from app.db.model_domains.ingest import Document, DocumentRun, IngestBatch, IngestBatchItem

    expected_models = {
        "Document": Document,
        "DocumentRun": DocumentRun,
        "IngestBatch": IngestBatch,
        "IngestBatchItem": IngestBatchItem,
    }

    for model_name, domain_model in expected_models.items():
        assert getattr(model_module, model_name) is domain_model
        assert domain_model.__module__ == "app.db.model_domains.ingest"


def test_document_artifact_models_are_owned_by_domain_module() -> None:
    from app.db.model_domains.document_artifacts import (
        DocumentChunk,
        DocumentFigure,
        DocumentRunEvaluation,
        DocumentRunEvaluationQuery,
        DocumentTable,
        DocumentTableSegment,
    )

    expected_models = {
        "DocumentRunEvaluation": DocumentRunEvaluation,
        "DocumentRunEvaluationQuery": DocumentRunEvaluationQuery,
        "DocumentChunk": DocumentChunk,
        "DocumentTable": DocumentTable,
        "DocumentTableSegment": DocumentTableSegment,
        "DocumentFigure": DocumentFigure,
    }

    for model_name, domain_model in expected_models.items():
        assert getattr(model_module, model_name) is domain_model
        assert domain_model.__module__ == "app.db.model_domains.document_artifacts"


def test_retrieval_interaction_models_are_owned_by_domain_module() -> None:
    from app.db.model_domains.retrieval_interactions import (
        ChatAnswerFeedback,
        ChatAnswerRecord,
        RetrievalEvidenceSpan,
        RetrievalEvidenceSpanMultiVector,
        SearchFeedback,
        SearchRequestRecord,
        SearchRequestResult,
        SearchRequestResultSpan,
    )

    expected_models = {
        "SearchRequestRecord": SearchRequestRecord,
        "SearchRequestResult": SearchRequestResult,
        "RetrievalEvidenceSpan": RetrievalEvidenceSpan,
        "RetrievalEvidenceSpanMultiVector": RetrievalEvidenceSpanMultiVector,
        "SearchRequestResultSpan": SearchRequestResultSpan,
        "SearchFeedback": SearchFeedback,
        "ChatAnswerRecord": ChatAnswerRecord,
        "ChatAnswerFeedback": ChatAnswerFeedback,
    }

    for model_name, domain_model in expected_models.items():
        assert getattr(model_module, model_name) is domain_model
        assert domain_model.__module__ == "app.db.model_domains.retrieval_interactions"


def test_retrieval_replay_governance_models_are_owned_by_domain_module() -> None:
    from app.db.model_domains.retrieval_replay_governance import (
        SearchHarnessEvaluation,
        SearchHarnessEvaluationSource,
        SearchHarnessRelease,
        SearchHarnessReleaseReadinessAssessment,
        SearchReplayQuery,
        SearchReplayRun,
    )

    expected_models = {
        "SearchReplayRun": SearchReplayRun,
        "SearchReplayQuery": SearchReplayQuery,
        "SearchHarnessEvaluation": SearchHarnessEvaluation,
        "SearchHarnessEvaluationSource": SearchHarnessEvaluationSource,
        "SearchHarnessRelease": SearchHarnessRelease,
        "SearchHarnessReleaseReadinessAssessment": SearchHarnessReleaseReadinessAssessment,
    }

    for model_name, domain_model in expected_models.items():
        assert getattr(model_module, model_name) is domain_model
        assert domain_model.__module__ == "app.db.model_domains.retrieval_replay_governance"


def test_retrieval_learning_example_models_are_owned_by_domain_module() -> None:
    from app.db.model_domains.retrieval_learning_examples import (
        RetrievalHardNegative,
        RetrievalJudgment,
        RetrievalJudgmentSet,
    )

    expected_models = {
        "RetrievalJudgmentSet": RetrievalJudgmentSet,
        "RetrievalJudgment": RetrievalJudgment,
        "RetrievalHardNegative": RetrievalHardNegative,
    }

    for model_name, domain_model in expected_models.items():
        assert getattr(model_module, model_name) is domain_model
        assert domain_model.__module__ == "app.db.model_domains.retrieval_learning_examples"


def test_retrieval_learning_artifact_models_are_owned_by_domain_module() -> None:
    from app.db.model_domains.retrieval_learning_artifacts import (
        RetrievalLearningCandidateEvaluation,
        RetrievalRerankerArtifact,
        RetrievalTrainingRun,
    )

    expected_models = {
        "RetrievalTrainingRun": RetrievalTrainingRun,
        "RetrievalLearningCandidateEvaluation": RetrievalLearningCandidateEvaluation,
        "RetrievalRerankerArtifact": RetrievalRerankerArtifact,
    }

    for model_name, domain_model in expected_models.items():
        assert getattr(model_module, model_name) is domain_model
        assert domain_model.__module__ == "app.db.model_domains.retrieval_learning_artifacts"


def test_evaluation_feedback_models_are_owned_by_domain_module() -> None:
    from app.db.model_domains.evaluation_feedback import EvalFailureCase, EvalObservation

    expected_models = {
        "EvalObservation": EvalObservation,
        "EvalFailureCase": EvalFailureCase,
    }

    for model_name, domain_model in expected_models.items():
        assert getattr(model_module, model_name) is domain_model
        assert domain_model.__module__ == "app.db.model_domains.evaluation_feedback"


def test_claim_support_models_are_owned_by_domain_module() -> None:
    from app.db.model_domains.claim_support import (
        ClaimSupportCalibrationPolicy,
        ClaimSupportEvaluation,
        ClaimSupportEvaluationCase,
        ClaimSupportFixtureSet,
        ClaimSupportPolicyChangeImpact,
        ClaimSupportReplayAlertFixtureCorpusRow,
        ClaimSupportReplayAlertFixtureCorpusSnapshot,
        ClaimSupportReplayAlertFixtureCoverageWaiverEscalation,
        ClaimSupportReplayAlertFixtureCoverageWaiverLedger,
    )

    expected_models = {
        "ClaimSupportReplayAlertFixtureCoverageWaiverLedger": (
            ClaimSupportReplayAlertFixtureCoverageWaiverLedger
        ),
        "ClaimSupportReplayAlertFixtureCoverageWaiverEscalation": (
            ClaimSupportReplayAlertFixtureCoverageWaiverEscalation
        ),
        "ClaimSupportFixtureSet": ClaimSupportFixtureSet,
        "ClaimSupportReplayAlertFixtureCorpusSnapshot": (
            ClaimSupportReplayAlertFixtureCorpusSnapshot
        ),
        "ClaimSupportReplayAlertFixtureCorpusRow": ClaimSupportReplayAlertFixtureCorpusRow,
        "ClaimSupportCalibrationPolicy": ClaimSupportCalibrationPolicy,
        "ClaimSupportEvaluation": ClaimSupportEvaluation,
        "ClaimSupportEvaluationCase": ClaimSupportEvaluationCase,
        "ClaimSupportPolicyChangeImpact": ClaimSupportPolicyChangeImpact,
    }

    for model_name, domain_model in expected_models.items():
        assert getattr(model_module, model_name) is domain_model
        assert domain_model.__module__ == "app.db.model_domains.claim_support"


def test_semantic_memory_models_are_owned_by_domain_module() -> None:
    from app.db.model_domains.semantic_memory import (
        DocumentRunSemanticPass,
        DocumentSemanticCategoryReview,
        DocumentSemanticConceptReview,
        SemanticAssertion,
        SemanticAssertionCategoryBinding,
        SemanticAssertionEvidence,
        SemanticCategory,
        SemanticConcept,
        SemanticConceptCategoryBinding,
        SemanticConceptTerm,
        SemanticEntity,
        SemanticFact,
        SemanticFactEvidence,
        SemanticGovernanceEvent,
        SemanticGraphSnapshot,
        SemanticOntologySnapshot,
        SemanticTerm,
        WorkspaceSemanticGraphState,
        WorkspaceSemanticState,
    )

    expected_models = {
        "SemanticOntologySnapshot": SemanticOntologySnapshot,
        "WorkspaceSemanticState": WorkspaceSemanticState,
        "SemanticGraphSnapshot": SemanticGraphSnapshot,
        "WorkspaceSemanticGraphState": WorkspaceSemanticGraphState,
        "SemanticConcept": SemanticConcept,
        "SemanticCategory": SemanticCategory,
        "SemanticTerm": SemanticTerm,
        "SemanticConceptTerm": SemanticConceptTerm,
        "SemanticConceptCategoryBinding": SemanticConceptCategoryBinding,
        "DocumentSemanticConceptReview": DocumentSemanticConceptReview,
        "DocumentSemanticCategoryReview": DocumentSemanticCategoryReview,
        "DocumentRunSemanticPass": DocumentRunSemanticPass,
        "SemanticAssertion": SemanticAssertion,
        "SemanticAssertionCategoryBinding": SemanticAssertionCategoryBinding,
        "SemanticAssertionEvidence": SemanticAssertionEvidence,
        "SemanticEntity": SemanticEntity,
        "SemanticFact": SemanticFact,
        "SemanticFactEvidence": SemanticFactEvidence,
        "SemanticGovernanceEvent": SemanticGovernanceEvent,
    }

    for model_name, domain_model in expected_models.items():
        assert getattr(model_module, model_name) is domain_model
        assert domain_model.__module__ == "app.db.model_domains.semantic_memory"


def test_agent_task_models_are_owned_by_domain_module() -> None:
    from app.db.model_domains.agent_tasks import (
        AgentTask,
        AgentTaskArtifact,
        AgentTaskArtifactImmutabilityEvent,
        AgentTaskAttempt,
        AgentTaskDependency,
        AgentTaskOutcome,
        AgentTaskVerification,
        KnowledgeOperatorInput,
        KnowledgeOperatorOutput,
        KnowledgeOperatorRun,
    )

    expected_models = {
        "AgentTask": AgentTask,
        "AgentTaskDependency": AgentTaskDependency,
        "AgentTaskAttempt": AgentTaskAttempt,
        "AgentTaskArtifact": AgentTaskArtifact,
        "AgentTaskArtifactImmutabilityEvent": AgentTaskArtifactImmutabilityEvent,
        "AgentTaskOutcome": AgentTaskOutcome,
        "AgentTaskVerification": AgentTaskVerification,
        "KnowledgeOperatorRun": KnowledgeOperatorRun,
        "KnowledgeOperatorInput": KnowledgeOperatorInput,
        "KnowledgeOperatorOutput": KnowledgeOperatorOutput,
    }

    for model_name, domain_model in expected_models.items():
        assert getattr(model_module, model_name) is domain_model
        assert domain_model.__module__ == "app.db.model_domains.agent_tasks"


def test_audit_and_evidence_models_are_owned_by_domain_module() -> None:
    from app.db.model_domains.audit_and_evidence import (
        AuditBundleExport,
        AuditBundleValidationReceipt,
        ClaimEvidenceDerivation,
        EvidenceManifest,
        EvidencePackageExport,
        EvidenceTraceEdge,
        EvidenceTraceNode,
        TechnicalReportClaimRetrievalFeedback,
        TechnicalReportReleaseReadinessDbGate,
    )

    expected_models = {
        "AuditBundleExport": AuditBundleExport,
        "AuditBundleValidationReceipt": AuditBundleValidationReceipt,
        "EvidencePackageExport": EvidencePackageExport,
        "EvidenceManifest": EvidenceManifest,
        "TechnicalReportReleaseReadinessDbGate": TechnicalReportReleaseReadinessDbGate,
        "TechnicalReportClaimRetrievalFeedback": TechnicalReportClaimRetrievalFeedback,
        "EvidenceTraceNode": EvidenceTraceNode,
        "EvidenceTraceEdge": EvidenceTraceEdge,
        "ClaimEvidenceDerivation": ClaimEvidenceDerivation,
    }

    for model_name, domain_model in expected_models.items():
        assert getattr(model_module, model_name) is domain_model
        assert domain_model.__module__ == "app.db.model_domains.audit_and_evidence"


def test_base_metadata_table_contract_is_complete() -> None:
    assert frozenset(Base.metadata.tables) == EXPECTED_TABLE_NAMES


@pytest.mark.parametrize(
    ("table_name", "expected_columns"),
    INGEST_DOMAIN_TABLE_COLUMNS.items(),
)
def test_base_metadata_preserves_ingest_domain_table_columns(
    table_name: str, expected_columns: frozenset[str]
) -> None:
    table = Base.metadata.tables[table_name]

    assert frozenset(table.columns.keys()) == expected_columns


@pytest.mark.parametrize(
    ("table_name", "expected_columns"),
    DOCUMENT_ARTIFACT_DOMAIN_TABLE_COLUMNS.items(),
)
def test_base_metadata_preserves_document_artifact_domain_table_columns(
    table_name: str, expected_columns: frozenset[str]
) -> None:
    table = Base.metadata.tables[table_name]

    assert frozenset(table.columns.keys()) == expected_columns


@pytest.mark.parametrize(
    ("table_name", "expected_columns"),
    RETRIEVAL_INTERACTION_DOMAIN_TABLE_COLUMNS.items(),
)
def test_base_metadata_preserves_retrieval_interaction_domain_table_columns(
    table_name: str, expected_columns: frozenset[str]
) -> None:
    table = Base.metadata.tables[table_name]

    assert frozenset(table.columns.keys()) == expected_columns


@pytest.mark.parametrize(
    ("table_name", "expected_columns"),
    RETRIEVAL_REPLAY_GOVERNANCE_DOMAIN_TABLE_COLUMNS.items(),
)
def test_base_metadata_preserves_retrieval_replay_governance_domain_table_columns(
    table_name: str, expected_columns: frozenset[str]
) -> None:
    table = Base.metadata.tables[table_name]

    assert frozenset(table.columns.keys()) == expected_columns


@pytest.mark.parametrize(
    ("table_name", "expected_columns"),
    RETRIEVAL_LEARNING_DOMAIN_TABLE_COLUMNS.items(),
)
def test_base_metadata_preserves_retrieval_learning_domain_table_columns(
    table_name: str, expected_columns: frozenset[str]
) -> None:
    table = Base.metadata.tables[table_name]

    assert frozenset(table.columns.keys()) == expected_columns


@pytest.mark.parametrize(
    ("table_name", "expected_columns"),
    EVALUATION_FEEDBACK_DOMAIN_TABLE_COLUMNS.items(),
)
def test_base_metadata_preserves_evaluation_feedback_domain_table_columns(
    table_name: str, expected_columns: frozenset[str]
) -> None:
    table = Base.metadata.tables[table_name]

    assert frozenset(table.columns.keys()) == expected_columns


@pytest.mark.parametrize(
    ("table_name", "expected_columns"),
    CLAIM_SUPPORT_DOMAIN_TABLE_COLUMNS.items(),
)
def test_base_metadata_preserves_claim_support_domain_table_columns(
    table_name: str, expected_columns: frozenset[str]
) -> None:
    table = Base.metadata.tables[table_name]

    assert frozenset(table.columns.keys()) == expected_columns


@pytest.mark.parametrize(
    ("table_name", "expected_columns"),
    SEMANTIC_MEMORY_DOMAIN_TABLE_COLUMNS.items(),
)
def test_base_metadata_preserves_semantic_memory_domain_table_columns(
    table_name: str, expected_columns: frozenset[str]
) -> None:
    table = Base.metadata.tables[table_name]

    assert frozenset(table.columns.keys()) == expected_columns


@pytest.mark.parametrize(
    ("table_name", "expected_columns"),
    AGENT_TASK_DOMAIN_TABLE_COLUMNS.items(),
)
def test_base_metadata_preserves_agent_task_domain_table_columns(
    table_name: str, expected_columns: frozenset[str]
) -> None:
    table = Base.metadata.tables[table_name]

    assert frozenset(table.columns.keys()) == expected_columns


@pytest.mark.parametrize(
    ("table_name", "expected_columns"),
    AUDIT_AND_EVIDENCE_DOMAIN_TABLE_COLUMNS.items(),
)
def test_base_metadata_preserves_audit_and_evidence_domain_table_columns(
    table_name: str, expected_columns: frozenset[str]
) -> None:
    table = Base.metadata.tables[table_name]

    assert frozenset(table.columns.keys()) == expected_columns


@pytest.mark.parametrize(
    ("table_name", "expected_index_names"),
    REQUIRED_TABLE_INDEX_NAMES.items(),
)
def test_base_metadata_preserves_required_indexes(
    table_name: str, expected_index_names: frozenset[str]
) -> None:
    table = Base.metadata.tables[table_name]

    assert {index.name for index in table.indexes} >= expected_index_names


@pytest.mark.parametrize(
    ("table_name", "index_columns_by_name"),
    REQUIRED_TABLE_INDEX_COLUMNS.items(),
)
def test_base_metadata_preserves_required_index_columns(
    table_name: str, index_columns_by_name: dict[str, tuple[str, ...]]
) -> None:
    table = Base.metadata.tables[table_name]
    indexes_by_name = {index.name: index for index in table.indexes}

    for index_name, expected_columns in index_columns_by_name.items():
        index = indexes_by_name[index_name]
        assert tuple(column.name for column in index.columns) == expected_columns


@pytest.mark.parametrize(
    ("table_name", "expected_constraint_names"),
    REQUIRED_TABLE_UNIQUE_CONSTRAINT_NAMES.items(),
)
def test_base_metadata_preserves_required_unique_constraints(
    table_name: str, expected_constraint_names: frozenset[str]
) -> None:
    table = Base.metadata.tables[table_name]
    unique_constraint_names = {
        constraint.name
        for constraint in table.constraints
        if isinstance(constraint, UniqueConstraint)
    }

    assert unique_constraint_names >= expected_constraint_names


@pytest.mark.parametrize(
    ("table_name", "constraint_columns_by_name"),
    REQUIRED_TABLE_UNIQUE_CONSTRAINT_COLUMNS.items(),
)
def test_base_metadata_preserves_required_unique_constraint_columns(
    table_name: str, constraint_columns_by_name: dict[str, tuple[str, ...]]
) -> None:
    table = Base.metadata.tables[table_name]
    unique_constraints_by_name = {
        constraint.name: constraint
        for constraint in table.constraints
        if isinstance(constraint, UniqueConstraint)
    }

    for constraint_name, expected_columns in constraint_columns_by_name.items():
        constraint = unique_constraints_by_name[constraint_name]
        assert tuple(column.name for column in constraint.columns) == expected_columns


@pytest.mark.parametrize(
    ("table_name", "vector_columns"),
    REQUIRED_VECTOR_DIMENSIONS.items(),
)
def test_base_metadata_preserves_required_vector_dimensions(
    table_name: str, vector_columns: dict[str, int]
) -> None:
    table = Base.metadata.tables[table_name]

    for column_name, expected_dim in vector_columns.items():
        assert getattr(table.columns[column_name].type, "dim", None) == expected_dim


@pytest.mark.parametrize(
    ("table_name", "computed_sql_by_column"),
    REQUIRED_COMPUTED_SQL.items(),
)
def test_base_metadata_preserves_required_computed_sql(
    table_name: str, computed_sql_by_column: dict[str, str]
) -> None:
    table = Base.metadata.tables[table_name]

    for column_name, expected_sql in computed_sql_by_column.items():
        column = table.columns[column_name]
        assert column.computed is not None
        assert column.computed.persisted is True
        assert str(column.computed.sqltext) == expected_sql
