# Session Handoff

Date: 2026-04-15 local / 2026-04-15 UTC verification
Project: `/Users/chunkstand/Documents/docling-system`
Branch: `main`
Remote: `origin -> https://github.com/chunkstand/docling-system.git`
PR: merged `#1` `Build docling-system v1 ingestion, retrieval, evaluation, and run audit surfaces`
PR URL: `https://github.com/chunkstand/docling-system/pull/1`
Latest committed checkpoint before this handoff update: `0d65122` (`milestone 7: backfill remaining typed task outputs`)

## Current Session Update (April 15, 2026)

Current status from this session:

- local `main` is now seven commits ahead of `origin/main`
  - `8cb897c` `milestone 1: add typed agent task context substrate`
  - `67dadd6` `milestone 2: add freshness-aware task context resolution`
  - `28f1044` `milestone 3: migrate apply task context flow`
  - `c542273` `milestone 4: add evaluation task context projection`
  - `22c0910` `milestone 5: migrate evaluation verifier context flow`
  - `079211f` `milestone 6: add triage task context projection`
  - `0d65122` `milestone 7: backfill remaining typed task outputs`
- the full typed agent-task context rollout now exists locally:
  - every task type in the current registry validates typed input and now emits typed output plus a canonical `storage/agent_tasks/<task_id>/context.json` artifact
  - `GET /agent-tasks/actions` now advertises output-schema metadata for migrated task types
  - `GET /agent-tasks/{task_id}` and `GET /agent-tasks/traces/export` now include additive context fields such as `dependency_edges`, `context_summary`, `context_refs`, `context_artifact_id`, and `context_freshness_status`
  - `GET /agent-tasks/{task_id}/context?format=json|yaml` and the matching CLI surface now expose the full task context projection
  - workflow-heavy paths now consume upstream state through dependency-role-aware typed context refs instead of nested `result_json["payload"][...]` reads
- the migrated workflow slices now cover:
  - `evaluate_search_harness`
  - `verify_search_harness_evaluation`
  - `draft_harness_config_update`
  - `verify_draft_harness_config`
  - `triage_replay_regression`
  - `apply_harness_config_update`
  - `enqueue_document_reprocess`
  - plus the remaining read-only task types with minimal typed-context backfill
- agent-task freshness is now explicit and inspectable per ref:
  - `fresh`
  - `stale`
  - `missing`
  - `schema_mismatch`
- current enforcement is:
  - `missing` and `schema_mismatch` block migrated downstream consumers
  - `stale` is advisory in v1
  - pre-context upstream tasks must be rerun into the migrated path before typed downstream consumers will accept them
- targeted verification for the rollout passed in-session:
  - `pytest tests/unit/test_alembic_0021_agent_task_dependency_kind.py tests/unit/test_agent_task_context.py tests/unit/test_agent_tasks.py tests/unit/test_agent_task_actions.py tests/unit/test_agent_task_verifications.py tests/unit/test_agent_task_triage.py tests/unit/test_agent_task_migration_audit.py tests/unit/test_agent_task_worker.py tests/unit/test_agent_tasks_api.py tests/unit/test_cli.py tests/integration/test_agent_task_triage_roundtrip.py -q`
  - result: `98 passed, 8 skipped`
- `SYSTEM_PLAN.md` was rewritten as an as-built reference that supersedes the old rebuilt v1 plan. It now reflects the live ingestion, retrieval, evaluation, quality, and agent-task architecture rather than the original target-state design.
- current working tree still has uncommitted docs-only/session-local changes:
  - `SYSTEM_PLAN.md` updated to the new as-built plan
  - `docs/SESSION_HANDOFF.md` updated with this handoff section
  - `tests/unit/test_ui.py` still contains the earlier local lint-only line-wrap edit

Use this section as the authoritative April 15 state.

## Prior Session Update (April 14, 2026)

Current status from this session:

- GitHub `main` now matches the latest committed system code. `HEAD`, `origin/main`, and the merged checkpoint all point to `446e3ba49fcb5bd860f762f08c3d217d21a14818`.
- local `main` is one lint-only working-tree edit ahead of that commit: `tests/unit/test_ui.py` wraps three long assertion lines to satisfy Ruff `E501`.
- current non-DB verification is green:
  - `.venv/bin/ruff check app tests`
  - `.venv/bin/python -m pytest tests/unit -q` -> `190 passed`
  - `.venv/bin/python -m compileall app tests`
  - `node --check app/ui/app.js`
- the DB-backed verification path is currently blocked:
  - `docker version` still cannot connect to the Docker daemon
  - no process is listening on `localhost:5432`
  - `DOCLING_SYSTEM_RUN_INTEGRATION=1 .venv/bin/python -m pytest tests/integration -q` currently fails with `11` setup errors rooted in `psycopg.OperationalError: connection refused`
- `curl -sS http://127.0.0.1:8000/health` still returns `{"status":"ok"}`, but that endpoint is not DB-backed and should not be treated as proof that ingest, search, or evaluation are currently usable.
- earlier disk pressure that contributed to the Docker outage was mitigated by clearing local caches and Docker logs. Disk space is no longer the immediate blocker; Docker/Postgres recovery still is.

Use this section and the updated runtime/verification sections below as the authoritative April 14 state. Historical notes below remain useful context.

## Earlier Session Update (April 13, 2026)

Later local verification after this handoff:

- the repository now includes a real Postgres-backed end-to-end integration harness in `tests/integration/`
- the harness provisions an isolated temporary schema and temp storage per test, and disables live embedding calls for deterministic execution
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest tests/integration/test_postgres_roundtrip.py -q` passes locally
- retrieval-accuracy phase 1 now exists as a non-default harness rollout:
  - `prose_v3` adds query-intent-aware prose retrieval and reranking
  - replay suites now accept `cross_document_prose_regressions`
  - harness-evaluation summaries now expose MRR and foreign-top-result counts for rollout gating
- fixed-corpus evaluation now supports explicit "no confident answer" cases in addition to retrieval, citation-purity, and structural checks
- current local verification on April 13, 2026:
  - `uv run pytest tests/unit -q` -> `184 passed`
  - `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest tests/integration/test_postgres_roundtrip.py -q` -> `2 passed`
  - `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest tests/integration/test_agent_task_triage_roundtrip.py -q` -> `6 passed`
- a leaked integration document created during early harness bring-up was removed from the live corpus
- live state is back to:
  - `document_count = 16`
  - `completed_latest_evaluations = 16`
  - `violation_count = 0`

Use the counts in this section instead of the older 12-document snapshots later in this historical handoff narrative.

## Executive Summary

The branch now includes:

- the full seven-milestone typed agent-task context rollout on local `main`
- a rewritten `SYSTEM_PLAN.md` that now serves as the as-built high-level system reference
- Lopopolo milestone 2 quality surfaces
- legacy audit-field backfill so historical rows satisfy the current audit contract
- persisted search-request telemetry, feedback labels, replay suites, replay comparison, and ranking-dataset export
- a replay/quality operator UI that now exposes both replay execution and replay comparison controls
- Milestone 5 learned-reranking harness infrastructure with named search harnesses, harness evaluations, answer-feedback capture, and replay drilldown
- follow-up gap closures for Milestone 5:
  - answer-feedback gaps now flow into `GET /quality/eval-candidates`
  - the operator UI now runs harness evaluations directly
  - ranking-dataset export now marks row schema version and metadata era
- retrieval-accuracy phase 1 hardening after the initial harness work:
  - internal query intent classification now distinguishes `tabular`, `prose_lookup`, and `prose_broad`
  - `prose_v3` now widens prose candidate recall with metadata-supplement and adjacent-chunk expansion
  - replay suites can now mine and evaluate `cross_document_prose_regressions`
  - harness-evaluation summaries now surface gate-facing metrics such as MRR and foreign-top-result counts
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
- the harness catalog now includes `prose_v3` as a non-default experimental retrieval profile
- harness evaluation is now exposed in the operator UI instead of only through API/CLI
- harness evaluation now carries enough rank-sensitive replay metrics to apply rollout gates instead of relying only on pass/fail counts
- exported ranking rows now self-identify as `legacy_pre_harness` or `harness_v1`
- persisted search-request details now record whether keyword serving used `strict` or `relaxed_or`
- persisted search-request details now also record `query_intent`, candidate-source breakdown, metadata-supplement counts, and adjacent-context expansion counts
- generic prose documents can promote with human-readable titles derived from parsed content
- the worker can safely process multiple queued runs without tripping `MultipleResultsFound`
- the fixed corpus now covers seven non-UPC documents, not just `The Bitter Lesson.pdf`
- the corpus now contains sixteen active documents
- all sixteen active documents now have completed latest evaluations
- latest evaluation detail can now mix retrieval and grounded-answer checks in one persisted surface
- answer evaluation can now explicitly require a fallback-style "no confident answer" outcome for negative questions
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

### 7. Retrieval Accuracy Phase 1

Committed changes through `cd0220f`:

- `app/services/search.py`
  - added internal query-intent classification for `tabular`, `prose_lookup`, and `prose_broad`
  - added non-default harness `prose_v3`
  - widened prose candidate generation with:
    - metadata-supplement chunk retrieval over title, heading, and filename stem
    - adjacent chunk expansion around top prose chunk seeds
  - persisted search telemetry for `query_intent`, candidate-source breakdown, metadata candidate count, and context-expansion count
  - persisted new prose rerank features including heading overlap, phrase overlap, rare-token overlap, adjacent-context signal, and stronger document-cluster behavior
- `app/services/search_replays.py`
  - added replay source type `cross_document_prose_regressions`
  - mined source-purity replay cases from evaluation rows without adding a DB migration
  - replay summaries now persist rank metrics including MRR and foreign-top-result counts
- `app/services/search_harness_evaluations.py`
  - harness-evaluation summaries now expose baseline/candidate MRR, foreign-top-result counts, and acceptance-check booleans
- `app/services/evaluations.py`
  - added explicit negative answer support via `expect_no_answer`
- `docs/evaluation_corpus.yaml`
  - added prose paraphrases, an additional Tyler's Kitchen contamination guard, and a negative prose answer case

Relevant files:

- `app/cli.py`
- `app/schemas/search.py`
- `app/services/evaluations.py`
- `app/services/search.py`
- `app/services/search_harness_evaluations.py`
- `app/services/search_replays.py`
- `app/ui/index.html`
- `app/ui/app.js`
- `docs/evaluation_corpus.yaml`
- `tests/unit/test_search_service.py`
- `tests/unit/test_search_replays.py`
- `tests/unit/test_search_harness_evaluations.py`
- `tests/unit/test_search_api.py`
- `tests/unit/test_cli.py`
- `tests/unit/test_eval_config.py`
- `tests/unit/test_evaluation_service.py`
- `tests/integration/test_postgres_roundtrip.py`
- `tests/unit/test_chat_service.py`
- `tests/unit/test_run_logic.py`

Live result:

- `The Bitter Lesson.pdf` reprocessed successfully with title `The Bitter Lesson`
- direct keyword search for `What is the main claim of The Bitter Lesson?` now returns grounded prose chunks
- `POST /chat` for the same question now returns a cited, model-backed answer instead of a no-evidence fallback
- `uv run docling-system-eval-run 5410bb6f-c8a0-47d5-ae23-2664e0060865` completed with fixture `bitter_lesson_prose`, `passed_queries = 3`, `failed_queries = 0`

### 8. Fixed-Corpus Expansion And Answer-Level Evals

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

### 9. Tyler's Kitchen Fixture Expansion And Embedding Overflow Fix

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
  - `completed_latest_evaluations = 16`
  - `skipped_latest_evaluations = 0`
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
  - `tests/integration/conftest.py`
  - `tests/integration/test_postgres_roundtrip.py`

Live result:

- `uv run docling-system-eval-corpus` completed live across all active fixture-backed documents
- `GET /quality/summary` now reports:
  - `document_count = 12`
  - `completed_latest_evaluations = 12`
  - `skipped_latest_evaluations = 0`
  - `missing_latest_evaluations = 0`
- `GET /documents/57e1c1e8-44d4-4a8c-ad8d-11e5eeb5aea4/evaluations/latest` now includes an `evaluation_kind = "answer"` row for the Bitter Lesson answer contract
- `GET /quality/eval-candidates?include_resolved=true` now shows historically fixed gaps as `resolution_status = "resolved"` when later evidence exists

### 10. Candidate Queue Cleanup And Non-Tabular Chat Recovery

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

## Historical Runtime State (April 14, 2026)

At handoff time on April 14, 2026:

- `curl -sS http://127.0.0.1:8000/health` returns `{"status":"ok"}`
- Docker is currently unavailable: `docker version` cannot connect to `unix:///Users/chunkstand/.docker/run/docker.sock`
- no process is listening on `localhost:5432`
- the health endpoint is not DB-backed, so database-dependent surfaces should be treated as unavailable until Docker/Postgres are recovered
- the repository still includes the Postgres-backed end-to-end integration harness under `tests/integration/`, but it is not runnable in the current environment
- GitHub `main` and the latest committed local code both point to `446e3ba49fcb5bd860f762f08c3d217d21a14818` (`Close ingest batch correctness gaps`)
- the local working tree is not clean because `tests/unit/test_ui.py` has an uncommitted lint-only wrap fixing three Ruff `E501` lines
- the DB-backed corpus counts, audit counts, and latest-evaluation counts below are the last known good state from April 13, 2026; they were not revalidated this session

Last known Postgres-backed audit result from April 13, 2026:

```json
{
  "checked_documents": 16,
  "checked_runs": 40,
  "checked_evaluations": 27,
  "checked_tables": 530,
  "checked_figures": 374,
  "violation_count": 0,
  "violation_counts_by_code": {},
  "violations": []
}
```

Historical last-known live replay/feedback verification from April 13, 2026 (not rerun this session):

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
- `uv run docling-system-eval-corpus` completed live with completed latest evaluations for all sixteen active documents
- `uv run docling-system-run-replay-suite feedback --limit 3` completed live
- `uv run docling-system-eval-reranker wide_v2 --baseline-harness-name default_v1 --limit 3` completed live
- `uv run docling-system-export-ranking-dataset --limit 5` now emits:
  - `row_schema_version`
  - `metadata_era`
  - replay `source_type`
  - top-level reranker/profile/config fields

## Last Known Active Corpus State

Last known active set from the last successful Postgres-backed verification on April 13, 2026 (not revalidated this session because Postgres is currently unavailable):

- `openrouter_spend_report.pdf` -> fixture `openrouter_spend_report_tables`
- `Standing Framework LLC - MT filed evidence.pdf` -> fixture `auto_standing_framework_llc_mt_filed_evidence`
- `NSF 26-508: TechAccess: AI-Ready America | NSF - U.S. National Science Foundation.pdf` -> fixture `nsf_ai_ready_america_figures`
- `TEST_PDF.pdf` -> fixture `test_pdf_prose`
- `The Bitter Lesson.pdf` -> fixture `bitter_lesson_prose`
- `20251217_TK_SoilReport.pdf` -> fixture `tyler_kitchen_soil_report`
- `20251216_TK_TransportationReport.pdf` -> fixture `tyler_kitchen_transportation_report`
- `20251215_TK_WildlifeSpecReport.pdf` -> fixture `tyler_kitchen_wildlife_report`
- `UPC_CH_5.pdf` -> fixture `upc_ch5`
- `UPC_CH_4.pdf` -> fixture `upc_ch4`
- `UPC_Appendix_N.pdf` -> fixture `born_digital_simple`
- `UPC_Appendix_B.pdf` -> fixture `appendix_b_prose_guidance`
- `UPC_CH_3.pdf` -> fixture `awkward_headers`
- `UPC_Ch_2.pdf` -> fixture `upc_ch2_figures`
- `UPC_CH_7.pdf` -> fixture `upc_ch7`
- `UPC_CH_1.pdf` -> fixture `prose_control`

## Historical Verification Performed (April 14, 2026)

Commands run this session:

```bash
.venv/bin/ruff check app tests
.venv/bin/python -m pytest tests/unit -q
.venv/bin/python -m compileall app tests
node --check app/ui/app.js
DOCLING_SYSTEM_RUN_INTEGRATION=1 .venv/bin/python -m pytest tests/integration -q
docker version
lsof -nP -iTCP:5432 -sTCP:LISTEN
curl -sS http://127.0.0.1:8000/health
```

Key results:

- non-DB verification is green after a local lint-only fix in `tests/unit/test_ui.py`
- `.venv/bin/ruff check app tests` passes
- `.venv/bin/python -m pytest tests/unit -q` passes with `190 passed`
- `.venv/bin/python -m compileall app tests` passes
- `node --check app/ui/app.js` passes
- earlier in this session, Ruff reported three `E501` violations in `tests/unit/test_ui.py`; those were fixed locally and are the only current working-tree delta
- the integration suite does not currently run:
  - `DOCLING_SYSTEM_RUN_INTEGRATION=1 .venv/bin/python -m pytest tests/integration -q` fails with `11` setup errors
  - the root cause is `psycopg.OperationalError: connection refused` to `localhost:5432`
  - `docker version` confirms the Docker daemon is still unavailable
  - `lsof -nP -iTCP:5432 -sTCP:LISTEN` returns no listener
- `curl -sS http://127.0.0.1:8000/health` returns `{"status":"ok"}`, but that is not evidence that DB-backed flows are healthy

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

### Agent Tasks

- task creation validates typed input against the registry and migrated tasks now also validate typed output before completion
- every current task type now emits a context artifact at `storage/agent_tasks/<task_id>/context.json`, with `context.yaml` as the derived human-readable sidecar
- task action definitions now advertise output schema metadata in addition to input schema metadata
- task detail and trace export now expose additive context fields without replacing the canonical `input` and `result` payloads
- migrated downstream consumers must resolve upstream state through typed context refs and dependency kinds such as `target_task`, `draft_task`, `source_task`, and `verification_task`
- `missing` and `schema_mismatch` freshness states block migrated consumers; `stale` is advisory in v1
- promotable flows still require explicit approval before applying a live harness override or queueing a reprocess action

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

The operator-facing commands and endpoints are documented, the ranking dataset schema has its own doc, and `SYSTEM_PLAN.md` has now been rewritten to match the live system. The deeper design contract for harness evaluation semantics, answer-feedback interpretation, and future fitting workflows still lives mostly in code and tests.

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

Agent tasks:

```bash
uv run docling-system-agent-task-actions
uv run docling-system-agent-task-show <task_id>
uv run docling-system-agent-task-context <task_id>
uv run docling-system-agent-task-export-traces --limit 25
curl -sS http://127.0.0.1:8000/agent-tasks/actions | jq
curl -sS http://127.0.0.1:8000/agent-tasks/<task_id> | jq
curl -sS "http://127.0.0.1:8000/agent-tasks/<task_id>/context?format=json" | jq
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

GitHub references:

```text
https://github.com/chunkstand/docling-system
https://github.com/chunkstand/docling-system/pull/1
```
