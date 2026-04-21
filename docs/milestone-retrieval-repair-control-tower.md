# Milestone: Retrieval Repair Control Tower

Status: Proposed
Date: 2026-04-20
Scope: Search request diagnosis, replay regression triage, harness draft/verify/apply, and post-apply follow-up.

## Intent

Implement one vertical slice that makes the retrieval and search-harness repair loop legible to both humans and agents.

This milestone is not a generic agent-platform expansion. It deepens the existing bounded workflow:

1. inspect a failing search request or replay regression
2. explain what happened in a durable, agent-readable form
3. draft a bounded harness repair against that evidence
4. enforce a comprehension gate before apply
5. run follow-up replay and evaluation automatically
6. preserve the full problem to repair to verification chain as durable context

The result should align with the current v1 design: durable state, explicit approvals, typed context, replay-backed verification, and no hidden prompt-only memory.

## Why This Slice

This repository already has the core repair loop:

- persisted search requests and result telemetry
- replay runs and harness evaluations
- `triage_replay_regression`
- `draft_harness_config_update`
- `verify_draft_harness_config`
- `apply_harness_config_update`
- canonical task context artifacts

What is missing is legibility. The evidence is stored, but it is still too operator-grade and too raw. An agent can inspect the pieces, but the system does not yet present a canonical explanation of:

- what failed
- why it likely failed
- what lever is being changed
- what tradeoff is expected
- what evidence would prove or disprove the change

This milestone fixes that for one end-to-end vertical slice instead of adding broad introspection to every subsystem at once.

## Alignment

### Lopopolo-style alignment

- Keep humans in the steering role and agents in the execution role.
- Treat the repo, durable artifacts, and runtime metadata as the system of record.
- Improve harness engineering by making evidence, decisions, and repair loops first-class instead of implicit in chat.

### Jones-style alignment

- Make the system own the context instead of relying on the active conversation.
- Add shared readable and writable surfaces that both humans and agents can inspect.
- Add comprehension gates so speed of generation does not outrun review and understanding.

### Current repo alignment

- Preserve bounded workflows and explicit approval gates.
- Keep canonical machine-readable state in JSON artifacts and DB rows.
- Keep YAML derived and human-readable only.
- Prefer richer provenance, eval loops, and runtime evidence over more ad hoc retrieval heuristics.

## Milestone Outcome

For any failing evaluation query or replay regression in the selected harness family, the system can produce a durable repair dossier that answers four questions:

1. What happened?
2. Why does the system think it happened?
3. What exact harness change is proposed?
4. What follow-up evidence will confirm or reject the repair?

That dossier must be visible through repo-local docs, runtime endpoints, and agent-task artifacts.

## Vertical Slice

The slice starts with a concrete failed or regressed search query and ends with a verified repair attempt:

1. `search_request` or replay regression is identified
2. a canonical search explanation is produced
3. triage writes a canonical repair case
4. draft task proposes a bounded harness delta
5. verification checks both mechanics and comprehension
6. apply writes the promoted override only after approval
7. follow-up replay and evaluation run automatically
8. before and after evidence is attached back to the same task chain

This is vertical because each checkpoint includes:

- runtime artifact
- API surface
- task-context integration
- repo-local documentation
- tests

The milestone stops after this loop is strong for harness repair. It does not try to generalize across every task family yet.

## Deliverables

### 1. Repo-local system-of-record docs

Add and maintain these docs as reviewed contracts:

- `docs/retrieval_repair_loop.md`
  - authoritative workflow for diagnose, triage, draft, verify, approve, apply, and follow-up
- `docs/search_request_explanation_contract.md`
  - canonical explanation schema, field meanings, and evidence rules
- `docs/search_harness_descriptor_contract.md`
  - harness descriptor schema, knob semantics, and safe-change expectations

These docs must be updated whenever the corresponding schemas or route contracts change.

### 2. Canonical search explanation contract

Add a machine-readable explanation contract for a persisted search request:

- canonical route response: `GET /search/requests/{search_request_id}/explain`
- schema: `search_request_explanation`
- canonical embedded task evidence: JSON
- optional future derived artifact: `search_request_explanation.json`

Suggested schema:

- `schema_name`
- `schema_version`
- `search_request_id`
- `query`
- `origin`
- `filters`
- `requested_mode`
- `served_mode`
- `harness_name`
- `harness_config_snapshot`
- `reranker_name`
- `reranker_version`
- `embedding_status`
- `fallback_reason`
- `candidate_source_breakdown`
- `keyword_candidate_count`
- `semantic_candidate_count`
- `metadata_candidate_count`
- `context_expansion_count`
- `query_understanding`
- `top_result_snapshot`
- `diagnosis`
- `recommended_next_action`
- `evidence_refs`

The key addition is `diagnosis`, which should classify the observed behavior using a bounded taxonomy such as:

- `healthy`
- `low_recall`
- `bad_ranking`
- `fallback_only`
- `filter_overconstraint`
- `table_recall_gap`
- `metadata_bias`
- `unknown`

This explanation should be buildable from persisted runtime evidence, not prompt-only analysis.

### 3. Canonical repair case artifact

Extend `triage_replay_regression` so it writes a durable repair dossier instead of only a thin summary:

- canonical: `repair_case.json`
- schema: `search_harness_repair_case`

Suggested schema:

- `schema_name`
- `schema_version`
- `evaluation_id`
- `replay_run_id`
- `query_key`
- `baseline_search_request_id`
- `candidate_search_request_id`
- `failure_classification`
- `problem_statement`
- `observed_metric_delta`
- `baseline_explanation_ref`
- `candidate_explanation_ref`
- `affected_result_types`
- `likely_root_cause`
- `allowed_repair_surface`
- `blocked_repair_surfaces`
- `recommended_next_action`
- `evidence_refs`

This becomes the durable handoff between diagnosis and repair.

### 4. Search harness descriptor surface

Add a descriptor surface for each harness family so the system can explain itself before changing itself.

Suggested route:

- `GET /search/harnesses/{harness_name}/descriptor`

Suggested payload:

- harness identity and version
- config fingerprint
- retrieval stages enabled
- reranker used
- major tunable knobs
- constraints and invariants
- intended query families
- known tradeoffs
- linked evaluation corpus or replay suite expectations

This descriptor should be derived from code and config, not maintained as hand-written shadow state.

### 5. Search request explanation surface

Add a human and agent readable route over persisted runtime evidence:

- `GET /search/requests/{search_request_id}/explain`

This route should return the same canonical explanation schema used in task
context and repair evidence so humans, agents, and tests are all looking at the
same contract. If explanation sidecars are added later, they must be derived
from the route/schema contract rather than becoming a separate source of truth.

### 6. Comprehension gate before apply

The current repair loop verifies whether a draft passes replay-oriented checks. This milestone should go further and verify whether the proposed repair is understandable and justified.

Do this by extending `verify_draft_harness_config`, not by creating an open-ended new planner.

The verification output should explicitly answer:

- what failed
- what config field is changing
- why that field is the relevant lever
- what evidence supports the change
- what tradeoff is expected
- what could regress
- what follow-up evidence will be used

Suggested additions to `harness_config_draft_verification.json`:

- `comprehension_passed`
- `claim_evidence_alignment`
- `change_justification`
- `predicted_blast_radius`
- `rollback_condition`
- `follow_up_plan`

The comprehension gate fails if any of these are true:

- the draft changes knobs not named in the repair case
- claims are unsupported by evidence refs
- the task cannot name expected gains and plausible regressions
- required context refs are stale, missing, or schema-mismatched
- the repair surface exceeds the allowed bounded change scope

### 7. Automatic follow-up replay and evaluation

After `apply_harness_config_update` succeeds, the system should automatically queue follow-up replay and evaluation work against the same target corpus or replay suite and attach the results to the repair chain.

Required follow-up outputs:

- `follow_up_replay_summary.json`
- `follow_up_evaluation_summary.json`
- before and after metric comparison
- regression count delta
- explicit pass or fail recommendation for keeping the override

This closes the loop and prevents one-off repair attempts from ending at "applied".

### 8. Human-readable repair narrative in task detail

Enrich the existing task detail and context surfaces so the repair chain is understandable without opening multiple raw artifacts.

For harness-repair tasks, the task detail should always expose:

- `problem`
- `evidence`
- `proposed_change`
- `predicted_risk`
- `verification_status`
- `follow_up_status`
- `next_action`

This can be additive to the current `context_summary` contract.

## Implementation Strategy

Build this milestone in three vertical checkpoints.

### Checkpoint 1: Explain the failure

Goal:
Make one persisted search request or replay regression self-explaining.

Ship:

- `SearchRequestExplanation` schema
- explanation builder from persisted search-request evidence
- `GET /search/requests/{id}/explain`
- docs for the explanation contract
- tests for healthy, fallback, and regression cases

Acceptance:

- a human can understand why a request behaved the way it did without reading raw DB rows
- an agent-task can consume the explanation via context refs

### Checkpoint 2: Turn explanation into a repair case and gate

Goal:
Make triage and draft outputs legible and bounded.

Ship:

- `repair_case.json` from `triage_replay_regression`
- richer task context for triage and draft tasks
- harness descriptor route
- extended `verify_draft_harness_config` with comprehension fields
- docs for repair case and harness descriptor contracts

Acceptance:

- every draft references a repair case and a harness descriptor
- a draft cannot pass verification without claim and evidence alignment

### Checkpoint 3: Close the loop automatically

Goal:
Make repair evidence durable after apply.

Ship:

- automatic post-apply replay and evaluation wiring
- follow-up summary artifacts
- task-detail narrative fields for repair chains
- route tests and end-to-end integration coverage

Acceptance:

- every applied harness repair has before and after evidence
- every applied repair can be reviewed from one task chain without manual artifact hunting

## Required Schema and Task Changes

### Extend, do not replace, current workflow tasks

Prefer deepening the existing tasks:

- extend `triage_replay_regression`
- extend `draft_harness_config_update`
- extend `verify_draft_harness_config`
- extend `apply_harness_config_update`

Avoid introducing a parallel repair framework. The existing task graph is already the right bounded substrate.

### Additive route policy

All new runtime surfaces should be additive:

- keep existing detail routes stable
- add new explanation and descriptor routes
- enrich task detail responses with additive fields only

### Artifact policy

- JSON is canonical
- YAML is derived
- every new artifact should carry explicit schema metadata
- every new artifact should be referenceable from task context with freshness checks

## Comprehension Gate Rules

The comprehension gate is the core control point in this milestone.

A repair proposal is comprehensible only if it can satisfy all of these:

1. It can restate the failure in system terms, not only operator intuition.
2. It can identify the specific harness lever being changed.
3. It can connect that lever to observed evidence from persisted search behavior.
4. It can name a plausible upside and a plausible downside.
5. It can define what follow-up evaluation will prove success or failure.
6. It stays inside an allowed bounded repair surface.

This gate is intentionally stricter than "the replay numbers improved once." It is meant to slow down opaque changes and speed up trustworthy ones.

## Non-Goals

- no broad multi-agent orchestration work
- no generalized task introspection for every action family
- no replacement of the current approval model
- no attempt to solve all retrieval diagnosis classes in one milestone
- no UI-first redesign before the API and artifact contracts are stable

## Verification Plan

Add verification at three levels.

### Unit

- explanation builder classification
- repair-case construction
- comprehension gate pass and fail paths
- harness descriptor generation

### HTTP boundary

- `GET /search/requests/{id}/explain`
- `GET /search/harnesses/{name}/descriptor`
- handled error paths for missing requests, missing harnesses, and missing artifacts

### Integration

Run one end-to-end harness-repair scenario:

1. replay regression detected
2. triage writes repair case
3. draft proposes bounded override
4. comprehension verification passes
5. approval and apply succeed
6. automatic follow-up replay and evaluation run
7. before and after evidence is visible from task detail and artifacts

## Success Criteria

The milestone is complete when all of these are true:

- a failing query can be explained from one canonical artifact
- a harness repair proposal cannot reach apply without a passed comprehension gate
- every applied repair has linked before and after evidence
- the runtime exposes stable, agent-readable surfaces for explanation and harness description
- repo-local docs explain the same contracts the runtime uses
- the repair chain is legible to a human without reading raw internal tables

## Recommended First PR Cut

Start with Checkpoint 1 only:

- explanation schema
- explanation builder
- explanation endpoint
- explanation contract doc
- tests

That is the smallest cut that materially improves legibility while preserving the current workflow and gives the later repair-case and comprehension-gate work a concrete evidence contract to build on.
