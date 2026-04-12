# Session Handoff

Date: 2026-04-12 local / 2026-04-12 UTC verification
Project: `/Users/chunkstand/Documents/docling-system`
Branch: `codex/docling-system-build`
Remote: `origin -> https://github.com/chunkstand/docling-system.git`
PR: `#1` `Build docling-system v1 ingestion, retrieval, evaluation, and run audit surfaces`
PR URL: `https://github.com/chunkstand/docling-system/pull/1`
Latest committed checkpoint before this handoff update: `de4f123` (`Close replay UI and docs gaps`)

## Executive Summary

The branch now includes:

- Lopopolo milestone 2 quality surfaces
- legacy audit-field backfill so historical rows satisfy the current audit contract
- persisted search-request telemetry, feedback labels, replay suites, replay comparison, and ranking-dataset export
- a replay/quality operator UI that now exposes both replay execution and replay comparison controls
- Milestone 5 learned-reranking harness infrastructure with named search harnesses, harness evaluations, answer-feedback capture, and replay drilldown
- a green live `docling-system-audit` result after migration `0012_harness_chat_feedback`

What is now true:

- validation still gates promotion
- evaluation still does not gate promotion
- search requests are durable first-class records
- chat answers are durable first-class records with operator feedback
- search requests, replay runs, and chat answers now all carry harness metadata when available
- replay and trend surfaces exist in both the API and the operator UI
- named search harnesses can be replayed and compared through both the API and the CLI
- the local corpus passes the current audit contract live

## What Landed Recently

### 1. Lopopolo Milestone 2

Commit:

- `0e41420` `Implement Lopopolo milestone 2 quality surfaces`

What changed:

- expanded `docling-system-audit` in `app/services/audit.py`
- added quality aggregation in `app/services/quality.py`
- added quality schemas in `app/schemas/quality.py`
- added:
  - `GET /quality/summary`
  - `GET /quality/failures`
  - `GET /quality/evaluations`
- added a quality panel to the UI

### 2. Legacy Audit Backfill

Commit:

- `5e98907` `Backfill legacy audit fields`

What changed:

- added reusable backfill logic in `app/services/cleanup.py`
- added CLI `docling-system-backfill-legacy-audit`
- normalized historical `figure_count` and `failure_stage` drift

Durable result:

- live `docling-system-audit` returned zero violations after the backfill

### 3. Retrieval Feedback And Replay Lab

Commit:

- `ce4da3f` `Add search feedback and replay lab`

What changed:

- added durable replay/feedback persistence in:
  - `app/db/models.py`
  - `alembic/versions/0011_search_feedback_replays.py`
- added replay and dataset services in:
  - `app/services/search_history.py`
  - `app/services/search_replays.py`
  - `app/services/quality.py`
- added API routes in `app/api/main.py`:
  - `POST /search/requests/{search_request_id}/feedback`
  - `GET /search/replays`
  - `POST /search/replays`
  - `GET /search/replays/{replay_run_id}`
  - `GET /search/replays/compare`
  - `GET /quality/trends`
- added CLI commands:
  - `uv run docling-system-run-replay-suite <source_type> --limit N`
  - `uv run docling-system-export-ranking-dataset --limit N`
- updated the UI to show:
  - search feedback labels
  - replay-run history
  - replay execution controls
  - replay comparison controls
  - search and feedback trend summaries

Relevant files:

- `app/api/main.py`
- `app/cli.py`
- `app/db/models.py`
- `app/schemas/search.py`
- `app/schemas/quality.py`
- `app/services/search_history.py`
- `app/services/search_replays.py`
- `app/services/quality.py`
- `app/ui/index.html`
- `app/ui/app.js`
- `app/ui/styles.css`
- `README.md`
- `tests/unit/test_search_api.py`
- `tests/unit/test_search_replays.py`
- `tests/unit/test_quality_api.py`
- `tests/unit/test_quality_service.py`
- `tests/unit/test_cli.py`
- `tests/unit/test_ui.py`

### 4. Gap-Closing Follow-Up

This handoff update also closes the post-milestone gaps that were still open after `ce4da3f`:

- the UI now exposes replay creation and replay comparison instead of only listing replay runs
- `README.md` now documents the replay/feedback endpoints and CLI commands
- this handoff reflects the current migration head and runtime state instead of the older milestone-2 state

### 5. Learned Reranking Harness

Uncommitted changes captured by this handoff update:

- versioned search harnesses now wrap:
  - retrieval profile
  - reranker name and version
  - persisted harness config snapshots on direct searches and replay runs
- chat answers are now persisted with:
  - `chat_answer_id`
  - `search_request_id`
  - harness metadata
  - durable answer-feedback labels
- new API routes in `app/api/main.py`:
  - `GET /search/harnesses`
  - `POST /search/harness-evaluations`
  - `POST /chat/answers/{chat_answer_id}/feedback`
- new CLI command:
  - `uv run docling-system-eval-reranker <candidate_harness_name> --baseline-harness-name <name> --limit N`
- the operator UI now exposes:
  - harness selectors on direct search, replay creation, and chat
  - replay drilldown
  - answer-feedback actions
- dataset export is now documented in `docs/ranking_dataset_schema.md`

Relevant files:

- `app/api/main.py`
- `app/cli.py`
- `app/db/models.py`
- `app/schemas/chat.py`
- `app/schemas/search.py`
- `app/schemas/quality.py`
- `app/services/chat.py`
- `app/services/search.py`
- `app/services/search_history.py`
- `app/services/search_replays.py`
- `app/services/search_harness_evaluations.py`
- `app/services/quality.py`
- `app/ui/index.html`
- `app/ui/app.js`
- `app/ui/styles.css`
- `alembic/versions/0012_harness_chat_feedback.py`
- `docs/ranking_dataset_schema.md`
- `README.md`
- `tests/unit/test_chat_api.py`
- `tests/unit/test_chat_service.py`
- `tests/unit/test_search_api.py`
- `tests/unit/test_search_harness_evaluations.py`
- `tests/unit/test_search_replays.py`
- `tests/unit/test_search_service.py`
- `tests/unit/test_quality_api.py`
- `tests/unit/test_quality_service.py`
- `tests/unit/test_cli.py`
- `tests/unit/test_ui.py`

## Current Runtime State

At handoff time:

- API health check succeeds at `http://127.0.0.1:8000/health`
- the API was restarted after the `0012_harness_chat_feedback` migration
- the worker was restarted after the same migration
- Alembic head in the running database is `0012_harness_chat_feedback`
- `docling-system-audit` completes live with zero violations
- the active/evaluated corpus remains eight documents

Live audit result:

```json
{
  "checked_documents": 8,
  "checked_runs": 27,
  "checked_evaluations": 14,
  "checked_tables": 481,
  "checked_figures": 344,
  "violation_count": 0,
  "violation_counts_by_code": {},
  "violations": []
}
```

Recent live replay/feedback verification:

- `GET /search/harnesses` returns `default_v1` and `wide_v2` with persisted config snapshots
- `POST /search` with `harness_name = "wide_v2"` returns `X-Search-Request-Id`
- persisted request detail includes:
  - harness metadata
  - retrieval profile metadata
  - rerank feature snapshots
- persisted direct search requests return `X-Search-Request-Id`
- request detail includes persisted rerank features and feedback labels
- `POST /search/requests/{id}/feedback` persists both ranked-result feedback and request-level `no_answer`
- `POST /chat` now returns:
  - `chat_answer_id`
  - `search_request_id`
  - harness metadata
- `POST /chat/answers/{id}/feedback` persists answer-level feedback live
- `POST /search/replays` succeeded for `feedback` and `live_search_gaps`
- `GET /search/replays/compare` returned shared-query regression/improvement summaries
- `GET /search/replays/{id}` returns replay drilldown rows with harness metadata
- `POST /search/harness-evaluations` completed live for `default_v1` vs `wide_v2`
- `GET /quality/trends` now includes `answer_feedback_counts`
- `uv run docling-system-run-replay-suite feedback --limit 3` completed live
- `uv run docling-system-eval-reranker wide_v2 --baseline-harness-name default_v1 --limit 3` completed live
- `uv run docling-system-export-ranking-dataset --limit 5` emitted feedback and replay rows live

## Active Corpus State

Current active/evaluated set:

- `UPC_CH_5.pdf` -> fixture `upc_ch5`
- `UPC_CH_4.pdf` -> fixture `upc_ch4`
- `UPC_Appendix_N.pdf` -> fixture `born_digital_simple`
- `UPC_Appendix_B.pdf` -> fixture `appendix_b_prose_guidance`
- `UPC_CH_3.pdf` -> fixture `awkward_headers`
- `UPC_Ch_2.pdf` -> fixture `upc_ch2_figures`
- `UPC_CH_7.pdf` -> fixture `upc_ch7`
- `UPC_CH_1.pdf` -> fixture `prose_control`

## Verification Performed

Commands run and observed passing recently:

```bash
uv run ruff check app/api/main.py app/cli.py app/db/models.py app/schemas/chat.py app/schemas/search.py app/schemas/quality.py app/services/chat.py app/services/search.py app/services/search_history.py app/services/search_replays.py app/services/search_harness_evaluations.py app/services/quality.py alembic/versions/0012_harness_chat_feedback.py tests/unit/test_chat_api.py tests/unit/test_chat_service.py tests/unit/test_search_api.py tests/unit/test_search_harness_evaluations.py tests/unit/test_search_replays.py tests/unit/test_search_service.py tests/unit/test_quality_api.py tests/unit/test_quality_service.py tests/unit/test_cli.py tests/unit/test_ui.py
uv run pytest tests/unit -q
uv run python -m compileall app tests
node --check app/ui/app.js
uv run alembic upgrade head
curl -sS http://127.0.0.1:8000/search/harnesses
curl -sS -X POST http://127.0.0.1:8000/search -H 'content-type: application/json' --data '{"query":"vent stack","mode":"keyword","limit":3,"harness_name":"wide_v2"}'
curl -sS http://127.0.0.1:8000/search/requests/<search_request_id>
curl -sS -X POST http://127.0.0.1:8000/chat -H 'content-type: application/json' --data '{"question":"What does the corpus say about vent stacks?","mode":"keyword","top_k":3,"harness_name":"wide_v2"}'
curl -sS -X POST http://127.0.0.1:8000/chat/answers/<chat_answer_id>/feedback -H 'content-type: application/json' --data '{"feedback_type":"incomplete","note":"Keyword harness did not surface a usable vent stack answer."}'
curl -sS -X POST http://127.0.0.1:8000/search/replays -H 'content-type: application/json' --data '{"source_type":"feedback","limit":3,"harness_name":"wide_v2"}'
curl -sS http://127.0.0.1:8000/search/replays/<replay_run_id>
curl -sS -X POST http://127.0.0.1:8000/search/harness-evaluations -H 'content-type: application/json' --data '{"baseline_harness_name":"default_v1","candidate_harness_name":"wide_v2","source_types":["feedback","evaluation_queries"],"limit":3}'
curl -sS http://127.0.0.1:8000/quality/trends
uv run docling-system-run-replay-suite feedback --limit 3
uv run docling-system-eval-reranker wide_v2 --baseline-harness-name default_v1 --limit 3
uv run docling-system-export-ranking-dataset --limit 5
uv run docling-system-audit
```

Key results:

- full unit suite passed
- JS syntax check passed
- compileall passed
- migration `0012_harness_chat_feedback` applied live
- harness catalog, harness-backed search, chat answer feedback, replay detail, harness evaluation, and trend endpoints all completed live
- replay, harness-evaluation, and export commands completed live
- audit stayed green after the new migration

## Current Contracts To Preserve

### Promotion

- validation still hard-gates promotion
- evaluation still does not block promotion

### Evaluation

- the fixed corpus in `docs/evaluation_corpus.yaml` remains the durable retrieval contract
- replay suites and mined candidates complement the fixed corpus; they do not replace it

### Search Telemetry

- every direct `/search` request persists a durable search-request record
- search requests now persist harness name, reranker version, retrieval profile name, and harness config snapshots
- feedback labels are durable operator annotations, not transient UI state
- replay suites should consume persisted requests, feedback, and eval rows instead of recomputing ad hoc query lists in the browser

### Chat

- every `/chat` response now persists a durable chat-answer record
- answer feedback is first-class persisted operator data and should be mined alongside retrieval feedback, not treated as UI-only state
- chat-answer rows should keep their originating `search_request_id` and harness metadata so answer quality can be evaluated against retrieval behavior

### Replay

- replay runs are persisted first-class records
- replay runs now persist the harness metadata they were executed with
- comparison is keyed by shared `(query_text, mode, filters)` identity
- ranking dataset export is a derived operator artifact, not a source of truth

### Audit

- `docling-system-audit` now checks:
  - active-run completion and validation invariants
  - completed-run document artifact presence
  - failed-run replayability
  - run summary count crosschecks
  - latest-evaluation presence for completed latest runs
  - table/figure artifact-path existence
  - required `failure.json` schema fields
  - known failure-stage membership

### Supplements

- chapter PDFs remain canonical
- supplement PDFs remain narrow repair inputs only
- overlay outputs must preserve chapter-local page spans and original source-segment provenance

## Remaining Gaps / Risks

### 1. Evaluation Still Does Not Gate Promotion

Still deliberate. Retrieval quality can regress while promotion still advances if validation passes.

### 2. Learned Harness Does Not Yet Use A Trained Model

Milestone 5 establishes the harness and data path, but the current rerankers are still hand-tuned linear scorers:

- there is still no trained reranker or offline fitting loop over the exported dataset
- harness evaluation currently compares named configs, not learned checkpoints
- the next leverage is using feedback, replay deltas, and eval rows to fit and validate a model-backed reranker offline

### 3. Historical Search Rows Still Carry Legacy Reranker Metadata

Older feedback rows in the local database still export their original reranker metadata, including legacy `heuristic_v1` labels. That is correct for provenance, but downstream training/export consumers need to treat historical rows as mixed-era data.

### 4. README And Handoff Are Current, But Product Docs Are Still Thin

The operator-facing commands and endpoints are documented, and the ranking dataset schema now has its own doc. The deeper design contract for harness evaluation semantics, answer-feedback interpretation, and future fitting workflows still lives mostly in code and tests.

## Recommended Next Steps

### Priority 1: Fit The First Offline Reranker

- define the first training/evaluation split over:
  - fixed eval queries
  - replay-derived labels
  - operator feedback
- fit the first offline reranker candidate against the exported dataset
- keep promotion gated by validation, but gate reranker adoption by replay/eval comparison

### Priority 2: Deepen Harness Evaluation

- persist named experiment configs beyond the current harness registry
- add richer drilldown on added hits, removed hits, and score shifts per replay query
- surface per-source improvements/regressions more prominently in the UI

### Priority 3: Expand Feedback Coverage

- add more answer-feedback coverage from real chat use
- mine repeated `no_answer` and `incomplete` patterns into new eval fixtures
- document when operator feedback should become a fixed corpus regression

## Handy Commands

Health:

```bash
curl -sS http://127.0.0.1:8000/health
```

Quality:

```bash
curl -sS http://127.0.0.1:8000/quality/summary | jq
curl -sS http://127.0.0.1:8000/quality/failures | jq
curl -sS http://127.0.0.1:8000/quality/evaluations | jq
curl -sS http://127.0.0.1:8000/quality/eval-candidates | jq
curl -sS http://127.0.0.1:8000/quality/trends | jq
```

Replay:

```bash
uv run docling-system-replay-search <search_request_id>
uv run docling-system-run-replay-suite feedback --limit 12
uv run docling-system-run-replay-suite live_search_gaps --limit 12
uv run docling-system-eval-reranker wide_v2 --baseline-harness-name default_v1 --limit 12
uv run docling-system-export-ranking-dataset --limit 200
curl -sS http://127.0.0.1:8000/search/harnesses | jq
curl -sS -X POST http://127.0.0.1:8000/search/harness-evaluations -H 'content-type: application/json' --data '{"baseline_harness_name":"default_v1","candidate_harness_name":"wide_v2","source_types":["feedback","evaluation_queries"],"limit":12}' | jq
curl -sS "http://127.0.0.1:8000/search/replays/compare?baseline_replay_run_id=<id>&candidate_replay_run_id=<id>" | jq
```

Chat:

```bash
curl -sS -X POST http://127.0.0.1:8000/chat -H 'content-type: application/json' --data '{"question":"What does the corpus say about vent stacks?","mode":"keyword","top_k":3,"harness_name":"wide_v2"}' | jq
curl -sS -X POST http://127.0.0.1:8000/chat/answers/<chat_answer_id>/feedback -H 'content-type: application/json' --data '{"feedback_type":"incomplete","note":"Keyword harness did not surface a usable vent stack answer."}' | jq
```

Audit / cleanup:

```bash
uv run docling-system-backfill-legacy-audit
uv run docling-system-audit
```

Open the PR:

```text
https://github.com/chunkstand/docling-system/pull/1
```
