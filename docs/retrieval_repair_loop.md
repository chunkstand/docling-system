# Retrieval Repair Loop

Status: Active v1 operator and agent workflow

## Purpose

This document is the repo-local system of record for the bounded retrieval repair loop.

The loop improves search harnesses without giving an agent open-ended control over ingestion, corpus truth, or evaluation criteria. Agents may inspect, draft, verify, and prepare repairs. Humans still approve promotable changes.

## Vertical Flow

1. A persisted search request, evaluation query, feedback case, or replay regression exposes a retrieval problem.
2. `/search/requests/{id}/explain` produces a canonical request explanation when request-level evidence is needed.
3. `triage_replay_regression` evaluates candidate-vs-baseline harness behavior and writes `repair_case.json`.
4. `draft_harness_config_update` creates a bounded draft override from a source repair task.
5. `verify_draft_harness_config` runs replay verification and the comprehension gate.
6. `apply_harness_config_update` waits for human approval before writing the live override.
7. Apply runs follow-up replay/evaluation and writes `follow_up_evaluation_summary.json`.
8. The final task context links the draft, verification, applied override, and follow-up evidence.

## Canonical Artifacts

- `search_request_explanation`: returned by the explain route and embeddable in repair evidence.
- `search_harness_evaluation`: persisted DB resource returned by `GET /search/harness-evaluations/{evaluation_id}`.
- `repair_case.json`: written by `triage_replay_regression`.
- `harness_config_draft.json`: written by `draft_harness_config_update`.
- `harness_config_draft_verification.json`: written by `verify_draft_harness_config`.
- `applied_harness_config_update.json`: written by `apply_harness_config_update`.
- `follow_up_evaluation_summary.json`: written by `apply_harness_config_update` when verification provided a follow-up plan.
- `context.json`: written for each completed task as the canonical task-context envelope.

YAML sidecars may exist for operator readability, but JSON and database state are the machine-facing contracts.

## Durable Harness Evaluations

Harness comparisons are not transient API payloads. `POST /search/harness-evaluations`
creates a durable `search_harness_evaluation` record and one source row per replay
source type. Each source row links the baseline and candidate replay runs that
produced the aggregate metrics.

Inspection surfaces:

- `GET /search/harness-evaluations`
- `GET /search/harness-evaluations/{evaluation_id}`

Agent tasks should carry the `evaluation_id` forward in task output and context refs.
Verification gates reload the durable evaluation when present so the DB record, replay
runs, task context, and operator API all describe the same evidence.

## Comprehension Gate

`verify_draft_harness_config` must fail the draft if the proposal cannot explain itself.

The gate checks that:

- the draft references a completed `triage_replay_regression` source task
- the source task exposes a `search_harness_repair_case`
- the draft changes at least one bounded retrieval or reranker knob
- the changed scopes are allowed by the repair case
- the draft carries an operator rationale
- the repair case has evidence refs
- the transient draft harness can produce a descriptor
- a follow-up replay/evaluation plan exists

Passing replay metrics without passing comprehension is not sufficient for apply.

## Human Review Contract

Before approving `apply_harness_config_update`, review:

- the source `repair_case`
- the changed override keys
- the verification record
- `comprehension_gate.comprehension_passed`
- expected rollback condition
- follow-up source types and limits

After apply, review the task context fields:

- `problem`
- `evidence`
- `proposed_change`
- `predicted_risk`
- `follow_up_status`
- `metrics.follow_up_recommendation`

## Non-Goals

- no corpus-source mutation
- no evaluation-corpus weakening to make a repair pass
- no parser hardcoding as a harness repair
- no hidden prompt memory as a source of truth
- no autonomous apply without explicit approval
