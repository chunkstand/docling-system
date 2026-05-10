# Evaluation Data Readiness

Status refreshed: 2026-05-10. The command remains the required preflight before
trusting retrieval, reranker, or court-grade document-generation gates. The
latest run reached local Postgres and reported `regression_ready=true`,
`court_grade_ready=false`, `passed_gate_count=4`, and `failed_gate_count=7`.
The regression tier is now satisfied on the live DB with 26 active documents,
26 completed evaluations, 52 passed evaluation queries, 26 auto-corpus
documents, 26 auto table queries, 25 auto chunk queries, one reviewed manual
seed document in `docs/evaluation_corpus.yaml`, and completed replay coverage
for `evaluation_queries`, `live_search_gaps`, and
`cross_document_prose_regressions` with non-zero replay queries in the latter
two lanes. Court-grade readiness remains intentionally false because the DB
still lacks enough hand-verified gold fixtures, operator feedback,
technical-report claim feedback, governed claim-support hard cases, full replay
and harness source coverage, and retrieval-learning materialization.

Use the data-readiness preflight before trusting retrieval, reranker, or
court-grade document-generation gates. The check is intentionally stricter than
unit/integration tests: it verifies that the live database contains enough
evaluation evidence to make the gates meaningful.

Run:

```bash
uv run docling-system-evaluation-data-readiness
```

Optional report artifact:

```bash
uv run docling-system-evaluation-data-readiness \
  --output storage/evaluation_data_readiness.latest.json
```

The report separates two readiness levels:

- `regression_ready`: enough active documents, persisted run evaluations,
  auto-generated fixtures, and replay-source coverage to detect broad regressions.
- `court_grade_ready`: enough hand-verified gold fixtures, operator feedback,
  technical-report claim feedback, claim-support hard cases, harness-evaluation
  source coverage, and retrieval-learning materialization for auditable gates.

Required data lanes:

- Auto-generated corpus: broad table and chunk recall coverage from ingested data.
- Hand-verified gold corpus: reviewed table, chunk, cross-document, and answer
  fixtures with exact expected evidence.
- Operator feedback: labeled real searches across relevant, irrelevant,
  missing-table, missing-chunk, and no-answer outcomes.
- Technical-report claim feedback: supported, weak, missing, contradicted, and
  rejected claim rows with payload hashes, source search/result/span IDs, evidence
  refs, evidence manifests, PROV artifacts, readiness DB gates, and semantic
  governance links.
- Claim-support replay-alert corpus: active governed hard-case snapshot.
- Replay and harness evaluations: completed replay/evaluation rows for every
  source type, including `technical_report_claim_feedback`.
- Retrieval learning: materialized judgment sets and completed training runs
  built from feedback, replay, and claim-feedback sources.

Current blocker interpretation:

- Empty `regression_blockers` means the live database is ready for broad
  regression detection and replay-backed retrieval checks; that is the Milestone
  6 claim and no broader claim.
- The checked-in manual corpus is now intentionally seeded, not empty. To
  persist manual-fixture evaluation rows, rerun:
  `DOCLING_SYSTEM_MANUAL_EVALUATION_CORPUS_PATH=docs/evaluation_corpus.yaml uv run docling-system-eval-corpus`.
- Remaining `court_grade_blockers` mean the system is not yet ready to claim
  auditable technical-report or claim-support gate readiness.

- Failing `operator_feedback_coverage` means the system needs more real search
  labels before feedback replay can represent operator experience.
- Failing `technical_report_claim_feedback_ledger` means report verification has
  not produced enough claim-level retrieval feedback for court-grade gating.
- Failing `claim_support_replay_alert_corpus` means hard cases have not been
  promoted into a governed active corpus snapshot.
- Failing `retrieval_learning_materialized` means no durable training/evaluation
  dataset exists for reranker promotion.
