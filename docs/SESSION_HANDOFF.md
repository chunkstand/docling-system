# Session Handoff

Date: 2026-04-11 local / 2026-04-12 UTC verification
Project: `/Users/chunkstand/Documents/docling-system`
Branch: `codex/docling-system-build`
Remote: `origin -> https://github.com/chunkstand/docling-system.git`
Latest committed checkpoint: `69f21bb` (`Refine operator UI and add Appendix B evaluation fixture`)

## Executive Summary

The system remains healthy and usable as a local Docling-based ingestion, retrieval, and evaluation harness.

Current durable state:

- validation still gates promotion through `documents.active_run_id`
- evaluations are persisted per run and exposed through API and UI
- production search still supports explicit `run_id` evaluation comparisons through the same ranking path
- the chapter 5 supplement overlay workflow remains active and structurally pinned in evaluation
- the UI now includes a grounded chat surface and a calmer operator-focused layout

Two meaningful changes landed after the prior handoff:

1. The internal UI was reworked into an operator workspace centered on grounded answers, process visibility, and compact inspection instead of showing every surface at once.
2. `UPC_Appendix_B.pdf` now has a real evaluation fixture (`appendix_b_prose_guidance`), so the active validated set and active evaluated set are both eight documents.

## Current Runtime State

At handoff time:

- API health check succeeds at `http://127.0.0.1:8000/health`
- Alembic head is `0008_run_evaluations`
- the branch is clean
- at least one worker process appears to be running

Verification:

```bash
curl -sS http://127.0.0.1:8000/health
uv run alembic current
git status --short
```

Results:

```json
{"status":"ok"}
```

```text
0008_run_evaluations (head)
```

```text
[clean worktree]
```

Current active/evaluated document set:

```json
[
  {
    "source_filename": "UPC_CH_5.pdf",
    "latest_validation_status": "passed",
    "latest_evaluation_status": "completed",
    "latest_evaluation_fixture": "upc_ch5"
  },
  {
    "source_filename": "UPC_CH_4.pdf",
    "latest_validation_status": "passed",
    "latest_evaluation_status": "completed",
    "latest_evaluation_fixture": "upc_ch4"
  },
  {
    "source_filename": "UPC_Appendix_N.pdf",
    "latest_validation_status": "passed",
    "latest_evaluation_status": "completed",
    "latest_evaluation_fixture": "born_digital_simple"
  },
  {
    "source_filename": "UPC_Appendix_B.pdf",
    "latest_validation_status": "passed",
    "latest_evaluation_status": "completed",
    "latest_evaluation_fixture": "appendix_b_prose_guidance"
  },
  {
    "source_filename": "UPC_CH_3.pdf",
    "latest_validation_status": "passed",
    "latest_evaluation_status": "completed",
    "latest_evaluation_fixture": "awkward_headers"
  },
  {
    "source_filename": "UPC_Ch_2.pdf",
    "latest_validation_status": "passed",
    "latest_evaluation_status": "completed",
    "latest_evaluation_fixture": "upc_ch2_figures"
  },
  {
    "source_filename": "UPC_CH_7.pdf",
    "latest_validation_status": "passed",
    "latest_evaluation_status": "completed",
    "latest_evaluation_fixture": "upc_ch7"
  },
  {
    "source_filename": "UPC_CH_1.pdf",
    "latest_validation_status": "passed",
    "latest_evaluation_status": "completed",
    "latest_evaluation_fixture": "prose_control"
  }
]
```

## What Changed Most Recently

### 1. Grounded Chat And Operator UI

The UI now exposes:

- a grounded chat surface backed by `/chat`
- direct raw retrieval through `/search`
- process-stage telemetry while search/chat requests run
- compact selected-document inspection
- lower-priority detail surfaces for eval trace and evidence preview

Important implementation detail:

- the answer surface is now primary
- unrelated operational detail was moved away from the answer block to avoid overload
- chat still uses retrieved evidence first, then model synthesis second

Relevant files:

- `app/api/main.py`
- `app/schemas/chat.py`
- `app/services/chat.py`
- `app/ui/index.html`
- `app/ui/app.js`
- `app/ui/styles.css`
- `.env.example`
- `README.md`

### 2. Appendix B Evaluation Fixture

`UPC_Appendix_B.pdf` is no longer uncovered by the fixed evaluation corpus.

Added fixture:

- `appendix_b_prose_guidance`

Current fixture shape:

- prose-only guidance fixture
- `expected_logical_table_count: 0`
- `expected_figure_count: 0`
- expected chunk-hit queries:
  - `combination waste and vent system`
  - `relief vents`

Relevant files:

- `docs/evaluation_corpus.yaml`
- `tests/unit/test_eval_config.py`
- `tests/unit/test_evaluation_service.py`

Live verification:

```bash
uv run docling-system-eval-run 79bba82b-37b7-4e07-a915-380b83f98527
```

Result summary:

- fixture: `appendix_b_prose_guidance`
- status: `completed`
- `passed_queries: 2`
- `failed_queries: 0`
- `structural_passed: true`

### 3. Current Model Usage

The system uses OpenAI in two distinct ways:

- embedding model
  - `text-embedding-3-small`
  - used during ingestion to embed chunks and tables
  - used during semantic/hybrid retrieval to embed incoming queries
- chat model
  - currently `gpt-4.1-mini`
  - used only in the grounded answer path after retrieval
  - answer generation is citation-bounded by retrieved evidence

Everything else in the ingestion/validation/promotion path is deterministic orchestration around Docling, Postgres, filesystem artifacts, validation, and stored evaluations.

## Current Contracts To Preserve

### Promotion

- validation still hard-gates promotion
- evaluation still does not block promotion

### Search And Chat

- `/search` remains the direct mixed typed retrieval endpoint
- `/chat` is a retrieval-backed answer endpoint, not a second source of truth
- model-generated answers must remain grounded in retrieved evidence
- fallback behavior should remain evidence-forward when the chat model is unavailable

### Supplements

- chapter PDFs remain canonical documents
- supplement PDFs remain narrow repair inputs only
- overlay outputs must preserve chapter-local page span and original source-segment provenance
- every supplement-backed repair should be pinned by fixed-corpus evaluation coverage

## Verification Performed Recently

Commands run across the most recent sessions:

```bash
curl -sS http://127.0.0.1:8000/health
curl -sS http://127.0.0.1:8000/documents | jq
curl -sS -X POST http://127.0.0.1:8000/chat -H 'Content-Type: application/json' -d '{"question":"How should plastic vent joints be installed?","mode":"hybrid","top_k":4}'
uv run pytest tests/unit/test_chat_api.py tests/unit/test_chat_service.py tests/unit/test_ui.py -q
uv run pytest tests/unit/test_eval_config.py tests/unit/test_evaluation_service.py -q
uv run docling-system-eval-run 79bba82b-37b7-4e07-a915-380b83f98527
node --check app/ui/app.js
uv run python -m compileall app tests
```

Passing/observed results:

- API health check succeeded
- live `/chat` request succeeded and returned grounded citations from `UPC_CH_5.pdf`
- chat/UI tests passed
- eval config/service tests passed
- Appendix B live evaluation completed successfully
- JS syntax check passed
- compileall passed

## Known Gaps / Risks

### 1. Evaluation Still Does Not Gate Promotion

This remains deliberate. A retrieval regression can still promote if validation passes.

### 2. Evaluation Corpus Is Broader, But Still Thin

The document count is now fully covered for the active set, but most fixtures still have only a small number of queries. The next quality lever is richer eval depth, not just more fixture presence.

### 3. UI Is Better Prioritized, But Still Needs Iteration

The answer area is now less overloaded, but there is still room to:

- add a true clear-selection control
- clarify operator terminology around raw retrieval vs eval trace
- decide whether some lower detail surfaces should collapse by default

### 4. Branch Push Status Is Unverified

The local branch is committed through `69f21bb`, but do not assume it has been pushed unless you verify it explicitly.

## Recommended Next Steps

### Priority 1: Continue Corpus Expansion

- ingest additional UPC chapters or related PDFs
- for each new document, add fixed-corpus eval coverage as soon as retrieval is stable

### Priority 2: Deepen Evaluation Quality

- add more queries per fixture
- add adversarial/ambiguous queries
- add more explicit mode/filter coverage where ranking behavior matters

### Priority 3: Decide On UI/Operator Fit

- add a clear selected-document reset if the operator workflow still feels sticky
- consider collapsing or tabbing lower evidence surfaces if the inspection area still feels dense

### Priority 4: Revisit Eval Influence On Promotion

- keep validation as the hard gate for now
- decide whether future eval failures should warn, soft-block, or hard-block promotion

## Handy Commands

Health:

```bash
curl -sS http://127.0.0.1:8000/health
```

List documents:

```bash
curl -sS http://127.0.0.1:8000/documents | jq
```

Read latest evaluation:

```bash
curl -sS http://127.0.0.1:8000/documents/<document_id>/evaluations/latest | jq
```

Grounded chat request:

```bash
curl -sS -X POST http://127.0.0.1:8000/chat \
  -H 'Content-Type: application/json' \
  -d '{"question":"How should plastic vent joints be installed?","mode":"hybrid","top_k":4}' | jq
```

Evaluate one run:

```bash
uv run docling-system-eval-run <run_id>
```

Evaluate all matching active fixtures:

```bash
uv run docling-system-eval-corpus
```

Run targeted UI tests:

```bash
uv run pytest tests/unit/test_ui.py -q
```

Run full tests:

```bash
uv run pytest tests
```
