# Evaluation Data Readiness

Status refreshed: 2026-05-10. The command remains the required preflight before
trusting retrieval, reranker, or court-grade document-generation gates. The
latest run reached local Postgres and reported `regression_ready=true`,
`court_grade_ready=true`, `passed_gate_count=11`, and `failed_gate_count=0`.
The live DB now satisfies both tiers with 26 active documents, 26 completed
evaluations, 52 passed evaluation queries, 26 auto-corpus documents, 26 auto
table queries, 25 auto chunk queries, and a reviewed manual corpus in
`docs/evaluation_corpus.yaml` that contributes 5 documents, 10 table queries,
20 chunk queries, 5 cross-document queries, and 5 answer queries. Court-grade
lanes are now present in the live DB as well: 25 operator-feedback rows across
all required feedback types, 25 technical-report claim-feedback rows across all
required labels and support statuses with no traceability gaps, one active
claim-support replay-alert snapshot with 5 governed rows, completed replay
coverage for `evaluation_queries`, `feedback`, `live_search_gaps`,
`cross_document_prose_regressions`, and `technical_report_claim_feedback`, one
harness-evaluation source row for each required replay source, and one
materialized retrieval-learning judgment/training set with 122 training
examples.

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

Current interpretation:

- Empty `regression_blockers` and empty `court_grade_blockers` mean the live
  database is ready for both broad regression detection and the stricter
  court-grade technical-report and claim-support gates.
- The checked-in manual corpus is intentionally seeded and reviewed. To persist
  manual-fixture evaluation rows into a fresh local database, rerun:
  `DOCLING_SYSTEM_MANUAL_EVALUATION_CORPUS_PATH=docs/evaluation_corpus.yaml uv run docling-system-eval-corpus`.
- Court-grade feedback replay now includes intentional `no_answer` cases. Those
  replays can legitimately produce zero search results, so trace review should
  treat them as expected feedback coverage rather than as replay regressions
  when the replay run otherwise completed successfully.
