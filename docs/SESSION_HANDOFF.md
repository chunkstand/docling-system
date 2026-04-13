# Session Handoff

Date: 2026-04-12 local / 2026-04-12 UTC verification
Project: `/Users/chunkstand/Documents/docling-system`
Branch: `codex/docling-system-build`
Remote: `origin -> https://github.com/chunkstand/docling-system.git`
PR: `#1` `Build docling-system v1 ingestion, retrieval, evaluation, and run audit surfaces`
PR URL: `https://github.com/chunkstand/docling-system/pull/1`
Latest committed checkpoint before this handoff update: `6d8980c` (`Add Tyler's Kitchen eval fixtures and clip embedding inputs`)

## Executive Summary

The branch now includes:

- Lopopolo milestone 2 quality surfaces
- legacy audit-field backfill so historical rows satisfy the current audit contract
- persisted search-request telemetry, feedback labels, replay suites, replay comparison, and ranking-dataset export
- a replay/quality operator UI that now exposes both replay execution and replay comparison controls
- Milestone 5 learned-reranking harness infrastructure with named search harnesses, harness evaluations, answer-feedback capture, and replay drilldown
- follow-up gap closures for Milestone 5:
  - answer-feedback gaps now flow into `GET /quality/eval-candidates`
  - the operator UI now runs harness evaluations directly
  - ranking-dataset export now marks row schema version and metadata era
- data-agnostic hardening after ingesting non-UPC PDFs:
  - generic prose docs now infer usable titles instead of falling back to UUID-like names
  - keyword retrieval now relaxes to OR matching when strict full-text search returns zero hits
  - worker leasing now limits claim queries to one row so queued runs do not crash the worker
  - `The Bitter Lesson.pdf` is now part of the fixed corpus with a live passing evaluation
- fixed-corpus expansion and answer-level evaluation coverage:
  - `TEST_PDF.pdf` now has a fixed-corpus fixture and a live completed latest evaluation
  - `NSF 26-508: TechAccess: AI-Ready America` now has a figure-heavy fixed-corpus fixture
  - `openrouter_spend_report.pdf` now has a table-heavy fixed-corpus fixture
  - fixed-corpus fixtures can now include grounded-answer checks in addition to retrieval hit checks
  - latest evaluation detail rows now surface `evaluation_kind = retrieval | answer`
  - stale `GET /quality/eval-candidates` rows now auto-resolve when later evidence closes the gap
- post-eval gap cleanup:
  - non-tabular chat questions now retry chunk-only retrieval when the first pass returns only tables
  - low-signal unscoped one-token zero-result searches no longer become eval candidates
  - the live unresolved candidate queue is now empty by default
- corpus expansion and ingestion hardening for new Tyler's Kitchen analysis PDFs:
  - added fixed-corpus fixtures for the soil, transportation, and wildlife reports
  - latest-evaluation coverage is now live for those three documents
  - embedding generation now clips overlong inputs token-safely and batches requests instead of dropping semantic coverage for an entire run
  - the transportation report was reprocessed live to verify the former 8192-token overflow now degrades to a logged truncation event instead of an OpenAI 400
- automatic post-ingest evaluation fixture generation:
  - every successful validated run now writes an auto-generated fixture to `storage/evaluation_corpus.auto.yaml` before evaluation
  - manual fixtures in `docs/evaluation_corpus.yaml` still win when both exist for the same source filename
  - older runs without fixtures can now backfill one on first evaluation instead of staying permanently `skipped`
  - generated retrieval queries now prefer parsed titles and normalized source-filename segments, with chunk text only as fallback
- a green live `docling-system-audit` result after migration `0012_harness_chat_feedback`

What is now true:

- validation still gates promotion
- evaluation still does not gate promotion
- search requests are durable first-class records
- chat answers are durable first-class records with operator feedback
- search requests, replay runs, and chat answers now all carry harness metadata when available
- replay and trend surfaces exist in both the API and the operator UI
- named search harnesses can be replayed and compared through both the API and the CLI
- harness evaluation is now exposed in the operator UI instead of only through API/CLI
- exported ranking rows now self-identify as `legacy_pre_harness` or `harness_v1`
- persisted search-request details now record whether keyword serving used `strict` or `relaxed_or`
- generic prose documents can promote with human-readable titles derived from parsed content
- the worker can safely process multiple queued runs without tripping `MultipleResultsFound`
- the fixed corpus now covers seven non-UPC documents, not just `The Bitter Lesson.pdf`
- the corpus now contains sixteen active documents
- all sixteen active documents now have completed latest evaluations
- latest evaluation detail can now mix retrieval and grounded-answer checks in one persisted surface
- `GET /quality/eval-candidates` defaults to unresolved rows, with resolved rows available via `include_resolved=true`
- keyword chat can recover from table-heavy retrieval by switching to chunk-only evidence for non-tabular questions
- the default unresolved eval-candidate queue is currently empty live
- successful ingests now create immediate evaluation coverage even when no hand-authored fixture exists yet
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

Committed changes through `d12fe12`:

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

### 6. Data-Agnostic Hardening

What changed:

- `app/services/docling_parser.py`
  - added UUID-aware title normalization and fallback title inference from the first meaningful parsed text chunk
- `app/services/search.py`
  - added relaxed keyword fallback that retries lexical search with OR semantics when strict `plainto_tsquery` returns zero candidates
  - persisted `keyword_strategy` and `keyword_strict_candidate_count` on durable search-request records
- `app/services/chat.py`
  - improved chunk citation labels for prose-only docs
  - added normalized-question retry logic for chat-backed search requests
- `app/services/runs.py`
  - fixed worker leasing by adding `LIMIT 1` to the `claim_next_run` query
- `docs/evaluation_corpus.yaml`
  - added `bitter_lesson_prose` as the first non-UPC fixed-corpus fixture
- tests added or updated:
  - `tests/unit/test_docling_parser.py`
  - `tests/unit/test_chat_service.py`
  - `tests/unit/test_search_service.py`
  - `tests/unit/test_run_logic.py`
  - `tests/unit/test_eval_config.py`
  - `tests/unit/test_evaluation_service.py`

Live result:

- `The Bitter Lesson.pdf` reprocessed successfully with title `The Bitter Lesson`
- direct keyword search for `What is the main claim of The Bitter Lesson?` now returns grounded prose chunks
- `POST /chat` for the same question now returns a cited, model-backed answer instead of a no-evidence fallback
- `uv run docling-system-eval-run 5410bb6f-c8a0-47d5-ae23-2664e0060865` completed with fixture `bitter_lesson_prose`, `passed_queries = 3`, `failed_queries = 0`

### 7. Fixed-Corpus Expansion And Answer-Level Evals

What changed:

- `app/services/evaluations.py`
  - fixtures now support `expected_answer_queries`
  - evaluations now persist retrieval and answer checks in the same `document_run_evaluation_queries` table
  - evaluation summaries now record retrieval-vs-answer query counts
- `app/services/chat.py`
  - `answer_question()` now supports evaluation-time execution against a specific `run_id`
  - evaluation-time answer checks can skip persisting `chat_answer_records` while still persisting underlying search requests
- `app/services/quality.py`
  - mined eval candidates now record `evaluation_kind`
  - stale candidates now resolve automatically when later evaluation, search, or helpful-answer evidence closes the gap

### 8. Tyler's Kitchen Fixture Expansion And Embedding Overflow Fix

What changed:

- `docs/evaluation_corpus.yaml`
  - added `tyler_kitchen_soil_report`
  - added `tyler_kitchen_transportation_report`
  - added `tyler_kitchen_wildlife_report`
  - each fixture includes structural expectations, retrieval hit checks, and one grounded-answer check
- `app/services/embeddings.py`
  - added token-aware clipping for oversized embedding inputs using `tiktoken`
  - batched embedding requests so ingestion no longer depends on a single all-or-nothing call
  - logs `embedding_inputs_truncated` when clipping occurs
- `pyproject.toml`
  - added runtime dependency `tiktoken`
- tests added or updated:
  - `tests/unit/test_embeddings.py`
  - `tests/unit/test_eval_config.py`
  - `tests/unit/test_evaluation_service.py`

Live result:

- recovery run `021bc808-5da5-46a7-ad16-0259465e6203` for `20251216_TK_TransportationReport.pdf` completed successfully
- the worker logged `embedding_inputs_truncated` with `clipped_input_count = 1`
- the prior OpenAI `400` for `maximum input length is 8192 tokens` did not recur
- latest transportation evaluation completed automatically with fixture `tyler_kitchen_transportation_report` and `4/4` queries passed
- manual eval runs for:
  - `20251217_TK_SoilReport.pdf`
  - `20251215_TK_WildlifeSpecReport.pdf`
  also completed with `4/4` queries passed
- live quality summary now reports:
  - `document_count = 16`
  - `completed_latest_evaluations = 15`
  - `skipped_latest_evaluations = 1`
- live audit remains green with:
  - `checked_documents = 16`
  - `checked_runs = 38`
  - `checked_evaluations = 25`
  - `checked_tables = 530`
  - `checked_figures = 364`
  - `violation_count = 0`
  - unresolved rows remain the default response; resolved rows require `include_resolved=true`
- `app/services/search_replays.py`
  - replay sourcing now ignores answer-evaluation rows and stays retrieval-only
- `app/api/main.py`
  - `GET /quality/eval-candidates` now accepts `limit` and `include_resolved`
- `app/cli.py`
  - `uv run docling-system-eval-candidates --include-resolved`
- `docs/evaluation_corpus.yaml`
  - added fixtures:
    - `test_pdf_prose`
    - `nsf_ai_ready_america_figures`
    - `openrouter_spend_report_tables`
  - added explicit `mode: keyword` retrieval cases for prose fixtures
  - added answer-level checks for `The Bitter Lesson`, `TEST_PDF`, `NSF 26-508`, and `openrouter_spend_report`
- tests added or updated:
  - `tests/unit/test_eval_config.py`
  - `tests/unit/test_evaluation_service.py`
  - `tests/unit/test_chat_service.py`
  - `tests/unit/test_quality_service.py`
  - `tests/unit/test_quality_api.py`
  - `tests/unit/test_cli.py`

Live result:

- `uv run docling-system-eval-corpus` completed live across all active fixture-backed documents
- `GET /quality/summary` now reports:
  - `document_count = 12`
  - `completed_latest_evaluations = 12`
  - `skipped_latest_evaluations = 0`
  - `missing_latest_evaluations = 0`
- `GET /documents/57e1c1e8-44d4-4a8c-ad8d-11e5eeb5aea4/evaluations/latest` now includes an `evaluation_kind = "answer"` row for the Bitter Lesson answer contract
- `GET /quality/eval-candidates?include_resolved=true` now shows historically fixed gaps as `resolution_status = "resolved"` when later evidence exists

### 8. Candidate Queue Cleanup And Non-Tabular Chat Recovery

Uncommitted changes captured by this handoff update:

- `app/services/chat.py`
  - non-tabular chat questions now retry chunk-only retrieval when the initial evidence set is all tables
  - this keeps keyword chat from synthesizing answers from irrelevant table context on prose-style questions
- `app/services/quality.py`
  - unscoped one-token zero-result searches no longer become live eval candidates
  - answer-gap resolution now treats internal chunk-only chat retries as the same question even though the retry persists `result_type = "chunk"`
- tests added or updated:
  - `tests/unit/test_chat_service.py`
  - `tests/unit/test_quality_service.py`

Live result:

- `POST /chat` for `What does the corpus say about vent stacks?` in `keyword` mode with `wide_v2` now returns chunk citations and a materially better grounded answer instead of table-only context
- posting `helpful` feedback on the repaired vent-stack answer resolves the historical `answer_feedback_gap`
- `GET /quality/eval-candidates` now returns an empty list live
- resolved history is still available from `GET /quality/eval-candidates?include_resolved=true`

## Current Runtime State

At handoff time:

- API health check succeeds at `http://127.0.0.1:8000/health`
- the API was restarted after the answer-eval and quality-candidate changes
- the worker was restarted after the same code update
- Alembic head in the running database is `0012_harness_chat_feedback`
- `docling-system-audit` completes live with zero violations
- the active corpus now includes twelve documents
- the latest-evaluation surface is populated for all twelve active documents
- the fixed corpus now includes four non-UPC fixtures:
  - `bitter_lesson_prose`
  - `test_pdf_prose`
  - `nsf_ai_ready_america_figures`
  - `openrouter_spend_report_tables`
- the default unresolved eval-candidate queue is empty

Live audit result:

```json
{
  "checked_documents": 12,
  "checked_runs": 33,
  "checked_evaluations": 20,
  "checked_tables": 484,
  "checked_figures": 355,
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
- `GET /quality/eval-candidates` now includes `answer_feedback_gap` rows from grounded chat feedback
- `GET /quality/eval-candidates` now defaults to unresolved rows and supports `include_resolved=true`
- `GET /quality/eval-candidates` now returns `[]` live after the vent-stack repair and low-signal candidate filtering
- direct keyword search for `What is the main claim of The Bitter Lesson?` now persists `keyword_strategy = "relaxed_or"` and returns the expected prose chunks
- `POST /chat` for the same query now returns a grounded answer with citations from `The Bitter Lesson.pdf`
- `POST /chat` for `What does the corpus say about vent stacks?` in `keyword` mode now returns chunk citations instead of table-only context
- `GET /documents/57e1c1e8-44d4-4a8c-ad8d-11e5eeb5aea4/evaluations/latest` now reports fixture `bitter_lesson_prose` with `passed_queries = 5`, including one answer-level check
- `uv run docling-system-eval-corpus` completed live with completed latest evaluations for all twelve active documents
- `uv run docling-system-run-replay-suite feedback --limit 3` completed live
- `uv run docling-system-eval-reranker wide_v2 --baseline-harness-name default_v1 --limit 3` completed live
- `uv run docling-system-export-ranking-dataset --limit 5` now emits:
  - `row_schema_version`
  - `metadata_era`
  - replay `source_type`
  - top-level reranker/profile/config fields

## Active Corpus State

Current active set:

- `openrouter_spend_report.pdf` -> fixture `openrouter_spend_report_tables`
- `NSF 26-508: TechAccess: AI-Ready America | NSF - U.S. National Science Foundation.pdf` -> fixture `nsf_ai_ready_america_figures`
- `TEST_PDF.pdf` -> fixture `test_pdf_prose`
- `The Bitter Lesson.pdf` -> fixture `bitter_lesson_prose`
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
curl -sS http://127.0.0.1:8000/quality/eval-candidates | jq
curl -sS -X POST http://127.0.0.1:8000/search/replays -H 'content-type: application/json' --data '{"source_type":"feedback","limit":3,"harness_name":"wide_v2"}'
curl -sS http://127.0.0.1:8000/search/replays/<replay_run_id>
curl -sS -X POST http://127.0.0.1:8000/search/harness-evaluations -H 'content-type: application/json' --data '{"baseline_harness_name":"default_v1","candidate_harness_name":"wide_v2","source_types":["feedback","evaluation_queries"],"limit":3}'
curl -sS http://127.0.0.1:8000/quality/trends
uv run docling-system-run-replay-suite feedback --limit 3
uv run docling-system-eval-reranker wide_v2 --baseline-harness-name default_v1 --limit 3
uv run docling-system-export-ranking-dataset --limit 5
uv run docling-system-audit
uv run pytest tests/unit/test_run_logic.py tests/unit/test_docling_parser.py tests/unit/test_chat_service.py tests/unit/test_search_service.py tests/unit/test_eval_config.py tests/unit/test_evaluation_service.py -q
uv run docling-system-eval-run 5410bb6f-c8a0-47d5-ae23-2664e0060865
uv run docling-system-eval-corpus
uv run docling-system-eval-run 12188f49-22a3-43c3-a774-00408386e9cf
uv run docling-system-eval-run 18732576-bd9f-4b8f-977e-7d0e88a7a0aa
uv run docling-system-eval-run 7531f905-2256-4cf2-bc1f-7e8ec02f92db
curl -i -sS -X POST http://127.0.0.1:8000/search -H 'content-type: application/json' --data '{"query":"What is the main claim of The Bitter Lesson?","mode":"keyword","limit":4,"filters":{"document_id":"57e1c1e8-44d4-4a8c-ad8d-11e5eeb5aea4"}}'
curl -sS -X POST http://127.0.0.1:8000/chat -H 'content-type: application/json' --data '{"question":"What is the main claim of The Bitter Lesson?","mode":"keyword","top_k":4,"document_id":"57e1c1e8-44d4-4a8c-ad8d-11e5eeb5aea4"}'
curl -sS http://127.0.0.1:8000/documents/57e1c1e8-44d4-4a8c-ad8d-11e5eeb5aea4/evaluations/latest
curl -sS 'http://127.0.0.1:8000/quality/eval-candidates?include_resolved=true&limit=20'
curl -sS -X POST http://127.0.0.1:8000/chat -H 'content-type: application/json' --data '{"question":"What does the corpus say about vent stacks?","mode":"keyword","top_k":4,"harness_name":"wide_v2"}'
curl -sS -X POST http://127.0.0.1:8000/chat/answers/<chat_answer_id>/feedback -H 'content-type: application/json' --data '{"feedback_type":"helpful","note":"Chunk-only retry surfaced usable vent stack context."}'
curl -sS http://127.0.0.1:8000/quality/eval-candidates | jq
```

Key results:

- full unit suite passed
- JS syntax check passed
- compileall passed
- migration `0012_harness_chat_feedback` applied live
- harness catalog, harness-backed search, chat answer feedback, replay detail, harness evaluation, and trend endpoints all completed live
- served UI now includes harness-evaluation controls and source toggles
- eval candidates now mine grounded-answer `unsupported` and `incomplete` feedback into first-class candidate rows
- ranking export now distinguishes `legacy_pre_harness` rows from `harness_v1` rows
- replay, harness-evaluation, and export commands completed live
- audit stayed green after the new migration
- focused parser/chat/search/worker/eval tests passed after the data-agnostic hardening work
- `The Bitter Lesson` fixed-corpus evaluation passed live
- the three new non-UPC fixtures (`TEST_PDF`, `NSF 26-508`, `openrouter_spend_report`) all passed live against their active runs
- `uv run docling-system-eval-corpus` completed live and eliminated the previously skipped latest evaluation rows
- evaluation detail now shows persisted `evaluation_kind = "answer"` rows alongside retrieval checks
- `GET /quality/eval-candidates?include_resolved=true` now shows resolved historical gaps with `resolution_status`, `resolved_at`, and `resolution_reason`
- `GET /quality/eval-candidates` is now empty live because the remaining actionable gap was resolved and low-signal zero-result noise is filtered out
- keyword chat over vent-stack questions now recovers with chunk citations instead of table-only evidence
- generic keyword questions over prose docs no longer fail closed when strict lexical matching returns zero hits

## Current Contracts To Preserve

### Promotion

- validation still hard-gates promotion
- evaluation still does not block promotion

### Evaluation

- the fixed corpus in `docs/evaluation_corpus.yaml` remains the durable evaluation contract
- the fixed corpus may now include grounded-answer contracts via `expected_answer_queries`
- retrieval and answer checks now share the same persisted `document_run_evaluation_queries` surface and are distinguished by `evaluation_kind`
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
- evaluation-time answer checks may skip persisting `chat_answer_records`, but the underlying search requests should remain durable for provenance

### Replay

- replay runs are persisted first-class records
- replay runs now persist the harness metadata they were executed with
- comparison is keyed by shared `(query_text, mode, filters)` identity
- ranking dataset export is a derived operator artifact, not a source of truth
- export rows now carry `row_schema_version`, `metadata_era`, and persisted harness config snapshots so mixed-era data is machine-visible

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

### 1. Cross-Domain Fixed-Corpus Coverage Is Better, But Still Thin

The corpus is no longer effectively UPC-only. Four non-UPC documents are now fixture-backed and passing live. The remaining gap is breadth, not existence:

- there is still no scientific paper with dense referenced figures
- there is still no spreadsheet-like financial PDF with many repeated table families
- there is still no long-form policy/report PDF with varied section hierarchy and appendices

### 2. Evaluation Still Does Not Gate Promotion

Still deliberate. Retrieval quality can regress while promotion still advances if validation passes.

### 3. Learned Harness Does Not Yet Use A Trained Model

Milestone 5 establishes the harness and data path, but the current rerankers are still hand-tuned linear scorers:

- there is still no trained reranker or offline fitting loop over the exported dataset
- harness evaluation currently compares named configs, not learned checkpoints
- the next leverage is using feedback, replay deltas, and eval rows to fit and validate a model-backed reranker offline

### 4. Historical Search Rows Still Carry Legacy Signals

Older feedback rows in the local database still export their original reranker metadata, including legacy `heuristic_v1` labels. The export now marks these rows as `legacy_pre_harness`, which removes ambiguity, but downstream fitting code still needs an explicit policy for whether to include them.

### 5. README And Handoff Are Current, But Product Docs Are Still Thin

The operator-facing commands and endpoints are documented, and the ranking dataset schema now has its own doc. The deeper design contract for harness evaluation semantics, answer-feedback interpretation, and future fitting workflows still lives mostly in code and tests.

## Recommended Next Steps

### Priority 1: Broaden Cross-Domain Fixture Diversity

- add at least:
  - one scientific paper with dense figures and citations
  - one longer policy/report PDF with appendices and section nesting
  - one spreadsheet-like or invoice-heavy PDF with repeated table families
- keep the fixture expectations generic and retrieval-focused
- keep pairing new domains with answer-level checks where grounded chat matters

### Priority 2: Fit The First Offline Reranker

- define the first training/evaluation split over:
  - fixed eval queries
  - replay-derived labels
  - operator feedback
- fit the first offline reranker candidate against the exported dataset
- keep promotion gated by validation, but gate reranker adoption by replay/eval comparison

### Priority 3: Deepen Harness Evaluation

- persist named experiment configs beyond the current harness registry
- add richer drilldown on added hits, removed hits, and score shifts per replay query
- surface per-source improvements/regressions more prominently in the UI

### Priority 4: Expand Feedback Coverage

- add more answer-feedback coverage from real chat use
- mine repeated `no_answer`, `unsupported`, and `incomplete` patterns into new eval fixtures
- document when operator feedback should become a fixed corpus regression
- decide whether resolved eval-candidates should eventually age out of the UI entirely or remain visible only through `include_resolved=true`

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
