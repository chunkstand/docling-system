# Evaluation Data Readiness

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

- Failing `operator_feedback_coverage` means the system needs more real search
  labels before feedback replay can represent operator experience.
- Failing `technical_report_claim_feedback_ledger` means report verification has
  not produced enough claim-level retrieval feedback for court-grade gating.
- Failing `claim_support_replay_alert_corpus` means hard cases have not been
  promoted into a governed active corpus snapshot.
- Failing `retrieval_learning_materialized` means no durable training/evaluation
  dataset exists for reranker promotion.
