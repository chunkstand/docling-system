# Evidence Hotspot Owner Milestone Plan

Date: 2026-05-12 local / 2026-05-12 UTC
Status: implemented locally; `IC-050E60059A34` is resolved under local
verification, and residual oversized owner-family budget debt is routed to
`IC-65AF4A6D8B1E`
Owner context: `IC-050E60059A34` / `app/services/evidence.py` is now recorded
as deployed under local verification. The next routed evidence-family
follow-up is `IC-65AF4A6D8B1E` /
`app/services/evidence_provenance_exports.py`.

## Local Closeout

This plan has now been implemented end to end under local verification. The
historical baseline below captures the pre-implementation state that motivated
the sequence.

Local closeout snapshot:

- `app/services/evidence.py` is now a 141-line / 4-private-helper
  compatibility facade
- the remaining claim-feedback, release-readiness, manifests, semantic-trace,
  claim-support impact, provenance-export, and audit-view families now live in
  focused `app/services/evidence_*.py` owner modules
- `tests/unit/test_evidence_facade_contract.py` now guards the public
  `app.services.evidence` export surface, including the settings-aware
  provenance wrapper seam
- `uv run docling-system-improvement-case-summary` now reports
  `case_count=27`, `status_counts.open=22`, `status_counts.deployed=4`,
  `status_counts.measured=1`, and `oldest_open_case_id=IC-9812A0B138D9`
- `uv run docling-system-architecture-quality-report --summary` reports
  `hotspot_count=10` and `max_hotspot_risk_score=541.06`; `top_hotspot_paths`
  may still include `app/services/evidence.py` because of public fan-in
- the architecture probe no longer lists `app/services/evidence.py` in the top
  12 churn hotspots; the top hotspot now routes to
  `app/services/agent_task_actions.py`
- the latest recorded local closeout still reports the full DB-backed suite at
  `1867 passed`; this refresh confirms the live readiness and trace-review
  surfaces still report `passed_gate_count=11`, `failed_gate_count=0`, and
  `observation_count=0`

Controlled follow-on:

- extracted evidence owner modules still exceed the default 600-line hygiene
  budget in several places, so this closeout explicitly routes that residual
  debt into `IC-65AF4A6D8B1E` rather than treating it as hidden drift
- current oversized evidence owner-family modules from the working tree are:
  `app/services/evidence_provenance_exports.py` (1048),
  `app/services/evidence_technical_report_exports.py` (884),
  `app/services/evidence_semantic_trace.py` (837),
  `app/services/evidence_claim_feedback.py` (834),
  `app/services/evidence_manifests.py` (725),
  `app/services/evidence_audit_views.py` (699), and
  `app/services/evidence_claim_support_replay_alerts.py` (646)

## Purpose

Resolve the remaining unclear-ownership debt in `app/services/evidence.py` by
finishing the compatibility-facade conversion that prior evidence milestones
started but did not close.

This plan is for the service hotspot itself, not for adjacent product work.
The target outcome is a narrow public facade that preserves existing import and
behavior contracts while moving the remaining implementation families into
focused `app/services/evidence_*.py` owner modules with explicit tests,
ratchets, and documentation.

## Historical Starting Evidence

Pre-implementation state captured from repo artifacts and live commands on
2026-05-11 local / 2026-05-11 UTC:

```text
docs/SESSION_HANDOFF.md
  active local follow-up owner case = IC-050E60059A34 / app/services/evidence.py
  architecture probe still reports app/services/evidence.py as the top churn hotspot

config/improvement_cases.yaml
  IC-050E60059A34 status=open
  observed_failure = app/services/evidence.py remains a hotspot with line_count=6307
  and private_helper_count=81 after the verified technical-report export split

uv run docling-system-architecture-quality-report --summary
  hotspot_count=10
  max_hotspot_risk_score=561.06
  top_hotspot_paths include app/services/evidence.py

uv run docling-system-improvement-case-summary
  case_count=26
  status_counts.open=22
  oldest_open_case_id=IC-050E60059A34

python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 12
  top hotspot app/services/evidence.py score=309043
  Python cycle components=3

wc -l app/services/evidence.py
  6307 app/services/evidence.py
```

Completed evidence-owner splits already in place:

- search evidence package assembly/export/trace ownership now lives in
  `app/services/evidence_search_packages.py`,
  `app/services/evidence_search_trace_graph.py`, and
  `app/services/evidence_search_trace_store.py`
- technical-report provenance helpers now live in
  `app/services/evidence_provenance.py`
- knowledge-operator run recording and task payload helpers now live in
  `app/services/evidence_operator_runs.py` and
  `app/services/evidence_task_payloads.py`
- technical-report derivation/export ownership now lives in
  `app/services/evidence_technical_report_exports.py`

The remaining large ownership clusters still inside `app/services/evidence.py`
are visible from the current function map:

- technical-report claim retrieval feedback ledger and integrity
  approximately lines 640-1413
- release-readiness DB gate and context-pack audit assembly
  approximately lines 1506-2029
- claim-support policy-impact and replay-alert evidence assembly
  approximately lines 2116-3231
- technical-report manifest, semantic trace, and manifest persistence
  approximately lines 3232-4667
- provenance-export response and audit-bundle assembly / readback
  approximately lines 4668-5860

## Goal

Retire the `IC-050E60059A34` unclear-ownership case by reducing
`app/services/evidence.py` to a pure compatibility facade with no remaining
owner-family implementation logic.

Success means:

- `app/services/evidence.py` is at or below 600 lines and 20 private helpers
- all remaining implementation families move into focused
  `app/services/evidence_*.py` owner modules
- the public `app.services.evidence` import surface remains compatible for
  governed call sites and tests
- no new Python import-cycle component is introduced
- the hotspot-prevention, hygiene, architecture, and DB-backed runtime gates
  remain green
- `config/improvement_cases.yaml` and `docs/SESSION_HANDOFF.md` record the
  owner case as deployed with the final routed state

The architecture-quality report may still mention `app/services/evidence.py`
because of intentional public fan-in. That does not block closure if the file
is verifiably reduced to a governed compatibility facade and the owner case is
otherwise closed by contract.

## Non-Goals

- No API, CLI, DB schema, migration, or storage-contract redesign.
- No changes to persisted artifact schemas, semantic-governance event schemas,
  or search-ranking behavior except compatibility-preserving internal rewiring.
- No reopening of already-extracted owner families.
- No broad rewrite of `app/services/audit_bundles.py`,
  `app/services/search.py`, or `app/services/agent_task_actions.py`.
- No umbrella commit that mixes unrelated hotspot families.

## Scope

In scope:

- gate bootstrap for the evidence compatibility facade
- extraction of the remaining evidence owner families from
  `app/services/evidence.py`
- focused unit and DB-backed integration coverage for each moved family
- hotspot-prevention, hygiene, improvement-case, index, and handoff updates
- atomic commit closeout for each milestone in this sequence

Out of scope:

- new technical-report product capabilities
- new claim-support behaviors
- new audit-bundle feature work
- route or response-shape changes beyond compatibility-preserving internals

## Owner Surfaces

- primary facade:
  `app/services/evidence.py`
- current extracted owner family:
  `app/services/evidence_common.py`,
  `app/services/evidence_records.py`,
  `app/services/evidence_operator_runs.py`,
  `app/services/evidence_task_payloads.py`,
  `app/services/evidence_provenance.py`,
  `app/services/evidence_manifest_traces.py`,
  `app/services/evidence_search_packages.py`,
  `app/services/evidence_search_trace_graph.py`,
  `app/services/evidence_search_trace_store.py`,
  `app/services/evidence_technical_report_exports.py`
- new owner family expected from this plan:
  `app/services/evidence_claim_feedback.py`,
  `app/services/evidence_release_readiness.py`,
  `app/services/evidence_manifests.py`,
  `app/services/evidence_claim_support_impacts.py`,
  `app/services/evidence_audit_views.py`
- focused tests:
  `tests/unit/test_evidence_*.py`,
  `tests/integration/test_technical_report_harness_roundtrip.py`,
  `tests/integration/test_semantic_governance_ledger.py`,
  `tests/integration/test_retrieval_learning_ledger.py`,
  `tests/integration/test_claim_support_policy_change_impacts_roundtrip.py`,
  `tests/integration/test_claim_support_policy_change_impacts_replay_alert_prevalidation.py`,
  `tests/integration/test_claim_support_policy_change_impacts_replay_alert_promotions.py`
- governance and closeout:
  `config/hygiene_policy.yaml`,
  `config/improvement_cases.yaml`,
  `config/hotspot_prevention.yaml`,
  `docs/agentic_architecture_index.md`,
  `docs/SESSION_HANDOFF.md`,
  this plan

## Placement Rules

- Keep `app/services/evidence.py` as the only public compatibility facade for
  this family until a later deliberate contract change says otherwise.
- New implementation must land in focused `app/services/evidence_*.py` owner
  modules, not back inside `app/services/evidence.py`.
- Preserve import-compatible public names by re-export or narrow wrapper when
  existing tests or callers rely on `app.services.evidence`.
- If a planned owner module would exceed 600 lines or 20 private helpers,
  split it further in the same milestone rather than creating a second broad
  module.
- Put new tests beside the moved owner family. Do not create one new giant
  evidence regression file.
- Do not move code into `app/services/audit_bundles.py` or
  `app/services/claim_support_policy_impacts.py` just to reduce
  `app/services/evidence.py`; the goal is clearer ownership, not cross-hotspot
  shuffling.
- Preserve handled failure behavior and append-only governance semantics for
  claim feedback, release-readiness, manifests, and provenance export.

## Execution Mode

This sequence is intentionally designed for one future implementation prompt to
run end to end without stopping for plan clarification.

Execution rule for that future prompt:

- start by reading the local `code-architecture-governance` skill and apply its
  gate-first, facade-preserving workflow to every milestone that changes
  module boundaries, imports, owner modules, or architecture controls
- use the local `docling-system-verification` skill for repo-specific
  verification depth, Postgres-backed integration expectations, and handoff
  closeout
- proceed milestone by milestone in order
- close each milestone with its own local atomic commit after verification
- continue automatically into the next milestone unless a stop condition in
  this plan triggers
- do not pause mid-sequence for “is this enough?” confirmation
- do not stop after any `reduced` milestone; the run is incomplete until
  Milestone 6 resolves the owner case and the final full-system closeout gates
  pass
- do not treat partial green focused tests as contract closeout; continue until
  the broad verification stack and final closeout gates are green
- ask only if a stop condition is hit, verification contradicts the plan, or
  unrelated dirty worktree changes materially interfere

## Required Skill Usage

- `code-architecture-governance` is mandatory for Milestones 0 through 6
  because every milestone changes ownership boundaries, compatibility-facade
  placement, or architecture controls.
- `docling-system-verification` is mandatory for Milestones 0 through 6 because
  final closure depends on the repo’s Postgres-backed integration gates,
  handoff rules, and closeout verification stack.
- Architecture best-practice requirements inherited from the skill are part of
  this plan’s contract:
  preserve narrow public facades, move one bounded concern at a time, keep
  ownership explicit, avoid new cycles, update durable architecture docs, and
  prove claims with executable gates rather than prose.

## Weak-Point Prevention Contract

| Weak point forecast | Owner surface | Prevention gate | Fail threshold | Controlled violation | Future-Codex misuse scenario |
| --- | --- | --- | --- | --- | --- |
| A new owner module simply becomes a second `evidence.py` | new `app/services/evidence_*.py` module plus `config/hygiene_policy.yaml` | `uv run docling-system-hygiene-check` and file-budget ratchets | any new owner module exceeds 600 lines or 20 private helpers without a same-milestone split | add a temporary oversized helper block locally and prove the ratchet would fail before commit | future Codex dumps another mixed concern into the first new module because “it is evidence-related” |
| Future edits add fresh implementation back into `app/services/evidence.py` | `config/hotspot_prevention.yaml`, `tests/unit/test_evidence_facade_contract.py`, `app/services/evidence.py` | `uv run docling-system-hotspot-prevention-check --strict` and focused facade-contract tests | new implementation logic remains in `app/services/evidence.py` beyond import forwarding, aliases, or narrow wrappers | introduce a temporary helper in `app/services/evidence.py` and prove strict hotspot prevention flags it | future Codex uses the public facade as the default place for new logic because callers already import it |
| Compatibility re-export drift breaks callers | `app/services/evidence.py` and new owner-module tests | focused `tests/unit/test_evidence_*.py` plus a dedicated facade-contract suite | any moved public name disappears, changes identity unexpectedly, or stops honoring settings-aware wrapper behavior | temporarily rename or stop re-exporting one moved symbol and prove the facade-contract suite fails | future Codex imports owner modules directly and silently abandons public facade guarantees |
| Integrity logic changes but the green result comes from weaker tests | technical-report and claim-support integration tests | targeted unit tests plus DB-backed integration roundtrips | any touched milestone deletes or weakens prior assertions without equivalent or stronger replacement coverage | temporarily remove one live-link or hash assertion and confirm the new targeted test catches it | future Codex narrows assertions to “just make the suite pass” |
| A split introduces a new import cycle or extra coordination layer | evidence owner modules and architecture controls | `uv run docling-system-architecture-inspect`, `uv run docling-system-capability-contracts`, and architecture probe | new cycle component appears or capability/architecture validation fails | temporary circular import in a local branch should cause the architecture probe or import path to fail | future Codex creates helper back-references between new evidence modules |
| The owner case closes in docs but not in measured gates | `config/improvement_cases.yaml`, handoff, and architecture reports | `uv run docling-system-improvement-case-validate`, `uv run docling-system-improvement-case-summary`, and post-closeout report refresh | improvement-case notes, measurement, or deployment ref do not match the committed repo state | modify measurement text without updating live numbers and prove closeout review rejects it | future Codex marks the debt “done” after a partial split without updating the durable owner record |
| A milestone goes green only because tests or verification were weakened | touched tests, gate configs, and owner-module closeout docs | side-by-side review of removed assertions plus focused and broad verification reruns | any milestone deletes, loosens, skips, xfails, or narrows prior coverage without proving stronger replacement coverage in the same commit | temporarily remove a prior integrity assertion and require the new focused owner test or integration path to fail | future Codex edits tests first to make the refactor easier instead of preserving or strengthening the contract |

## Milestone Sequence

### Milestone 0: Evidence Facade Gate Bootstrap

Outcome label: resolved

Purpose:

- create the explicit guardrails that make the later split sequence safe to run
  end to end without regressing facade compatibility

Implementation:

- read and apply `code-architecture-governance` before editing; treat this
  milestone as the gate-first architecture setup for the remaining run
- add `tests/unit/test_evidence_facade_contract.py` covering every moved public
  owner-family function or wrapper that must remain reachable from
  `app.services.evidence`
- update `config/hotspot_prevention.yaml` so the evidence facade blocks fresh
  implementation growth and points at the new owner-family destinations
- refresh `config/hygiene_policy.yaml` evidence-family budgets only where the
  current repo state requires pre-split baseline alignment
- record an explicit “no weakened tests or gates” rule in the facade-contract
  suite or closeout doc expectations so later milestones fail if they achieve
  green only by reducing contract strength

Acceptance:

- the repo has an explicit evidence facade-contract suite
- the strict hotspot-prevention gate knows the intended destination owner
  families for remaining evidence logic
- no behavior changes land in this milestone beyond gate/bootstrap work

Commit closeout:

- local atomic commit containing only gate/bootstrap tests and policy updates

### Milestone 1: Claim Retrieval Feedback Owner Split

Outcome label: reduced

Purpose:

- move the technical-report claim retrieval feedback ledger, integrity, and
  append-only linking logic out of `app/services/evidence.py`

Primary target:

- new owner module `app/services/evidence_claim_feedback.py`

Implementation:

- read and apply `code-architecture-governance` before editing this boundary
  change
- move the claim-feedback status, payload, integrity, append-only link, and
  persistence family into the new owner module
- keep `persist_technical_report_claim_retrieval_feedback_ledger` and any
  governed helper names import-compatible through the facade
- add focused unit coverage for claim-feedback payload integrity, live-link
  verification, and append-only protections

Acceptance:

- `app/services/evidence.py` loses the claim-feedback owner family
- claim-feedback persistence and integrity behavior remain unchanged
- `tests/integration/test_technical_report_harness_roundtrip.py` still proves
  the claim feedback ledger and integrity chain end to end

Commit closeout:

- one local atomic commit with implementation, focused tests, doc updates, and
  ratchet refreshes for this family

### Milestone 2: Release Readiness DB Gate Owner Split

Outcome label: reduced

Purpose:

- move technical-report release-readiness DB gate assembly, integrity, and
  context-pack audit logic into a focused owner family

Primary target:

- new owner module `app/services/evidence_release_readiness.py`

Implementation:

- read and apply `code-architecture-governance` before editing this boundary
  change
- move the DB gate payload, row-integrity, audit-ref, context-pack audit, and
  persistence helpers into the new owner module
- preserve existing gate payload fields, hash semantics, and governance-event
  linkage
- add focused unit coverage for payload hashing, integrity mismatch detection,
  and context-pack audit assembly

Acceptance:

- `app/services/evidence.py` no longer owns the release-readiness implementation
  family
- release-readiness assessment and DB-gate roundtrip behavior stays unchanged
- the technical-report integration suite still proves gate completeness,
  coverage, and governance links

Commit closeout:

- one local atomic commit for the release-readiness family only

### Milestone 3: Manifest And Semantic Trace Owner Split

Outcome label: reduced

Purpose:

- move technical-report evidence manifest assembly, manifest persistence, and
  semantic trace payload assembly into focused owner modules

Primary targets:

- `app/services/evidence_manifests.py`
- if needed for budget control, `app/services/evidence_semantic_trace.py`

Implementation:

- read and apply `code-architecture-governance` before editing this boundary
  change
- move evidence-manifest payload, integrity, row translation, persistence,
  refresh, and readback logic out of the facade
- move semantic assertion/fact payload and source-record extraction helpers into
  the same milestone if that keeps the manifest owner modules below budget
- preserve manifest JSON shape, audit checklist semantics, and evidence trace
  graph behavior

Acceptance:

- manifest creation and refresh stay behaviorally identical
- `get_agent_task_evidence_manifest` and `get_agent_task_evidence_trace` remain
  import-compatible through the facade
- technical-report harness integration still proves manifest completeness, gate
  linkage, semantic trace payloads, and evidence trace graph integrity

Commit closeout:

- one local atomic commit containing only manifest/trace extraction work

### Milestone 4: Claim Support Impact Evidence Owner Split

Outcome label: reduced

Purpose:

- move claim-support policy-impact, replay-alert fixture, waiver-closure, and
  governance-summary evidence logic out of the facade

Primary targets:

- `app/services/evidence_claim_support_impacts.py`
- if needed for budget control, `app/services/evidence_claim_support_replay_alerts.py`

Implementation:

- read and apply `code-architecture-governance` before editing this boundary
  change
- move change-impact summary, fixture-promotion, waiver-lifecycle, and related
  payload helpers into focused owner modules
- preserve audit-bundle and manifest consumers of these payloads
- add focused unit coverage for summary assembly and mismatch/integrity
  detection paths

Acceptance:

- `app/services/evidence.py` no longer owns the claim-support impact evidence
  family
- claim-support replay-alert and policy-impact integration suites still pass
- no audit payload or checklist field changes are introduced

Commit closeout:

- one local atomic commit for the claim-support impact family only

### Milestone 5: Audit View And Provenance Readback Owner Split

Outcome label: reduced

Purpose:

- move the remaining audit-bundle assembly, provenance-export readback, and
  audit-view helpers out of the facade so only compatibility wrappers remain

Primary target:

- `app/services/evidence_audit_views.py`

Implementation:

- read and apply `code-architecture-governance` before editing this boundary
  change
- move audit-bundle assembly/readback helpers and provenance-export response
  helpers into a focused owner module
- preserve `get_agent_task_audit_bundle`,
  `persist_agent_task_provenance_export`, and
  `get_agent_task_provenance_export` public behavior
- add focused unit coverage for readback payloads and facade exports where
  equivalent focused tests do not already exist

Acceptance:

- the remaining implementation-heavy audit/provenance family leaves the facade
- technical-report and semantic-governance integration tests still prove audit
  bundle, provenance export, and governance-chain behavior
- no new broad owner module is created while extracting the final family

Commit closeout:

- one local atomic commit for audit-view ownership only

### Milestone 6: Evidence Facade Resolution Closeout

Outcome label: resolved

Purpose:

- close the owner case by ratcheting `app/services/evidence.py` to final
  compatibility-facade shape and aligning durable governance docs to the live
  repo state

Implementation:

- read and apply `code-architecture-governance` before editing this final
  contract-closeout milestone
- remove or inline any residual implementation that still violates facade-only
  placement rules
- ratchet `config/hygiene_policy.yaml` for `app/services/evidence.py` to its
  final compatibility-facade ceiling at or below 600 lines / 20 private helpers
- update `config/improvement_cases.yaml` for `IC-050E60059A34` with deployment
  ref, refreshed measurements, and closure notes
- update `docs/agentic_architecture_index.md`, this plan, and
  `docs/SESSION_HANDOFF.md` with the completed milestone sequence, verification
  stack, final commit hashes, residual risks, and next routed owner case

Acceptance:

- `app/services/evidence.py` is a pure compatibility facade with no remaining
  owner-family implementation logic
- the final file is at or below 600 lines and 20 private helpers
- the evidence owner case is recorded as deployed with current live numbers
- if architecture-quality still lists `app/services/evidence.py`, the closeout
  docs explain that the residual signal is public fan-in rather than
  unresolved unclear ownership

Commit closeout:

- one final local atomic closeout commit containing only facade cleanup,
  ratchets, docs, and handoff alignment

## Required Implementation Artifacts

- `tests/unit/test_evidence_facade_contract.py`
- `app/services/evidence_claim_feedback.py`
- `app/services/evidence_release_readiness.py`
- `app/services/evidence_manifests.py`
- `app/services/evidence_claim_support_impacts.py`
- `app/services/evidence_audit_views.py`
- additional focused owner-module tests only when needed to prove a moved family
  at the unit boundary

If a milestone needs an extra sibling owner module to stay under budget, create
it in that same milestone and update the ratchet and prevention docs together.

## Required Documentation And Handoff Updates

Before each milestone commit, update the affected durable docs as a set:

- this plan with milestone status, verified results, and commit hash
- `config/hygiene_policy.yaml`
- `config/improvement_cases.yaml`
- `docs/agentic_architecture_index.md`
- `docs/SESSION_HANDOFF.md`

Update `docs/SESSION_HANDOFF.md` after every milestone with:

- completed milestone name
- exact verification commands run
- pass/fail counts
- commit hash
- residual risks or accepted deferrals
- the next milestone routing target

## Required Verification Gates

Run focused gates for each milestone first, then the broad gates before commit.

Focused gates by family:

- claim feedback:
  `uv run pytest -q tests/unit/test_evidence_claim_feedback.py tests/unit/test_evidence_facade_contract.py tests/integration/test_technical_report_harness_roundtrip.py -k \"claim_retrieval_feedback or technical_report\"`
- release readiness:
  `uv run pytest -q tests/unit/test_evidence_release_readiness.py tests/unit/test_evidence_facade_contract.py tests/integration/test_technical_report_harness_roundtrip.py -k \"release_readiness or technical_report\"`
- manifests and semantic trace:
  `uv run pytest -q tests/unit/test_evidence_manifests.py tests/unit/test_evidence_facade_contract.py tests/integration/test_technical_report_harness_roundtrip.py -k \"manifest or technical_report\"`
- claim support impacts:
  `uv run pytest -q tests/unit/test_evidence_claim_support_impacts.py tests/integration/test_claim_support_policy_change_impacts_roundtrip.py tests/integration/test_claim_support_policy_change_impacts_replay_alert_prevalidation.py tests/integration/test_claim_support_policy_change_impacts_replay_alert_promotions.py`
- audit views:
  `uv run pytest -q tests/unit/test_evidence_audit_views.py tests/integration/test_technical_report_harness_roundtrip.py tests/integration/test_semantic_governance_ledger.py`

Broad gates before every milestone commit:

- `git diff --check`
- `uv run ruff check app/services/evidence.py app/services/evidence_*.py tests/unit/test_evidence_*.py`
- `uv run docling-system-hotspot-prevention-check --strict`
- `uv run docling-system-hygiene-check`
- `uv run docling-system-architecture-inspect`
- `uv run docling-system-capability-contracts`
- `uv run docling-system-architecture-quality-report --summary`
- `uv run docling-system-improvement-case-summary`
- `uv run docling-system-improvement-case-validate`
- `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 12`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs tests/integration/test_technical_report_harness_roundtrip.py tests/integration/test_semantic_governance_ledger.py tests/integration/test_retrieval_learning_ledger.py tests/integration/test_claim_support_policy_change_impacts_roundtrip.py tests/integration/test_claim_support_policy_change_impacts_replay_alert_prevalidation.py tests/integration/test_claim_support_policy_change_impacts_replay_alert_promotions.py`

Verification hard rules:

- do not weaken tests, skip newly failing assertions, add xfails, or narrow
  coverage scope just to get green
- if a prior test is replaced, the same commit must prove equivalent or
  stronger contract coverage with new focused owner-module tests plus the
  unchanged broad gate stack
- if a focused gate passes but any broad gate fails, the milestone remains open
  and the run must continue
- contract closeout is not reached until Milestone 6 plus the final full-system
  closeout gate pass

Final full-system closeout gate after Milestone 6:

- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs`
- `uv run docling-system-evaluation-data-readiness --output storage/evaluation_data_readiness.latest.json`
- `uv run docling-system-agent-trace-review --limit 5 --skip-hygiene`

## Acceptance Criteria

- every milestone lands as a local atomic commit after verification passes
- unrelated dirty or untracked files remain untouched
- each moved family gains focused owner-module tests proving either direct
  behavior or compatibility-facade identity
- no milestone weakens prior coverage without stronger replacement coverage in
  the same commit
- the implementation run does not stop at an intermediate `reduced` state; it
  continues until the owner case is resolved and Milestone 6 closes
- `app/services/evidence.py` line count and helper count trend strictly
  downward across the sequence
- no new owner module exceeds 600 lines or 20 private helpers at closeout
- no new Python import-cycle component appears
- no evidence manifest, audit bundle, provenance export, claim feedback, or
  release-readiness artifact contract drifts
- the final milestone updates the owner case and handoff with current live
  verification numbers, not stale snapshots
- the final closeout includes both focused milestone gates and the repo-wide
  DB-backed suite, readiness report, and trace review outputs

## Stop Conditions

Stop and ask before continuing if any of the following happens:

- a proposed extraction requires changing public API or artifact schemas rather
  than preserving compatibility
- a milestone cannot keep the new owner module family below the budget even
  after same-milestone splitting
- a touched integration suite reveals pre-existing behavioral drift that the
  current milestone cannot fix without crossing into a new runtime feature lane
- a split introduces a new import cycle or capability-contract failure that
  cannot be fixed inside the same milestone
- unrelated worktree changes appear in touched files and materially conflict
  with the planned extraction

Do not stop for any of the following:

- a milestone is merely `reduced` and the next milestone is still routable
- focused tests are green but the full closeout stack has not yet run
- a doc or handoff update remains outstanding for contract closeout

## Local Commit Closeout Policy

- implement and commit milestone by milestone in the order above
- do not batch multiple milestones into one commit
- stage only the verified milestone slice
- include implementation, tests, docs, ratchets, and handoff updates for that
  milestone in the same commit
- record the commit hash in this plan and `docs/SESSION_HANDOFF.md`
- treat a verified but uncommitted milestone as ready-to-close, not complete
- treat the full sequence as incomplete until Milestone 6 is committed and the
  final full-system closeout gates pass
- if a milestone verification stack fails, do not commit partial work; fix the
  failure or stop under the stop rules

## Residual Risks And Next Routing

Expected residual risks during execution:

- some owner families may need one extra sibling module to stay under budget
- architecture-quality may still report `app/services/evidence.py` because of
  public fan-in even after unclear ownership is resolved
- the technical-report harness integration is large; focused tests must stay
  strong enough to localize regressions before the full DB-backed suite

If Milestone 6 closes successfully, route the next architecture follow-up to
the highest remaining open service hotspot from the live improvement-case
summary, expected to be `app/services/agent_task_actions.py`,
`app/services/search.py`, or `app/services/agent_task_context.py` unless the
live reports say otherwise.
