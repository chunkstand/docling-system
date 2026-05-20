# Court-Grade Readiness DB Blockers Resolution Milestone Plan

Date: 2026-05-20
Status: resolved locally in the current working tree on 2026-05-20
(uncommitted)
Owner context: standalone follow-on after the 2026-05-20 regression-readiness
bootstrap refresh in `docs/evaluation_data_readiness.md` and
`docs/SESSION_HANDOFF.md`

## Completed Result

Live closeout result on 2026-05-20:

- `uv run docling-system-bootstrap-court-grade-readiness --compact` succeeded
  on the strict regression-only local baseline.
- `uv run docling-system-evaluation-data-readiness --output storage/evaluation_data_readiness.latest.json`
  now reports `regression_ready=true`, `court_grade_ready=true`,
  `passed_gate_count=11`, and `failed_gate_count=0`.
- The live DB now contains `25` operator-feedback rows, `25`
  technical-report claim-feedback rows, `1` active governed replay-alert
  snapshot with `5` rows, complete replay coverage across all required source
  types, `1` persisted harness evaluation covering every required source type,
  `1` retrieval-judgment set, `1` completed retrieval-training run, and
  `147` training examples.
- The court-grade owner split closed without shifting architecture debt:
  `app/services/court_grade_readiness_bootstrap.py` now closes at `287` lines,
  with focused owners at `400`, `600`, and `338` lines; the CLI closes at
  `app/cli.py=212`, `app/cli_commands/runtime.py=384`, and
  `app/cli_commands/readiness.py=278`.
- `uv run docling-system-hotspot-prevention-check --strict`,
  `uv run docling-system-hygiene-check`, `uv run docling-system-architecture-inspect`,
  and `git diff --check` all pass on the final working tree.
- `env DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs` passes at
  `2159 passed`.

Later 2026-05-20 replay-quality follow-on result:

- `DOCLING_SYSTEM_MANUAL_EVALUATION_CORPUS_PATH=docs/evaluation_corpus.yaml uv run docling-system-eval-corpus`
  refreshed the reviewed manual evaluation to `8 / 8`.
- `uv run docling-system-agent-trace-review --limit 5 --skip-hygiene` now
  reports `observation_count=0`.
- The prior reviewed `mesa restoration outlook distinct prose recall`
  `evaluation_queries` miss is closed, so no DB-readiness residual remains in
  this packet.

## Purpose

Resolve the six open database-backed court-grade readiness blockers that remain
after the fresh regression bootstrap succeeds, and make the repopulation path
deterministic from tracked repo artifacts instead of ad hoc local DB edits.

Current blocker set from `storage/evaluation_data_readiness.latest.json`:

- `operator_feedback_coverage`
- `technical_report_claim_feedback_ledger`
- `claim_support_replay_alert_corpus`
- `all_replay_source_coverage`
- `harness_evaluation_source_coverage`
- `retrieval_learning_materialized`

Current live evidence from the fresh 2026-05-20 local rebuild:

- `regression_ready=true`
- `court_grade_ready=false`
- `passed_gate_count=5`
- `failed_gate_count=6`
- `1` active document
- `2` completed evaluations
- `10` persisted evaluation queries
- replay coverage only for `evaluation_queries`, `live_search_gaps`, and
  `cross_document_prose_regressions`
- `0` operator-feedback rows
- `0` technical-report claim-feedback rows
- `0` governed claim-support replay-alert corpus rows / active snapshots
- `0` harness-evaluation source rows
- `0` retrieval judgment sets, `0` completed retrieval training runs, and `0`
  retrieval training examples

## Goal

Starting from a repo-owned local Postgres database rebuilt from tracked
artifacts, make the readiness path deterministic and repeatable until:

- `uv run docling-system-evaluation-data-readiness --output storage/evaluation_data_readiness.latest.json`
  reports `regression_ready=true`
- the same report reports `court_grade_ready=true`
- `failed_gate_count=0`
- the live DB contains the minimum required court-grade evidence lanes without
  manual SQL edits or chat-only instructions

## Non-Goals

- Do not broaden this DB-blockers packet into unrelated search tuning beyond
  the focused replay-quality follow-on needed to keep the reviewed fixtures and
  trace-review lane truthful.
- Do not broaden the manual five-document reviewed corpus unless the current
  thresholds drift or stop matching the live fixtures.
- Do not reopen the broader architecture queue, hotspot-owner routing, or
  unrelated runtime/worker modernization work.
- Do not weaken readiness thresholds, replay suites, harness gates, or
  retrieval-learning provenance requirements just to force green output.

## Scope

- Add a deterministic court-grade repopulation path on top of the current
  regression bootstrap baseline.
- Materialize the missing operator-feedback, technical-report claim-feedback,
  governed replay-alert corpus, replay-source, harness-source, and
  retrieval-learning rows through repo-owned services and commands.
- Add or extend tracked bootstrap artifacts, runtime/CLI surfaces,
  DB-backed tests, and closeout docs needed to prove the path.
- Keep the current regression bootstrap reproducible and strict about mixed DB
  state.

## Out Of Scope

- Manual one-off DB editing in a SQL console.
- New public API surface unless an existing CLI/service contract cannot express
  the deterministic bootstrap.
- Broad documentation refresh outside the touched readiness/runbook surfaces.

## Owner Surfaces

- `app/services/regression_readiness_bootstrap.py`
- `app/services/evaluation_data_readiness.py`
- `app/services/search_replays.py`
- `app/services/search_replay_claim_feedback_cases.py`
- `app/services/search_harness_evaluations.py`
- `app/services/evidence_claim_feedback_lifecycle.py`
- `app/services/retrieval_learning.py`
- `app/services/retrieval_learning_dataset_sources.py`
- `app/services/retrieval_learning_replay_alert_sources.py`
- `app/services/audit_bundle_replay_alert_corpus.py`
- `app/cli.py`
- `app/cli_commands/runtime.py`
- `app/cli_commands/search_harness.py`
- `docs/evaluation_bootstrap/`
- `docs/evaluation_data_readiness.md`
- `docs/SESSION_HANDOFF.md`
- `docs/agentic_architecture_index.md`
- `README.md` if command or operator workflow text changes
- `tests/integration/test_regression_readiness_bootstrap.py`
- new focused readiness / replay / harness / retrieval-learning integration
  tests placed beside the surfaces they protect

## Placement Rules

- Preserve `uv run docling-system-bootstrap-regression-readiness` as the
  empty-DB baseline. Do not silently repurpose it to accept arbitrary partial
  DB state.
- The preferred path is a second deterministic bootstrap step that requires the
  regression baseline and rejects unexpected mixed-state DBs.
- Track bootstrap seed inputs under repo-owned docs or config paths, not under
  `/tmp`, notebooks, or ad hoc scripts.
- Persist operator feedback, claim feedback, replay-alert corpora, harness
  evaluations, and retrieval-learning rows through typed service owners so the
  normal provenance and readiness ledgers remain intact.
- Keep YAML human-readable only. Readiness gates must still derive from typed
  DB rows and persisted canonical artifacts.
- Place new tests beside the concern they protect; do not grow broad hotspot
  test roots just to cover the new bootstrap path.

## Weak-Point Prevention Contract

| Weak point forecast | Owner surface | Prevention gate | Fail threshold | Controlled violation | Future-Codex misuse scenario |
| --- | --- | --- | --- | --- | --- |
| A bootstrap claims court-grade readiness from a mixed or partially seeded DB. | `app/services/regression_readiness_bootstrap.py`, new court-grade bootstrap owner, `docs/evaluation_data_readiness.md` | Focused integration bootstrap tests plus readiness report diff | A command succeeds when required baseline preconditions are missing or when unrelated rows already exist | Seed one extra feedback or replay row before court-grade bootstrap and confirm the bootstrap refuses to run | A future session reruns the court-grade builder on a drifted local DB and mistakes the merged state for deterministic proof |
| Readiness turns back into prose-only status instead of live DB evidence. | `app/services/evaluation_data_readiness.py`, `storage/evaluation_data_readiness.latest.json` | `uv run docling-system-evaluation-data-readiness --output storage/evaluation_data_readiness.latest.json` | `court_grade_ready` stays false after the intended closeout, or blockers disappear without matching DB rows | Remove one required source family and confirm the report fails with the exact blocker key | A future session edits docs to say "ready" without regenerating the report |
| Operator feedback or claim-feedback rows are seeded without the required type/label/status diversity. | feedback / claim-feedback seed artifacts and their bootstrap owner | Focused integration assertions on row counts and diversity plus readiness report | Missing any required feedback type, learning label, or support status | Seed only `relevant` feedback or only `supported` claim rows and confirm readiness still fails | A future session takes a shortcut with twenty-five copies of one row family to satisfy the total-count threshold |
| Replay and harness coverage are created incompletely or through the wrong source families. | `app/services/search_replays.py`, `app/services/search_harness_evaluations.py`, CLI wrappers | Replay-suite commands plus persisted harness-evaluation detail checks | `feedback` or `technical_report_claim_feedback` replay coverage is missing, or persisted harness sources omit any required source type | Run a harness evaluation without one source type and confirm the source-row gate still fails | A future session records a replay run and assumes that also created harness source coverage |
| `no_answer` replay rows get reclassified as regressions during the closeout. | replay traces, trace-review surface, focused replay tests | `uv run docling-system-agent-trace-review --limit 5 --skip-hygiene` plus replay-source integration coverage | Trace review reports court-grade replay rows as regressions when the replay run completed successfully | Seed intentional `no_answer` feedback rows and confirm trace review stays empty only when the replay handling is correct | A future session "fixes" zero-result rows by deleting them instead of preserving the governed no-answer coverage |
| Retrieval-learning materialization loses provenance or produces a green count with the wrong sources. | `app/services/retrieval_learning.py`, dataset source owners, training-run artifacts | `uv run docling-system-materialize-retrieval-learning ...` plus focused ledger integrity tests | No completed training run exists, source families are missing, or training examples stay below threshold | Materialize from only replay sources and confirm readiness still fails on training coverage or provenance assertions | A future session bypasses the governed replay-alert / claim-feedback sources and materializes a set that looks large but is not court-grade grounded |
| Docs drift away from the live bootstrap chain. | `docs/evaluation_data_readiness.md`, `README.md`, `docs/SESSION_HANDOFF.md`, `docs/agentic_architecture_index.md` | `git diff --check` plus closeout review against the regenerated readiness report | Commands, blockers, or counts in docs do not match the closeout report | Leave a stale blocker list in one doc and confirm closeout review rejects the mismatch | A future session updates only the plan doc and leaves the operator docs pointing at the older readiness state |

## Milestone Sequence

### Milestone 0: Freshness And Baseline Lock

Outcome label: reduced

Purpose: freeze the exact current blocker state and lock the bootstrap contract
before broader DB repopulation work starts.

Scope:

- Re-run or regenerate the current readiness report from the live rebuild.
- Confirm the six open blocker keys and their exact row deficits.
- Confirm the regression bootstrap still rejects non-empty DBs.
- Decide and document the deterministic bootstrap shape:
  empty DB -> regression bootstrap -> court-grade bootstrap.
- Stop if the current dirty readiness-bootstrap slice cannot be separated
  safely from unrelated work.

Acceptance:

- `storage/evaluation_data_readiness.latest.json` records the six blocker keys
  listed at the top of this plan.
- `docs/evaluation_data_readiness.md` and `docs/SESSION_HANDOFF.md` reflect the
  same blocker set and baseline counts.
- The implementation path for the next milestone is recorded as a sibling
  court-grade bootstrap or an equally strict typed-service sequence.
- The regression bootstrap still refuses unexpected non-empty DB state.

Stop conditions:

- The readiness report surfaces blocker keys outside the current six and they
  cannot be routed as part of this packet.
- The current regression-bootstrap worktree slice is still too unstable to use
  as the deterministic baseline.
- The required tracked seed artifacts do not exist yet and their format cannot
  be agreed from current repo contracts.

### Milestone 1: Court-Grade Seed Artifacts And Deterministic Bootstrap Owner

Outcome label: reduced

Purpose: create a repo-owned, replayable path that populates the missing
court-grade data lanes without manual DB editing.

Scope:

- Add tracked seed artifacts for operator feedback, technical-report claim
  feedback, and governed claim-support replay-alert rows.
- Implement a typed bootstrap owner that requires the regression baseline and
  writes the missing rows through existing service/model contracts.
- Preserve claim-feedback hashes, search/result linkage, evidence refs, manifest
  refs, PROV refs, readiness gate refs, and semantic-governance linkage.
- Publish one active governed replay-alert corpus snapshot with at least five
  rows from tracked bootstrap inputs.

Acceptance:

- Running the new court-grade bootstrap on top of the regression baseline
  creates at least:
  `25` operator-feedback rows across `relevant`, `irrelevant`,
  `missing_table`, `missing_chunk`, and `no_answer`;
  `25` technical-report claim-feedback rows across `positive`, `negative`,
  and `missing` plus `supported`, `weak`, `missing`, `contradicted`, and
  `rejected`;
  and `1` active claim-support replay-alert snapshot with `5` rows.
- The bootstrap refuses an empty DB, an already court-grade-seeded DB, or any
  mixed DB state that is not the documented regression baseline.
- `uv run docling-system-evaluation-data-readiness` passes
  `operator_feedback_coverage`,
  `technical_report_claim_feedback_ledger`, and
  `claim_support_replay_alert_corpus` after this milestone.

Stop conditions:

- The existing typed owners cannot write the claim-feedback or replay-alert rows
  without a schema change not already routed in the repo.
- Meeting the traceability requirements would require bypassing the current
  evidence or semantic-governance contracts.

### Milestone 2: Replay Completion And Harness Source Coverage

Outcome label: reduced

Purpose: finish the court-grade replay lanes and persist the missing
`SearchHarnessEvaluationSource` rows.

Scope:

- Run or encode the bootstrap orchestration for the missing replay suites:
  `feedback` and `technical_report_claim_feedback`.
- Preserve the intentional `no_answer` zero-result rows as valid feedback
  coverage rather than replay regressions.
- Record at least one persisted harness evaluation whose `sources` include all
  required replay source types:
  `evaluation_queries`, `feedback`, `live_search_gaps`,
  `cross_document_prose_regressions`, and
  `technical_report_claim_feedback`.

Acceptance:

- `uv run docling-system-run-replay-suite feedback --limit 25` completes with
  persisted replay coverage.
- `uv run docling-system-run-replay-suite technical_report_claim_feedback --limit 25`
  completes with persisted replay coverage.
- `uv run docling-system-eval-reranker default_v1 --baseline-harness-name default_v1 --source-type evaluation_queries --source-type feedback --source-type live_search_gaps --source-type cross_document_prose_regressions --source-type technical_report_claim_feedback --limit 25`
  persists a harness evaluation whose `SearchHarnessEvaluationSource` rows cover
  every required source type.
- `uv run docling-system-evaluation-data-readiness` passes
  `all_replay_source_coverage` and
  `harness_evaluation_source_coverage`.
- `uv run docling-system-agent-trace-review --limit 5 --skip-hygiene` reports
  `observation_count=0`.

Stop conditions:

- The replay suites require search-quality tuning unrelated to missing data to
  reach completed state.
- Harness evaluation cannot be persisted without broadening scope into new
  API/runtime work.

### Milestone 3: Retrieval-Learning Materialization And Final Readiness Gate

Outcome label: resolved

Purpose: materialize the final DB-backed learning artifacts needed to make the
readiness report fully green on the rebuilt local database.

Scope:

- Materialize retrieval-learning judgments and a completed training run from
  the governed court-grade source families.
- Link the materialization to the persisted harness evaluation when available.
- Regenerate the readiness report and verify zero blocker keys remain.

Acceptance:

- `uv run docling-system-materialize-retrieval-learning --limit 50 --source-type feedback --source-type replay --source-type claim_support_replay_alert_corpus --source-type technical_report_claim_feedback --set-name court-grade-ready-seed --created-by milestone3`
  creates at least `1` `RetrievalJudgmentSet`, `1` completed
  `RetrievalTrainingRun`, and at least `25` training examples.
- `uv run docling-system-evaluation-data-readiness --output storage/evaluation_data_readiness.latest.json`
  reports `regression_ready=true`, `court_grade_ready=true`,
  `regression_blockers=[]`, `court_grade_blockers=[]`, and
  `failed_gate_count=0`.
- The resulting training-run payloads and readiness report still point back to
  governed feedback, replay, claim-feedback, and replay-alert evidence instead
  of local-only bootstrap shortcuts.

Stop conditions:

- Retrieval-learning materialization can only pass by dropping one of the
  governed source families or by lowering thresholds.
- The final report is green but a focused integrity test shows missing source
  provenance or mismatched counts.

### Milestone 4: Docs, Handoff, And Closeout Routing

Outcome label: resolved

Purpose: make the achieved DB repopulation path discoverable and auditable for
future fresh rebuilds.

Scope:

- Refresh the active plan doc with executed results and commit hashes.
- Refresh `docs/evaluation_data_readiness.md` with the final court-grade-ready
  rebuild path.
- Refresh `README.md` if the operator command sequence changes.
- Refresh `docs/agentic_architecture_index.md` and `docs/SESSION_HANDOFF.md`
  so future sessions route from the closed blocker state rather than the
  current partial baseline.

Acceptance:

- The plan, readiness doc, architecture index, and handoff all agree on the
  final command sequence and final readiness result.
- The final report artifact path is named in the handoff.
- Any accepted residual risk is explicitly routed to a later milestone or
  follow-on plan.

Stop conditions:

- The docs can only be made to agree by hiding blocker counts or omitting the
  final readiness artifact.

## Required Implementation Artifacts

- A deterministic court-grade bootstrap owner, preferably as a sibling to the
  regression bootstrap owner.
- Tracked court-grade seed artifacts under `docs/evaluation_bootstrap/` or an
  equally durable repo-owned location.
- Focused integration tests for the new bootstrap step and its mixed-state
  refusal behavior.
- Updated readiness report artifact at
  `storage/evaluation_data_readiness.latest.json`.
- Updated plan / handoff / architecture index docs describing the final path.

## Required Documentation And Handoff Updates

- This plan
- `docs/evaluation_data_readiness.md`
- `docs/SESSION_HANDOFF.md`
- `docs/agentic_architecture_index.md`
- `README.md` if commands or operator steps change
- any focused runbook or schema doc that becomes the source of truth for the
  new bootstrap artifacts

## Required Verification Gates

- `uv run docling-system-bootstrap-regression-readiness`
- the new court-grade bootstrap command or typed-service equivalent
- `uv run docling-system-evaluation-data-readiness --output storage/evaluation_data_readiness.latest.json`
- `uv run docling-system-run-replay-suite feedback --limit 25`
- `uv run docling-system-run-replay-suite technical_report_claim_feedback --limit 25`
- `uv run docling-system-eval-reranker default_v1 --baseline-harness-name default_v1 --source-type evaluation_queries --source-type feedback --source-type live_search_gaps --source-type cross_document_prose_regressions --source-type technical_report_claim_feedback --limit 25`
- `uv run docling-system-materialize-retrieval-learning --limit 50 --source-type feedback --source-type replay --source-type claim_support_replay_alert_corpus --source-type technical_report_claim_feedback --set-name court-grade-ready-seed --created-by milestone3`
- `uv run docling-system-agent-trace-review --limit 5 --skip-hygiene`
- focused bootstrap / replay / harness / retrieval-learning tests
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs`

## Acceptance Criteria

- A fresh local DB can move from empty -> regression bootstrap ->
  court-grade bootstrap -> final readiness report without manual SQL editing.
- The final readiness report contains zero court-grade blockers and zero failed
  gates.
- The operator-feedback, claim-feedback, replay-alert, replay-source,
  harness-source, and retrieval-learning lanes are all present as durable DB
  rows at or above the configured thresholds.
- The regression bootstrap remains strict about non-empty DB state.
- The court-grade bootstrap is equally strict about unexpected mixed-state DBs.
- Coverage is not weakened. If any readiness, replay, or retrieval-learning
  tests are replaced, the replacement coverage must be stricter or broader and
  must prove the old test was wrong.
- The milestone closeout commit for each implementation slice contains code,
  tests, docs, generated report artifacts, and handoff updates for that slice
  only.

## Stop Conditions

- The implementation requires schema or migration work that is not already
  supported by current model contracts.
- The repopulation path depends on local secrets, external notebooks, or
  one-off shell history instead of tracked repo artifacts.
- OpenAI quota or runtime failures make the replay / evaluation path
  nondeterministic and cannot be isolated from missing-data work.
- Verification only passes after lowering thresholds, skipping DB-backed tests,
  or deleting negative cases.

## Local Commit Closeout Policy

- Close each implementation milestone with a local atomic commit after its
  verification passes.
- Stage only the verified milestone slice.
- Leave unrelated dirty and untracked files alone.
- Include implementation, tests, docs, generated readiness artifacts, and
  handoff updates in the same milestone commit.
- Record the commit hash in `docs/SESSION_HANDOFF.md` and in this plan’s
  completed-result section when the milestone lands.
- Treat a verified but uncommitted milestone as ready-to-close, not complete.

## Residual Risks And Next Milestone Routing

- If the court-grade repopulation path closes from curated bootstrap seeds but
  still lacks fresh live operator traffic, accept that as a separate data
  freshness risk rather than a blocker for deterministic local rebuilds.
- If future reviewed query misses appear after the final readiness report is
  green, route them to a focused search-quality or retrieval-ranking packet
  instead of reopening this DB blockers plan.
- If mixed-state refusal handling becomes complex, route any follow-on runtime
  ergonomics into a separate operator bootstrap UX plan after this packet is
  closed.
