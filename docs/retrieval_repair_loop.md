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
- `search_harness_release_gate`: persisted release decision returned by `GET /search/harness-releases/{release_id}`.
- `search_harness_release_readiness_assessment`: immutable DB resource that freezes the live release-readiness decision, blocker details, lineage remediation, linked audit bundle, linked validation receipt, payload hashes, and semantic governance event.
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
- `docling-system-search-harness-evaluation-list`
- `docling-system-search-harness-evaluation-show <evaluation_id>`
- the evaluation UI's recent durable harness-evaluation history panel

Agent tasks should carry the `evaluation_id` forward in task output and context refs.
Verification gates reload the durable evaluation when present so the DB record, replay
runs, task context, and operator API all describe the same evidence.

## Durable Release Gates

Harness release checks are persisted as first-class gate records. `POST
/search/harness-releases` evaluates one durable `search_harness_evaluation` against
operator thresholds and writes a `search_harness_release_gate` record with:

- the candidate and baseline harness names
- the source types and replay thresholds used by the decision
- pass/fail/error outcome, aggregate metrics, per-source details, and failure reasons
- an evaluation snapshot captured at decision time
- `release_package_sha256`, a stable hash over the evaluation snapshot and gate package

Inspection surfaces:

- `GET /search/harness-releases`
- `GET /search/harness-releases/{release_id}`
- `GET /search/harness-releases/{release_id}/readiness`
- `POST /search/harness-releases/{release_id}/readiness-assessments`
- `GET /search/harness-releases/{release_id}/readiness-assessments/latest`
- `GET /search/harness-releases/{release_id}/readiness-assessments/{assessment_id}`
- `POST /search/harness-releases/{release_id}/audit-bundles`
- `GET /search/harness-releases/{release_id}/audit-bundles/latest`
- `POST /search/retrieval-training-runs/{training_run_id}/audit-bundles`
- `GET /search/retrieval-training-runs/{training_run_id}/audit-bundles/latest`
- `GET /search/audit-bundles/{bundle_id}`
- `POST /search/audit-bundles/{bundle_id}/validation-receipts`
- `GET /search/audit-bundles/{bundle_id}/validation-receipts`
- `GET /search/audit-bundles/{bundle_id}/validation-receipts/latest`
- `GET /search/audit-bundles/{bundle_id}/validation-receipts/{receipt_id}`
- `docling-system-gate-search-harness-release <candidate_harness_name>`, which now
  prints both the evaluation and persisted release gate
- `docling-system-search-harness-release-audit-bundle <release_id>`, which exports a
  signed immutable audit bundle for a persisted release gate
- `docling-system-retrieval-training-run-audit-bundle <training_run_id>`, which
  exports a signed immutable audit bundle for a materialized retrieval training run
- `docling-system-audit-bundle-validation-receipt <bundle_id>`, which validates a
  signed bundle and emits a signed receipt plus a PROV JSON-LD export
- `verify_search_harness_evaluation`, which writes a release gate when the target
  evaluation is durable and links the `release_id` in verifier details

Passing a release gate is evidence that the candidate met the configured retrieval
guardrails. It does not mutate corpus truth, weaken evaluation fixtures, or silently
promote parser behavior.

## Retrieval Learning Candidate Gates

The learning ledger now has a governed handoff into harness evaluation. `POST
/search/retrieval-learning/candidate-evaluations` binds a completed
`retrieval_training_run` to a candidate harness evaluation and a persisted release
gate. The resulting `retrieval_learning_candidate_evaluation` record stores:

- the training run, judgment set, dataset hash, and example counts used as learning input
- the candidate and baseline harness names, source types, and replay limit
- the durable `search_harness_evaluation_id` and `search_harness_release_id`
- gate thresholds, metrics, reasons, evaluation/release snapshots, and `learning_package_sha256`
- a `retrieval_learning_candidate_evaluated` governance event for trace replay

Inspection surfaces:

- `GET /search/retrieval-learning/candidate-evaluations`
- `GET /search/retrieval-learning/candidate-evaluations/{candidate_evaluation_id}`
- `POST /search/retrieval-learning/reranker-artifacts`
- `GET /search/retrieval-learning/reranker-artifacts`
- `GET /search/retrieval-learning/reranker-artifacts/{artifact_id}`
- `docling-system-evaluate-retrieval-learning-candidate <candidate_harness_name>`
- `docling-system-create-retrieval-reranker-artifact <candidate_harness_name>`

This pass intentionally records the learning influence and gate decision without
turning handcrafted query rules into the accuracy engine. Reranker artifacts now use
the same ledger to persist a versioned data-derived scorer candidate, evaluate it
through a bounded harness override and release gate, and store a change-impact report
that links the ranking artifact to training sources, active semantic governance, and
any affected evidence traces or claims.

Retrieval training run audit bundles freeze the full learning input: the training run
record, judgment set, canonical training payload, every judgment row, every hard
negative row, source payload hashes, evidence refs, semantic governance events, and a
PROV-style graph. When the governed claim-support replay-alert corpus is included as a
learning source, each corpus-derived judgment and hard negative carries the active
snapshot hash, governance event/artifact/receipt, promotion lineage, source
policy-change impact IDs, escalation event IDs, fixture hash, hard-case kind, expected
verdict, and evidence-card references. Training audit bundles also elevate that source
chain into first-class corpus sections for snapshots, rows, promotion artifacts,
promotion events, replay escalation events, and snapshot-governance artifacts/events.
The bundle integrity block rechecks snapshot hashes, row fixture hashes, frozen
training-reference-to-current-row identity, artifact receipt hashes, governance-event
hash integrity, and source lineage resolution, and the PROV graph derives the training
dataset from the corpus rows and their governance sources. Search harness release audit bundles include any linked
`retrieval_learning_candidate_evaluations`, the referenced training runs and judgment
sets, any linked `retrieval_reranker_artifacts`, the artifact payload hashes,
change-impact report hashes, the associated governance events, and references to the
latest signed training audit bundle hash for each linked training run. If a linked
completed training run has no current matching training audit bundle, release-bundle
export freezes one before signing the release bundle; for replay-alert corpus sources,
the matching check recomputes current corpus lineage and fails the release checklist if
the signed training bundle no longer matches the governed corpus rows it cites.
Release-bundle export also validates every linked training audit bundle and embeds the resulting
validation-receipt references before signing, then validates the signed release bundle
itself so the release readiness gate can pass without a separate receipt step.
Validation receipts are immutable database rows with canonical `receipt.json`,
standards-facing `prov.jsonld`, schema/source/integrity/semantic-governance check
flags, receipt hash, PROV export hash, and HMAC signature. Release audit bundles carry
a machine-checkable semantic governance policy profile. If a release claims semantic
coverage by linking active semantic state, the policy requires ontology and semantic
graph snapshot references plus a closed governance-event hash chain. The release
readiness endpoint combines retrieval gate status, latest release audit bundle status,
release validation receipt status, and semantic governance policy status into one
live document-generation gate. It also returns a machine-readable diagnostics envelope
with latest validation errors, failed audit-checklist keys, linked training-bundle
lineage match checks, blocker details with normalized reason codes, and replay-alert
corpus remediation items so operators can see which training run, audit bundle, and
corpus source need repair before retrying the release audit export.

When a release readiness decision needs to be used as court-facing generation input,
operators freeze the live readiness result with `POST
/search/harness-releases/{release_id}/readiness-assessments`. The resulting
`search_harness_release_readiness_assessment` row is immutable, links the release,
latest release audit bundle, latest validation receipt, and semantic governance
event, stores the full readiness payload plus assessment wrapper, and records stable
SHA-256 hashes for both. Assessment detail responses include an `integrity` envelope
that recomputes the stored readiness/assessment payload hashes and checks that the
embedded release, audit-bundle, validation-receipt, readiness-status, and blocker
links still match the row. `GET /search/harness-releases/{release_id}/readiness`
stays live and reports the latest frozen assessment reference when one exists.
Downstream document generation now treats that frozen assessment as a hard
consuming boundary. `prepare_report_agent_harness` binds every source search
request in the document-generation context pack to the latest passed release for
that harness and records the frozen readiness assessment ID, payload hash,
selection status, linked audit bundle, linked validation receipt, and integrity
result in `audit_refs.release_readiness_assessments`.
`evaluate_document_generation_context_pack` fails when any source search request
lacks a ready, integrity-complete assessment, when the frozen assessment is
blocked, when its stored hashes no longer verify, when it is stale relative to
the latest release audit bundle or validation receipt, or when the context-pack
ref differs from the canonical DB-derived assessment ref. The DB-bound gate also
rejects duplicate, unexpected, and malformed readiness refs, so the release
authorization set must exactly cover the source search requests consumed by the
generation pack. Technical-report audit bundles, evidence manifests, evidence
traces, and PROV exports carry the same assessment refs, the DB-derived gate
summary, and provenance edges so court-facing generated documents can prove
which release-readiness decision authorized the retrieval evidence and whether
the latest database check exactly covered every consumed source search request.
The database enforces that audit bundle source IDs match their concrete release
or training-run foreign keys. That keeps
the signed release package traceable from release gate back to the exact
auditable dataset that influenced the candidate, and gives downstream
document-generation workflows a court-facing receipt they can re-check
independently of the bundle payload.

## Multivector Retrieval Repair Surface

`multivector_v1` is available as a bounded search harness for high-accuracy retrieval experiments. It adds persisted retrieval evidence span multivectors and a late-interaction max-sim candidate stage without changing canonical chunk, table, or span truth.

Repair agents may tune whether a derived harness enables late interaction and its candidate limits through descriptor-listed retrieval-profile overrides. They must still verify against durable replay or evaluation evidence. A late-interaction improvement is auditable only when the resulting search request retains the per-span max-sim trace in persisted result-span metadata, the evidence package materializes the referenced span-vector rows with content and embedding hashes, and the multivector generation operator is present in the package trace graph.

Failed multivector regeneration must not erase the last valid vector set for a run. The system records the failed generation attempt as an `embed` operator run, preserves existing `retrieval_evidence_span_multivectors`, and only swaps vectors after replacement embeddings pass count and dimension validation.

Audit bundles are stored under `storage/audit_bundles/`, persisted in
`audit_bundle_exports`, and include a PROV-style graph plus HMAC-SHA256 signature
metadata. `DOCLING_SYSTEM_AUDIT_BUNDLE_SIGNING_KEY` must be configured before
creating a signed bundle. The database treats audit bundle exports as append-only:
`audit_bundle_exports` has a Postgres trigger that rejects row updates and deletes,
so corrections require a new signed bundle instead of mutating the prior record.
Technical-report verification uses the same signing key for frozen PROV export
receipts. A report audit bundle is complete only when the receipt hash chain and
HMAC signature verify against the stored evidence manifest, trace, and frozen
PROV payload.

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
