# Evaluation Data Readiness

Status refreshed: 2026-05-20. A fresh empty local checkout can now
deterministically reach both readiness levels through two tracked bootstrap
commands:

```bash
uv run docling-system-bootstrap-regression-readiness
uv run docling-system-bootstrap-court-grade-readiness
```

The regression bootstrap installs the tracked auto-corpus seed from
`docs/evaluation_corpus.auto.bootstrap.yaml` into
`storage/evaluation_corpus.auto.yaml`, seeds one zero-result live gap, ingests
and promotes `docs/evaluation_bootstrap/regression_doc_03.pdf`, runs the
manual reviewed evaluation from `docs/evaluation_corpus.yaml`, executes the
minimum replay trio (`evaluation_queries`, `live_search_gaps`,
`cross_document_prose_regressions`), and writes the standard report to
`storage/evaluation_data_readiness.latest.json`. The command refuses to run on
a non-empty DB so the outcome stays deterministic.

The court-grade bootstrap requires that exact regression-only baseline. It
seeds the missing operator-feedback, technical-report claim-feedback, and
governed replay-alert rows from tracked bootstrap YAML, runs the missing
`feedback` and `technical_report_claim_feedback` replay suites, persists a
harness evaluation covering every required source type, materializes
retrieval-learning rows, rewrites
`storage/evaluation_data_readiness.latest.json`, and refuses empty,
already-ready, or mixed advanced DB state.

Regression-step baseline result on 2026-05-20:

- `regression_ready=true`
- `court_grade_ready=false`
- `passed_gate_count=5`
- `failed_gate_count=6`
- live DB counts: `1` active document, `2` completed evaluations, `10`
  persisted evaluation queries
- replay coverage: `evaluation_queries=7`, `live_search_gaps=1`,
  `cross_document_prose_regressions=2`

This closes the reproducibility debt for the regression lane. The later
2026-05-20 replay-quality follow-on also fixed the reviewed
`mesa restoration outlook distinct prose recall` miss, refreshed the latest
manual evaluation to `8 / 8` with
`DOCLING_SYSTEM_MANUAL_EVALUATION_CORPUS_PATH=docs/evaluation_corpus.yaml uv run docling-system-eval-corpus`,
and brought the `evaluation_queries` replay back to `7 / 7`. The current live
repo DB therefore keeps the rebuildable readiness gate and the reviewed
search-quality lane aligned instead of leaving a known miss behind.

Focused Postgres-backed verification of the full two-step chain on 2026-05-20:

- `env DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest tests/integration/test_regression_readiness_bootstrap.py tests/integration/test_court_grade_readiness_bootstrap.py -q` passed at `3 passed`
- The verified court-grade step created `25` operator-feedback rows, `25`
  technical-report claim-feedback rows, `1` active governed replay-alert
  snapshot with `5` rows, persisted all required harness source types, and
  closed the readiness report with `court_grade_ready=true` and
  `failed_gate_count=0`
- Live local closeout on the current repo DB also passed:
  `uv run docling-system-bootstrap-court-grade-readiness --compact` succeeded,
  and `uv run docling-system-evaluation-data-readiness --output storage/evaluation_data_readiness.latest.json`
  now reports `passed_gate_count=11` and `failed_gate_count=0`.
- `uv run docling-system-agent-trace-review --limit 5 --skip-hygiene`
  now reports `observation_count=0` after the replay-quality follow-on
  separates intentional learning-suite failures from actionable regressions and
  closes the reviewed `evaluation_queries` miss.

Use the data-readiness preflight before trusting retrieval, reranker, or
court-grade document-generation gates. The check is intentionally stricter than
unit/integration tests: it verifies that the live database contains enough
evaluation evidence to make the gates meaningful.

Bootstrap first when the checkout is empty:

```bash
uv run docling-system-bootstrap-regression-readiness
```

Then close the court-grade blockers from that strict baseline:

```bash
uv run docling-system-bootstrap-court-grade-readiness
```

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

- Empty `regression_blockers` means the live database has enough active runs,
  persisted evaluations, auto-corpus coverage, and basic replay coverage to
  make the regression gate meaningful.
- Empty `court_grade_blockers` means the stricter operator-feedback,
  claim-feedback, replay-alert, harness-evaluation, and retrieval-learning lanes
  are present as well.
- The checked-in manual corpus is intentionally seeded and reviewed. The new
  bootstrap command is now the canonical way to persist manual-fixture
  evaluation rows plus the minimum replay trio into a fresh local database.
- Court-grade feedback replay now includes intentional `no_answer`,
  contradicted, and other negative cases. Those rows are required for readiness
  coverage, and the trace-review pass now filters those intentional failed-case
  suites away from actionable replay regressions.
