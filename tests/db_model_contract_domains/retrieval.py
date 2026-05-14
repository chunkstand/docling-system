"""DB model contract fragment for retrieval."""

from __future__ import annotations

from tests.db_model_contract_domains import (
    retrieval_interactions as _interactions,
)
from tests.db_model_contract_domains import (
    retrieval_learning as _learning,
)
from tests.db_model_contract_domains import (
    retrieval_replay_governance as _replay_governance,
)

MODEL_SYMBOLS = (
    "SearchRequestRecord",
    "SearchRequestResult",
    "RetrievalEvidenceSpan",
    "RetrievalEvidenceSpanMultiVector",
    "SearchRequestResultSpan",
    "SearchFeedback",
    "SearchReplayRun",
    "SearchReplayQuery",
    "SearchHarnessEvaluation",
    "SearchHarnessEvaluationSource",
    "SearchHarnessRelease",
    "SearchHarnessReleaseReadinessAssessment",
    "RetrievalJudgmentSet",
    "RetrievalJudgment",
    "RetrievalHardNegative",
    "RetrievalTrainingRun",
    "RetrievalLearningCandidateEvaluation",
    "RetrievalRerankerArtifact",
    "ChatAnswerRecord",
    "ChatAnswerFeedback",
)

RETRIEVAL_INTERACTION_DOMAIN_TABLE_COLUMNS = _interactions.TABLE_COLUMNS
RETRIEVAL_REPLAY_GOVERNANCE_DOMAIN_TABLE_COLUMNS = _replay_governance.TABLE_COLUMNS
RETRIEVAL_LEARNING_DOMAIN_TABLE_COLUMNS = _learning.TABLE_COLUMNS

REQUIRED_TABLE_INDEX_NAMES = {
    **_interactions.REQUIRED_TABLE_INDEX_NAMES,
    **_replay_governance.REQUIRED_TABLE_INDEX_NAMES,
    **_learning.REQUIRED_TABLE_INDEX_NAMES,
}
REQUIRED_TABLE_INDEX_COLUMNS = {
    **_interactions.REQUIRED_TABLE_INDEX_COLUMNS,
    **_replay_governance.REQUIRED_TABLE_INDEX_COLUMNS,
    **_learning.REQUIRED_TABLE_INDEX_COLUMNS,
}
REQUIRED_TABLE_UNIQUE_CONSTRAINT_NAMES = {
    **_interactions.REQUIRED_TABLE_UNIQUE_CONSTRAINT_NAMES,
    **_replay_governance.REQUIRED_TABLE_UNIQUE_CONSTRAINT_NAMES,
    **_learning.REQUIRED_TABLE_UNIQUE_CONSTRAINT_NAMES,
}
REQUIRED_TABLE_UNIQUE_CONSTRAINT_COLUMNS = {
    **_interactions.REQUIRED_TABLE_UNIQUE_CONSTRAINT_COLUMNS,
    **_replay_governance.REQUIRED_TABLE_UNIQUE_CONSTRAINT_COLUMNS,
    **_learning.REQUIRED_TABLE_UNIQUE_CONSTRAINT_COLUMNS,
}
REQUIRED_VECTOR_DIMENSIONS = {
    **_interactions.REQUIRED_VECTOR_DIMENSIONS,
    **_replay_governance.REQUIRED_VECTOR_DIMENSIONS,
    **_learning.REQUIRED_VECTOR_DIMENSIONS,
}
REQUIRED_COMPUTED_SQL = {
    **_interactions.REQUIRED_COMPUTED_SQL,
    **_replay_governance.REQUIRED_COMPUTED_SQL,
    **_learning.REQUIRED_COMPUTED_SQL,
}
