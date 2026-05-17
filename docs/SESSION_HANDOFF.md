# Session Handoff

Date: 2026-05-16 local / 2026-05-16 UTC
Project: `/Users/chunkstand/Documents/docling-system`
Branch: `main`
Remote: `origin -> https://github.com/chunkstand/docling-system.git`
Search Hydration Boundary Milestone 1 checkpoint: `14390ad`
Search Execution Persistence Boundary Milestone 1 checkpoint: `f55b474`
Search Execution Orchestration Milestone 1 checkpoint: `dae5e4f`
Search Compatibility Facade Boundary closeout checkpoint:
`fd9dd2a`
Claim Support Policy Impacts Boundary Milestone 4 checkpoint: `3d7d090`
Evaluations Service Boundary Milestone 1 checkpoint: `9e3a8e4`
Evaluations Service Boundary Milestone 2 checkpoint: `3817659`
Evaluations Service Boundary Milestone 3 checkpoint:
`b05def0`
Evaluations Service Boundary Milestone 4 checkpoint:
`1159297`
Evidence Provenance Exports Boundary closeout checkpoint:
`1aa8378`
Semantics Service Boundary closeout checkpoint:
`a2eb27e`
CLI Command Dispatch Milestone 0 checkpoint:
`381ca15`
CLI Command Dispatch Milestone 1 checkpoint:
`c674871`
CLI Command Dispatch Milestone 2 checkpoint:
`f5a4260`
CLI Command Dispatch closeout checkpoint:
`4a79a82`
Agent Task Schema Aggregation Milestone 0 checkpoint:
`5436f6f`
Agent Task Schema Aggregation closeout checkpoint:
`efe6d4e`
Hygiene Owner-Case Routing Milestone 0 checkpoint:
`08a1a75`
Hygiene Owner-Case Routing Milestone 1 checkpoint:
`d4f082c`
Hygiene Owner-Case Routing closeout checkpoint:
`9876f67`
Architecture Governance Cycle Milestone 0 checkpoint:
`46b90a7`
Architecture Governance Cycle Milestone 1 checkpoint:
`4338d4e`
Architecture Governance Cycle closeout checkpoint:
`7a4c5b0`
Runtime Health Orchestration Milestone 0 checkpoint:
`289f15a`
Runtime Health Orchestration Milestone 1 checkpoint:
`a84728c`
Runtime Health Orchestration closeout checkpoint:
`a57f74f`
CI Release Gate Parity Milestone 1 checkpoint:
`abecfa1`
CI Release Gate Parity Milestone 2 checkpoint:
`26dffcd`
CI Release Gate Parity Milestone 3 checkpoint:
`ad18d74`
CI Release Gate Parity Milestone 4 closeout checkpoint:
`0906e35`
Evidence Residual Owner Family Milestone 0 checkpoint:
`44bec70`
Evidence Residual Owner Family Milestone 1 closeout checkpoint:
`d9d79ef`
Evidence Residual Owner Family Milestone 2 closeout checkpoint:
`115be15`
Evidence Residual Owner Family Milestone 3 closeout checkpoint:
`245dc9f`
Evidence Residual Owner Family Milestone 4 closeout checkpoint:
`3e033fc`
Milestone 5 implementation checkpoint: agent-task orchestration local closeout
commit `7cf7465`; the prior agent-task orchestration Milestone 3 checkpoint
remains `faa3827`, the prior evidence and orchestration follow-on checkpoint
remains `3fe9132`, the prior Audit Bundle And Retrieval Learning Hotspots
Milestone 5 checkpoint remains `bf14f2a`, and the prior DB Models
Compatibility Facade Milestone 2 checkpoint remains `8340dc0`.
The app large owner modules follow-on is now resolved locally in the working
tree through the Milestone 9 closeout pass. The routed selected-root owner
cases are
`IC-9A0332D41F79` for `app/services/docling_parser.py`,
`IC-33B4990DC366` for `app/services/quality.py`,
`IC-8AFAD4A415CA` for `app/services/runs.py`,
`IC-865AB8419D55` for `app/services/semantic_graph.py`,
`IC-649D7B4E3AB5` for `app/services/semantic_candidates.py`,
`IC-A92BA42C6D18` for `app/services/semantic_generation.py`, and refreshed
`IC-81C531769EB3` for `app/services/semantic_governance.py`. Accepted routed
residual owner-family cases now remain open as `IC-6F4E2B5A91C3` for
`app/services/semantic_generation_brief.py` at `644` lines and
`IC-C8D41A2F77BE` for `app/services/semantic_graph_core.py` at `697` lines
plus `app/services/semantic_graph_promotions.py` at `718` lines. The selected
roots now measure `199`, `15`, `404`, `120`, `91`, `39`, and `185` lines for
`docling_parser.py`, `quality.py`, `runs.py`, `semantic_candidates.py`,
`semantic_generation.py`, `semantic_governance.py`, and `semantic_graph.py`
respectively. The broader current working tree has since been revalidated
after the evidence-owner closeout: `git diff --check` passed,
`uv run ruff check app/services app/api tests/unit tests/integration config`
passed, `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs` passed at
`2018 passed`, `uv run docling-system-hotspot-prevention-check --strict`
reported `changed_hotspots=0` and `blocked=0`,
`uv run docling-system-improvement-case-validate` returned `valid=true`,
`uv run docling-system-improvement-case-summary` reported `case_count=49`,
`status_counts.open=33`, and `measured_case_count=44`,
`uv run docling-system-hygiene-check` reported `new hygiene regressions: none`,
`uv run docling-system-architecture-quality-report --summary` reported
`agent_legibility_average_score=90.0`, `broad_facade_count=2`,
`hotspot_count=10`, and `max_hotspot_risk_score=496.06`,
`uv run docling-system-architecture-inspect` remained `valid=true` with
`violation_count=0`, and the architecture probe now reports `3` Python cycle
components with `29` code files above `800` lines while no selected closed
owner regrew above its ratchet.
Latest active bounded implementation brief:
`pending post-hotspot-prevention packet selection via docs/boring_change_architecture_milestone_plan.md`
Latest resolved bounded implementation brief:
`docs/hotspot_prevention_family_boundary_milestone_plan.md`
Milestones 0 and 1 of `docs/boring_change_architecture_milestone_plan.md` are
now resolved locally in the current checkout. The hotspot-prevention family
packet is now resolved locally: `app/hotspot_prevention_classifier.py` is
`360` lines / `1` private helper, the companion classifier owners now live in
`app/hotspot_prevention_claim_support_rules.py` at `436 / 1`,
`app/hotspot_prevention_classifier_service_rules.py` at `384 / 0`,
`app/hotspot_prevention_classifier_boundary_rules.py` at `209 / 0`, and
`app/hotspot_prevention_classifier_support.py` at `571 / 1`, and the test
owner family now lives in `tests/unit/test_hotspot_prevention.py` at `595 / 0`
plus `tests/unit/test_hotspot_prevention_family_rules.py` at `318 / 0`,
`tests/unit/test_hotspot_prevention_wrapper_rules.py` at `296 / 0`, and
`tests/unit/hotspot_prevention_test_support.py` at `50 / 2`. Focused
verification is green: the hotspot-prevention Ruff slice passed, `uv run
pytest -q tests/unit/test_hotspot_prevention.py
tests/unit/test_hotspot_prevention_family_rules.py
tests/unit/test_hotspot_prevention_wrapper_rules.py` passed at `40 passed`,
`uv run docling-system-hotspot-prevention-check --strict` returned
`changed_hotspots=0` and `blocked=0`, `uv run
docling-system-improvement-case-validate` returned `valid=true`, `uv run
docling-system-improvement-case-summary` still reports `case_count=49`,
`status_counts.open=33`, `status_counts.deployed=15`, and
`measured_case_count=44`, `uv run docling-system-hygiene-check` still reports
`new hygiene regressions: none`, `uv run
docling-system-architecture-quality-report --summary` still reports
`hotspot_count=10` with `max_hotspot_risk_score=496.06`, and the architecture
probe still reports `3` Python cycle components while dropping the code-file
backlog from `29` to `27` files above `800`. The broader coordination brief
remains `docs/boring_change_architecture_milestone_plan.md`, and its next
fresh bounded packet should be selected from the refreshed post-closeout
baseline. Current evidence favors a residual test-large-owner packet before
reopening app or UI backlog because the hotspot-prevention family no longer
appears in the `>800`-line queue.
The semantic pass lifecycle or reads follow-on now remains the prior resolved
bounded implementation brief:
`docs/semantic_pass_lifecycle_reads_boundary_milestone_plan.md`: it refreshes
the live post-replay-alert baseline, creates dedicated owner-case routing
`IC-8304248AB64C` for `app/services/semantic_pass_lifecycle.py` and
`IC-ADCFFF108626` for `app/services/semantic_pass_reads.py`, reduces
`app/services/semantic_pass_lifecycle.py` to `529` lines / `3` private
helpers by moving artifact ownership into
`app/services/semantic_pass_artifacts.py` at `150` lines / `0` private
helpers and keeping review and projection ownership in
`app/services/semantic_pass_reviews.py` at `369` lines / `4` private helpers,
reduces `app/services/semantic_pass_reads.py` to `372` lines / `3` private
helpers by moving source materialization and record shaping into
`app/services/semantic_pass_source_records.py` at `415` lines / `4` private
helpers, and marks the older
`docs/semantic_residual_owner_family_milestone_plan.md` draft as superseded by
this narrower lifecycle/read packet. Milestone 5 now closes the selected
owner-family packet locally: the full DB-backed closeout gate passed at
`2037 passed`, the broader `IC-9E6B8F5D62A1` case plus selected owner cases
`IC-8304248AB64C` and `IC-ADCFFF108626` are now retirement-ready pending an
atomic commit, and the broader repo routing has now advanced to the
hotspot-prevention family packet. Focused semantic verification is green:
`uv run pytest -q tests/unit/test_semantic_pass_lifecycle.py tests/unit/test_semantic_pass_reads.py ... tests/unit/test_semantic_graph.py`
passed at `108 passed`,
`DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs ...test_semantic_backfill_roundtrip.py`
passed at `8 passed`, the Milestone 4 focused read closeout slice passed at
`21 passed` plus `2 passed`, the final full DB-backed suite passed at
`2037 passed`, and the architecture probe still reports `3`
Python cycle components.
The replay-alert evidence follow-on now remains the latest resolved bounded
evidence-owner packet in the current checkout. Its planned local closeout is
still resolved in the current checkout. `app/services/evidence_claim_support_replay_alerts.py`
now measures `407` lines / `4` private helpers, replay-alert fixture-corpus
snapshot lineage now lives in
`app/services/evidence_claim_support_replay_alert_corpus.py` at `128` lines /
`0` private helpers, the manifest-owner predecessor remains reduced at `370`
lines with payload assembly in `app/services/evidence_manifest_payloads.py` at
`384`, and the broader `IC-65AF4A6D8B1E` evidence owner family now has no
governed file above the default `600`-line budget in the local checkout. The
focused owner suite now lives in
`tests/unit/test_evidence_claim_support_replay_alerts.py` and adds shared
governance reuse, snapshot payload completeness, promotion-event indexing,
facade re-export coverage, and the `<= 600` facade ratchet. Closeout
verification is green: `uv run pytest -q
tests/unit/test_evidence_claim_support_replay_alerts.py
tests/unit/test_evidence_facade_contract.py
tests/unit/test_replay_alert_waiver_integrity.py
tests/unit/test_claim_support_policy_impacts.py
tests/unit/test_technical_reports.py` passed at `24 passed`,
`DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs
tests/integration/test_technical_report_harness_integrity.py
tests/integration/test_technical_report_harness_audit_surfaces.py
tests/integration/test_multivector_retrieval.py` passed at `5 passed`,
`uv run docling-system-hygiene-check` still reports `new hygiene regressions:
none`, `uv run docling-system-improvement-case-summary` still reports
`case_count=48`, `status_counts.open=32`, and `measured_case_count=43`, and
the architecture probe still reports `3` Python cycle components with `29`
code files above `800` lines. The broader evidence owner-family case is now
locally retirement-ready pending an atomic commit of this packet.
The broader coordination brief remains
`docs/boring_change_architecture_milestone_plan.md`, but the just-closed
selected evidence packet is now the narrower standalone evidence-owner packet
for
`app/services/evidence_technical_report_exports.py`,
`app/services/evidence_semantic_trace.py`,
`app/services/evidence_claim_feedback.py`, and
`app/services/evidence_audit_views.py`. Milestone 0 is now resolved locally
through closeout commit `44bec70` for that evidence packet, and Milestone 1 is
resolved locally through closeout commit `d9d79ef`:
`app/services/evidence_technical_report_exports.py` now measures `396` lines
after moving release-binding and audit-bundle or
receipt lookup plus provenance-lock assembly into
`app/services/evidence_technical_report_export_provenance_locks.py` at `426`
lines and claim-derivation contract mismatch helpers into
`app/services/evidence_technical_report_export_contracts.py` at `112` lines.
Milestone 2 is now resolved locally through closeout commit `115be15`:
`app/services/evidence_technical_report_exports.py` measures `45` lines after
moving derivation package shaping and claim-derivation row payload shaping into
`app/services/evidence_technical_report_export_payloads.py` at `258` lines and
export persistence plus attachment helpers into
`app/services/evidence_technical_report_export_lifecycle.py` at `138` lines.
Milestone 3 is resolved locally through closeout commit `245dc9f`:
`app/services/evidence_claim_feedback.py` measures `498` lines after moving
verdict classification, retrieval-context materialization, evidence-ref
shaping, and desired-row payload construction into
`app/services/evidence_claim_feedback_payloads.py` at `376` lines.
Milestone 4 is resolved locally through closeout commit `3e033fc`:
`app/services/evidence_claim_feedback.py` now measures `47` lines after moving
claim-retrieval row payload shaping plus row and integrity summary reporting
into `app/services/evidence_claim_feedback_integrity.py` at `305` lines and
row lookup plus append-only live-link enforcement and ledger persistence into
`app/services/evidence_claim_feedback_lifecycle.py` at `215` lines. The current
checkout now measures `48` lines after the later no-behavior seam-ratchet
closeout.
Milestone 5 is resolved locally in the current checkout:
`app/services/evidence_semantic_trace.py` now measures `36` lines after moving
technical-report derivation integrity recomputation into
`app/services/evidence_semantic_trace_integrity.py` at `149` lines,
semantic-trace payload assembly into
`app/services/evidence_semantic_trace_payloads.py` at `182` lines,
source-record shaping into
`app/services/evidence_semantic_trace_source_records.py` at `109` lines, and
provenance-edge assembly into
`app/services/evidence_semantic_trace_provenance.py` at `444` lines.
The semantic-trace public surface remains stable for
`app/services/evidence.py`,
`app/services/evidence_manifests.py`, and
`app/services/evidence_audit_views.py` because the existing imports still
route through `app/services/evidence_semantic_trace.py`.
Milestone 6 is resolved locally in the current checkout:
`app/services/evidence_audit_views.py` now measures `19` lines after moving
the main audit-bundle aggregation into
`app/services/evidence_audit_views_bundle.py` at `482` lines, context-pack
audit reads into `app/services/evidence_audit_views_context.py` at `115`
lines, receipt payload shaping into
`app/services/evidence_audit_views_payloads.py` at `26` lines, and
release-readiness DB-gate persistence plus governance-event backfill into
`app/services/evidence_audit_views_release_readiness.py` at `136` lines.
The audit-view public surface remains stable for
`app/services/evidence.py`,
`app/services/evidence_manifests.py`,
`app/services/evidence_provenance_export_lifecycle.py`,
`app/services/capabilities/agent_orchestration.py`, and
`app/api/routers/agent_tasks.py` because the existing imports still route
through `app/services/evidence_audit_views.py`.
The selected residual evidence packet, manifest-trace follow-on, and
manifest-owner follow-on all remain resolved locally in the current checkout.
`app/services/evidence_technical_report_exports.py`,
`app/services/evidence_claim_feedback.py`,
`app/services/evidence_semantic_trace.py`, and
`app/services/evidence_audit_views.py` remain closed at `45`, `48`, `36`, and
`19` lines / `0` private helpers respectively;
`app/services/evidence_manifest_traces.py` remains closed at `203` lines with
focused siblings at `204`, `461`, and `244`; and
`app/services/evidence_manifests.py` remains closed at `370` lines with
payload assembly in `app/services/evidence_manifest_payloads.py` at `384`.
The replay-alert follow-on now closes the last live over-budget evidence root:
`app/services/evidence_claim_support_replay_alerts.py` is reduced to `407`
lines / `4` private helpers, the new
`app/services/evidence_claim_support_replay_alert_corpus.py` owner measures
`128` lines / `0` private helpers, and the broader
`IC-65AF4A6D8B1E` case now has no governed owner above budget in the current
checkout. This leaves the broader case open only as an uncommitted
retirement-ready route rather than as a still-blocked live evidence split.
The older semantic residual draft at
`docs/semantic_residual_owner_family_milestone_plan.md` is now explicitly
superseded by
`docs/semantic_pass_lifecycle_reads_boundary_milestone_plan.md`: the stale
draft predates the app large owner closeout that reduced
`app/services/semantic_governance.py` to `39` lines, while the remaining live
semantic pass residuals are now routed under `IC-8304248AB64C` and
`IC-ADCFFF108626`.
The hygiene owner-case routing packet is now resolved locally through closeout
commit `9876f67`. Its Milestone 0 refresh is committed locally as `08a1a75`,
Milestone 1 owner-case bootstrap is committed locally as `d4f082c` through
`IC-08C078FD4F45`, `IC-7C73737C689F`, and `IC-81C531769EB3`, Milestone 2
owner-case binding conversion is committed locally as `7ef99cd`, and
Milestone 3 owner-case-only hygiene-contract enforcement is committed locally
as `0dbd4c7`. Milestone 4 routing-packet closeout now leaves zero live
`owner_milestone` entries and keeps those three owner-case bindings as the
durable routing map.
The architecture-governance cycle packet is now resolved locally through
closeout commit `7a4c5b0`. Milestone 0 live refresh remains baseline commit `46b90a7`,
and Milestone 1 gate-first architecture import contract remains checkpoint
`4338d4e`: `app/architecture_decisions.py` now uses
`app/architecture_contract_catalog.py` instead of importing
`app.architecture_inspection`, `app/architecture_inspection.py` now reads
improvement-case and agent-action metadata through
`app/services/improvement_case_contracts.py` and
`app/services/agent_actions/contracts.py`, and the focused AST gate lives in
`tests/unit/test_architecture_governance_imports.py`. The closeout pass
revalidated `docling-system-architecture-inspect`,
`docling-system-capability-contracts`, improvement-case summary/validate,
hygiene, architecture quality, hotspot prevention, and the architecture
probe. The targeted architecture-governance cycle remains gone,
`IC-08C078FD4F45` remains open only as the residual oversized-owner anchor,
and the remaining global cycle backlog is now three non-governance components:
the search/documents/evaluations/runs/semantics family,
evidence-provenance export graph, and evidence-search packages/trace-store.
The runtime-health packet is now resolved locally through Milestone 4 closeout
commit `a57f74f`.
Runtime-health Milestone 0 refresh / owner-case bootstrap remains committed
locally as checkpoint `289f15a`, and Milestone 1 gate-first health contract
remains committed locally as checkpoint `a84728c`. Milestones 2 through 4 now
close the production-orchestration health gap under `IC-0F89DBB1CF9F` across
`app/api/main.py`, `app/api/routers/system.py`, `app/services/runtime.py`,
`app/workers/poller.py`, `app/workers/agent_poller.py`, and
`docker-compose.yml`: `app/services/runtime_health.py` now enriches
`/runtime/status` through the `system_governance` seam with nested shared
`health` diagnostics; `app/api/main.py`, `app/services/runs.py`, and
`app/services/agent_task_worker.py` now publish whole-process heartbeats
through `runtime_process_heartbeat(...)`; `app/runtime_health_cli.py` exposes
the repo-owned `docling-system-runtime-health` command; and
`docker-compose.yml` now wires repo-owned healthchecks for `api`, `worker`,
and `agent-worker` with a verified `10s` timeout budget.
Focused verification is green: `docker compose config --quiet`, the focused
runtime-health/API/worker unit slice (`62 passed`), `ruff`, architecture
inspection, architecture decisions, capability contracts, improvement-case
validate/summary, hygiene, and the architecture-quality summary all passed.
The final runtime proof is also green: `DOCLING_SYSTEM_POSTGRES_PORT=5434
docker compose up -d db api worker agent-worker` now brings up healthy `api`,
`worker`, and `agent-worker` containers, and
`TMPDIR=$PWD/.tmp DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run --extra dev python -m
pytest -q -rs` now passes at `1975 passed`.
The CI release-gate parity packet is now resolved locally under
`IC-2D8D5BF5A8C4`. Implementation proof remains checkpoint `ad18d74`, and the
Milestone 4 docs or registry closeout is committed locally as `0906e35`:
`app/release_gate_cli.py` owns the canonical `docling-system-release-gate-parity`
command, `.github/workflows/release-gate-parity.yml` runs that same command on
pull requests and pushes to `main`, every run uploads
`build/release-gate-parity/release_gate_report.json`, and failures upload
`build/release-gate-parity/failure/`. Milestone 4 closes the remaining docs,
handoff, README, SYSTEM_PLAN, architecture-index, and improvement-case
alignment so "GitHub green" and the checked-in local release contract now point
to the same repo-owned runner.

Closeout verification is green:
`git diff --check` passed,
`uv run pytest -q tests/unit/test_release_gate_cli.py` passed at `12 passed`,
`uv run docling-system-improvement-case-validate` returned `valid=true`,
`uv run docling-system-improvement-case-summary` reported
`case_count=38`, `status_counts.open=25`, `status_counts.deployed=12`, and
`status_counts.measured=1`,
`uv run docling-system-architecture-quality-report --summary` reported
`agent_legibility_average_score=90.0`, `broad_facade_count=2`,
`hotspot_count=10`, and `max_hotspot_risk_score=501.06`,
`uv run docling-system-architecture-inspect` remained `valid=true` with
`violation_count=0`,
`uv run docling-system-capability-contracts` remained `valid=true` with
`facade_count=6` and `function_count=111`,
`uv run docling-system-hygiene-check` reported `new hygiene regressions: none`,
and `uv run docling-system-release-gate-parity` again passed end to end with
metadata verification at `335 passed` and the wrapped full DB-backed suite at
`1987 passed`.

The only residual manual action for this packet is out of repo: if GitHub
required checks are managed in repository settings, require both
`Architecture Governance` and `Release Gate Parity`. That policy choice is no
longer represented as missing repo work.
The oversized-test packet is now resolved locally in the 2026-05-14 closeout
window through closeout commit `65c0c67`. Deployed follow-on cases are
`IC-5F0E1C8B0D42`,
`IC-7A628A4CBCAC`, and `IC-908E7A1D2C44`; reduced/open residuals remain
`IC-D9A84C20546B`, `IC-3B4C9F2A76E1`, `IC-25C1F7B9E4DA`, and
`IC-D49E037D5657` because their focused successor files still exceed the
default `600`-line hygiene budget. The broader search owner case
`IC-1D03DBFE8492` is now deployed locally after the compatibility-facade
closeout reduced `app/services/search.py` to a narrow facade and removed it
from the live architecture-probe hotspot queue. Both claim-support owner cases
`IC-E2270F89B397` and `IC-7C73737C689F` are now deployed locally after the
residual owner-family closeout reduced every governed claim-support owner to
the default `600`-line budget or below.

## Current Position

The checkout is on `main`. Local `main` carries the un-pushed CI parity
Milestone 4 closeout commit `0906e35`, the branch-pointer refresh commit
`e0d7ee2`, and the search compatibility-facade implementation closeout commit
`fd9dd2a`, plus the claim-support residual owner-family closeout commit
`40024a3`; the earlier CI parity implementation proof checkpoint remains
`ad18d74`, and the agent-task orchestration follow-on plan is resolved locally
through Milestone 5,
`docs/search_hydration_boundary_milestone_plan.md` is resolved locally through
Milestone 1 closeout commit `14390ad` for `IC-1D03DBFE8492`, and
`docs/search_execution_persistence_boundary_milestone_plan.md` is resolved
locally through Milestone 1 closeout commit `f55b474` for the prior search
owner reduction, and
`docs/search_execution_orchestration_boundary_milestone_plan.md` is now
resolved locally through Milestone 1 closeout commit `dae5e4f` for the next
search boundary split.

`docs/search_compatibility_facade_boundary_milestone_plan.md` is now resolved
locally through closeout commit `fd9dd2a` for `IC-1D03DBFE8492`. The closeout
extracts the remaining `app/services/search.py` ownership into three explicit
families:
`app/services/search_harnesses.py` at `627` lines / `0` private helpers,
`app/services/search_retrieval_primitives.py` at `653` lines /
`0` private helpers, and
`app/services/search_metadata_supplement.py` at `262` lines /
`0` private helpers.

`app/services/search.py` is now a `231` line / `2` private-helper
compatibility facade. It preserves the public import contract, alias
forwarding, and the explicit `execute_search(...)` / `search_documents(...)`
wrappers while delegating hydration to `app/services/search_hydration.py`,
persistence to `app/services/search_execution_persistence.py`, execution
orchestration to `app/services/search_execution_orchestration.py`, harness and
reranker ownership to `app/services/search_harnesses.py`, low-level retrieval
primitives to `app/services/search_retrieval_primitives.py`, and metadata
supplement plus adjacent-context expansion to
`app/services/search_metadata_supplement.py`.

The broader search owner case `IC-1D03DBFE8492` is now deployed locally rather
than reduced. The live architecture probe no longer lists
`app/services/search.py` in the top 20 hotspots and now routes
`app/services/agent_tasks.py` as the top hotspot instead, while the
architecture-quality summary top-five still excludes the search facade.

The broader coordination brief after this closeout is now
`docs/boring_change_architecture_milestone_plan.md`, and its Milestone 0
freshness step must rerun the live architecture-quality, hygiene,
improvement-case, and architecture-probe baseline before new implementation
starts.

This closeout still leaves `app/hotspot_prevention_classifier.py` at `999`
lines so the search compatibility-facade gate directly blocks harness-registry,
retrieval-primitive, and metadata-supplement regrowth in `app/services/search.py`.
That hygiene residual remains open under `IC-6C1B516A3F92`.

`docs/claim_support_policy_impacts_boundary_milestone_plan.md` is now resolved
locally through Milestone 4 closeout commit `3d7d090`. The scoped
subsystem-knot for `IC-E2270F89B397` is resolved:
`app/services/claim_support_policy_impacts.py` is now a 184-line /
0-private-helper compatibility facade, read-model and alert logic now live in
`app/services/claim_support_policy_impact_views.py` at 899 lines /
16 private helpers, and replay queueing plus closure lifecycle now live in
`app/services/claim_support_policy_impact_replay.py` at 898 lines /
11 private helpers. That earlier boundary implementation proof now rolls
forward into the resolved owner-family closeout below.

`docs/claim_support_residual_owner_family_milestone_plan.md` is now resolved
locally through closeout commit `40024a3`. It retires both open claim-support owner
cases together:

- `app/services/claim_support_policy_impact_views.py`,
  `app/services/claim_support_policy_impact_replay.py`, and
  `app/services/claim_support_replay_alert_promotions.py` now close at
  `207 / 0`, `247 / 6`, and `600 / 9`, while the extracted policy-impact owner
  modules close at `361 / 7`, `469 / 9`, `344 / 4`, `424 / 1`, `428 / 9`, and
  `535 / 6`.
- `app/services/claim_support_evaluations.py`,
  `app/services/claim_support_policy_governance.py`, and
  `app/services/claim_support_replay_alert_fixture_corpus.py` now close at
  `164 / 0`, `257 / 6`, and `206 / 0`, while the extracted support-family
  owner modules close at `534 / 7`, `319 / 4`, `339 / 1`, `534 / 6`,
  `559 / 2`, `328 / 4`, and `569 / 8`.
- No new claim-support service hotspots formed: the architecture-quality
  summary top hotspot paths still exclude claim-support service modules and the
  architecture probe top 20 no longer routes the split claim-support owner
  files. The only directly related residual still carried forward from this
  packet is `app/hotspot_prevention_classifier.py` under
  `IC-6C1B516A3F92`.
- The live claim-support cycle between
  `app.services.claim_support_policy_impacts` and
  `app.services.claim_support_replay_alert_promotions` is gone from the
  architecture probe.
- Focused verification is green:
  `uv run pytest -q ...claim_support... test slice` passed at `51 passed`,
  the focused DB-backed claim-support integration slice passed at `17 passed`,
  `uv run docling-system-hotspot-prevention-check --strict` passed with
  `blocked=0` and `allowed=7`,
  `uv run docling-system-hygiene-check`,
  `uv run docling-system-architecture-inspect`,
  `uv run docling-system-capability-contracts`, and
  `uv run docling-system-improvement-case-validate` all passed, and the
  wrapped full DB-backed suite passed at `1995 passed`.

`IC-E2270F89B397` and `IC-7C73737C689F` are now deployed locally rather than
reduced/open residuals. The next broader coordination brief remains
`docs/boring_change_architecture_milestone_plan.md`, and the only directly
related residual is the still-large hotspot-prevention classifier under
`IC-6C1B516A3F92`.

`docs/evaluations_service_boundary_milestone_plan.md` is now resolved locally
through Milestone 4 closeout commit `1159297`. The scoped subsystem-knot for
`IC-BF180637814C` is resolved locally:
`app/services/evaluations.py` is now a 283-line / 1-private-helper
orchestration and compatibility facade, the fixture/corpus owner remains in
`app/services/evaluation_fixtures.py` at 966 lines / 32 private helpers, the
scoring/structural owner remains in
`app/services/evaluation_scoring.py` at 897 lines / 25 private helpers, and
latest-evaluation summary/detail reads now live in
`app/services/evaluation_reads.py` at 154 lines / 1 private helper. The
architecture probe no longer lists the evaluation facade among the top 15
churn hotspots, so the broader owner case is now deployed locally rather than
remaining an open reduced hotspot.

`docs/evidence_provenance_exports_boundary_milestone_plan.md` is now resolved
locally through closeout commit `1aa8378` on 2026-05-13.
`app/services/evidence_provenance_exports.py` is now a 14-line compatibility
facade, provenance graph scaffolding now lives in
`app/services/evidence_provenance_export_graph_core.py` at 549 lines,
report-trace and claim-lineage graph ownership now lives in
`app/services/evidence_provenance_export_graph_report.py` at 218 lines, and
export lifecycle and persistence now live in
`app/services/evidence_provenance_export_lifecycle.py` at 278 lines. The
public evidence facade, the agent-orchestration capability seam, and
`/agent-tasks/{task_id}/provenance` all remain contract-stable, and
hotspot-prevention now blocks provenance graph, report-lineage, lifecycle, and
governance change-impact regrowth in the facade.

At the 2026-05-13 provenance-export checkpoint, the broader evidence owner
case `IC-65AF4A6D8B1E` still remained reduced rather than retired because
`app/services/evidence_technical_report_exports.py` measured 884 lines,
`app/services/evidence_semantic_trace.py` 837,
`app/services/evidence_claim_feedback.py` 834, and
`app/services/evidence_audit_views.py` 699. The hotspot-prevention classifier
follow-up case `IC-6C1B516A3F92` also remained open after the semantics gate
and later CLI Milestone 1 facade-prevention ratchet expanded the classifier;
the oversized-test closeout then split shared classification helpers into
`app/hotspot_prevention_classifier_support.py`, leaving
`app/hotspot_prevention_classifier.py` at `960` lines.

`docs/semantics_service_boundary_milestone_plan.md` is now resolved locally
through closeout commit `a2eb27e`. The scoped semantics service-boundary
knot under `IC-9E6B8F5D62A1` is resolved: `app/services/semantics.py` is now a
54-line / 0-private-helper compatibility facade, semantic pass lifecycle
ownership now lives in `app/services/semantic_pass_lifecycle.py` at
529 lines / 3 private helpers after the later lifecycle or reads follow-on
moved artifact ownership into
`app/services/semantic_pass_artifacts.py` at 150 lines / 0 private helpers
and review and projection ownership into
`app/services/semantic_pass_reviews.py` at 369 lines / 4 private helpers,
active-pass row/detail/continuity reads now live in
`app/services/semantic_pass_reads.py` at 372 lines / 3 private helpers after
the later read materialization split moved source materialization and record
shaping into `app/services/semantic_pass_source_records.py` at 415 lines / 4
private helpers, and registry preview ownership now lives in
`app/services/semantic_registry_preview.py` at 558 lines / 5 private helpers.
The broader owner case is now locally retirement-ready pending an atomic
closeout commit because the extracted lifecycle, artifact, review, read, and
source-record owners are all under budget locally even though the
architecture probe no longer lists the semantics facade among the top 12 churn
hotspots.

`docs/cli_command_dispatch_boundary_milestone_plan.md` is now resolved locally
through closeout commit `4a79a82`. The prior stacked prerequisites remain
closed as `3d7d090`, `1159297`, `1aa8378`, and `a2eb27e`, the tightened CLI
rule still blocks direct session or storage wiring plus parser-body or
JSON-render scaffolding in `app/cli.py`, runtime and maintenance command
ownership remains in `app/cli_commands/runtime.py` at `463` lines,
retrieval-learning and search-harness command ownership now lives in
`app/cli_commands/search_harness.py` at `604` lines, and `app/cli.py` is
reduced to `375` lines with explicit forwarding wrappers that preserve the
stable `app.cli:run_*` entrypoints plus the legacy lazy service-wrapper seam
names. Direct owner coverage now lives in
`tests/unit/test_cli_search_harness.py` at `714` lines, forwarding coverage now
lives in `tests/unit/test_cli_entrypoints.py` at `102` lines, and
`tests/unit/test_cli.py` is reduced to an empty compatibility placeholder so
the governed hotspot no longer absorbs direct owner assertions. The live
architecture-quality report now measures `app/cli.py` at `375` lines, `56`
changes over 90 days, and `risk_score 425.5`; the architecture probe no longer
lists `app/cli.py` in the top 12 churn hotspots, but the architecture-quality
summary still routes the facade among the top hotspot paths, so the broader
owner case remains reduced/open under `IC-9812A0B138D9`. The strict hotspot
gate stays green at `changed_hotspots=2`, `blocked=0`, `allowed=3`,
`exceptions=0`.

Resolved stacked follow-on after the CLI packet:
`docs/agent_task_schema_aggregation_boundary_milestone_plan.md`. The packet is
now resolved locally through closeout commit `efe6d4e`: `app/schemas/agent_tasks.py`
is reduced to a `38` line compatibility facade, production `app/` import
fan-in is now `0`, local test and integration import fan-in is now `30`, and
the refreshed architecture-quality evidence measures the facade at
`risk_score=363.75`, `line_count=38`, `changes_90d=58`,
`hygiene_finding_count=0`. The broader owner case remains reduced/open under
`IC-24F3558D6091` because the architecture-quality summary still routes the
facade even though the scoped aggregation issue is closed.

Resolved stacked follow-on after the agent-task schema packet:
`docs/oversized_test_hotspots_boundary_milestone_plan.md`. The packet is now
resolved locally through closeout commit `65c0c67` in the 2026-05-14
oversized-test closeout window:
`tests/db_model_contract.py` is `159` lines,
`tests/unit/test_agent_task_context.py` is `328`,
`tests/unit/test_agent_tasks_api.py` is `92`,
`tests/unit/test_evaluation_service.py` is `389`,
`tests/unit/test_search_service.py` is `117`,
`tests/integration/test_retrieval_learning_ledger.py` is `428`, and
`tests/integration/test_technical_report_harness_roundtrip.py` is `93`. The
architecture probe no longer lists any of those residual files among the top
20 hotspots. The broader follow-on routing is now explicit:
`IC-5F0E1C8B0D42`, `IC-7A628A4CBCAC`, and `IC-908E7A1D2C44` are deployed,
while `IC-D9A84C20546B`, `IC-3B4C9F2A76E1`, `IC-25C1F7B9E4DA`, and
`IC-D49E037D5657` remain reduced/open because focused successor files still
measure `756`, `636` or `630` or `653`, `621`, and `799` lines respectively.

Resolved stacked follow-on after the oversized-test packet:
`docs/hygiene_owner_case_routing_boundary_milestone_plan.md`. Milestone 0 is
resolved locally through baseline commit `08a1a75`, and Milestone 1
owner-case bootstrap is resolved locally through checkpoint `d4f082c`: the
seven prerequisite packets are closed locally, the registry now binds the
eight residual owner-routing paths through
`IC-08C078FD4F45`, `IC-7C73737C689F`, and `IC-81C531769EB3`, and Milestone 2
owner-case binding conversion is committed locally as `7ef99cd`:
`config/hygiene_policy.yaml` no longer contains any live `owner_milestone`
entries for
`app/architecture_inspection.py`,
`app/architecture_inspection_rules.py`,
`app/services/claim_support_evaluations.py`,
`app/services/claim_support_policy_governance.py`,
`app/services/claim_support_replay_alert_fixture_corpus.py`,
`app/services/improvement_case_intake.py`,
`app/services/improvement_cases.py`, and
`app/services/semantic_governance.py`. No residual file remains routed through
the old milestone label, and Milestone 3 owner-case-only hygiene-contract
enforcement is committed locally as `0dbd4c7`: `app/hygiene.py`,
`app/hygiene_types.py`, `tests/unit/test_hygiene.py`, and
`docs/improvement_loop.md` now reject `owner_milestone` as a live owner
reference. Milestone 4 routing-packet closeout is now resolved locally through
closeout commit `9876f67`, and the next active slice is
`docs/architecture_governance_cycle_boundary_milestone_plan.md`.

Active stacked follow-on after the hygiene owner-case routing packet:
`docs/architecture_governance_cycle_boundary_milestone_plan.md`. Milestone 0
live refresh is now resolved locally through baseline commit `46b90a7`: the
packet reuses `IC-08C078FD4F45` across `config/improvement_cases.yaml` and
`config/hygiene_policy.yaml`, freezes the architecture-control cycle component
as `app.architecture_decisions`, `app.architecture_inspection`,
`app.architecture_inspection_rules`, `app.hygiene`, and
`app.services.improvement_case_intake`, and confirms architecture-quality,
hotspot-prevention, and hygiene remain green so the baseline does not form new
hotspots or shift debt into adjacent owner surfaces. Milestone 1 gate-first
architecture import contract is the next active slice for removing the
`app.architecture_decisions` / `app.architecture_inspection` recursive
contract-discovery dependency, and eliminating the architecture-governance
cycle component from the architecture probe without broadening into the other
remaining cycle families.

Additional committed later-stack follow-ons now exist for
`docs/runtime_health_orchestration_milestone_plan.md`,
`docs/ci_release_gate_parity_milestone_plan.md`, and
`docs/boring_change_architecture_milestone_plan.md`; each still depends on the
earlier routed packets closing first, and the broader coordination queue now
also sits behind the architecture-governance cycle packet above.

The live alignment snapshot at the architecture-governance Milestone 0
baseline is:

- `uv run docling-system-improvement-case-summary`: `case_count=36`,
  `status_counts.open=25`, `status_counts.deployed=10`,
  `status_counts.measured=1`, `measured_case_count=31`,
  `oldest_open_case_id=IC-9812A0B138D9`
- `uv run docling-system-architecture-quality-report --summary`:
  `agent_legibility_average_score=90.0`, `broad_facade_count=2`,
  `hotspot_count=10`, `max_hotspot_risk_score=501.06`
- `uv run docling-system-improvement-case-validate`: `valid=true`,
  `issue_count=0`
- `uv run docling-system-hotspot-prevention-check --strict`:
  `known_hotspots=21`, `changed_hotspots=0`, `blocked=0`, `allowed=0`,
  `exceptions=0`
- `uv run docling-system-hygiene-check`: `new hygiene regressions: none`
- `uv run docling-system-improvement-case-import --source hygiene --dry-run`:
  `candidate_count=0`, `imported_count=0`, `skipped_count=0`
- `rg -n "owner_milestone:" config/hygiene_policy.yaml`: no hits
- `rg -n "app/architecture_inspection.py|app/architecture_inspection_rules.py|app/services/claim_support_evaluations.py|app/services/claim_support_policy_governance.py|app/services/claim_support_replay_alert_fixture_corpus.py|app/services/improvement_case_intake.py|app/services/improvement_cases.py|app/services/semantic_governance.py" config/improvement_cases.yaml`:
  registry hits now route the eight residual files through
  `IC-08C078FD4F45`, `IC-7C73737C689F`, and `IC-81C531769EB3`
- `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 20`:
  top hotspot `app/services/search.py`; the targeted residual files remain
  large; Python cycle components=`5`

## Architecture Governance Cycle Boundary Milestone 0 Local Refresh

Milestone 0 is resolved locally through baseline commit `46b90a7`. The
post-stack baseline is now refreshed against the live owner-case map, the
exact architecture-control cycle component is frozen before code motion
begins, and Milestone 1 gate-first architecture import contract is now the
next active slice.

Results:

- confirmed the prior hygiene owner-case routing packet is already closed
  through `9876f67`, so the active architecture-governance packet now reuses
  the live owner case `IC-08C078FD4F45` instead of creating a duplicate case
  family
- confirmed `config/improvement_cases.yaml` and `config/hygiene_policy.yaml`
  both route `app/architecture_inspection.py`,
  `app/architecture_inspection_rules.py`,
  `app/services/improvement_case_intake.py`, and
  `app/services/improvement_cases.py` through `IC-08C078FD4F45`
- refreshed the current 2026-05-14 post-stack baseline and froze the exact
  architecture-control cycle component as
  `app.architecture_decisions`,
  `app.architecture_inspection`,
  `app.architecture_inspection_rules`,
  `app.hygiene`, and
  `app.services.improvement_case_intake`
- confirmed the refreshed baseline is not shifting debt: the architecture
  quality summary remains `hotspot_count=10` with
  `max_hotspot_risk_score=501.06`, `docling-system-hotspot-prevention-check
  --strict` reports `changed_hotspots=0` and `blocked=0`, and
  `docling-system-hygiene-check` still reports `new hygiene regressions: none`
- updated the active plan, handoff, and architecture index so Milestone 1
  gate-first architecture import contract is now the next active code-changing
  slice

Verification:

- `git status -sb`: clean worktree at baseline start commit `6867004`; local
  `main` ahead of `origin/main` by `52`
- `uv run docling-system-improvement-case-summary`: `case_count=36`,
  `status_counts.open=25`, `status_counts.deployed=10`,
  `status_counts.measured=1`, `measured_case_count=31`,
  `oldest_open_case_id=IC-9812A0B138D9`
- `uv run docling-system-improvement-case-validate`: `valid=true`,
  `issue_count=0`
- `uv run docling-system-architecture-inspect`: `valid=true`,
  `violation_count=0`
- `uv run docling-system-capability-contracts`: `valid=true`,
  `facade_count=6`, `function_count=110`
- `uv run docling-system-architecture-quality-report --summary`:
  `agent_legibility_average_score=90.0`, `broad_facade_count=2`,
  `hotspot_count=10`, `max_hotspot_risk_score=501.06`
- `uv run docling-system-hotspot-prevention-check --strict`:
  `known_hotspots=21`, `changed_hotspots=0`, `blocked=0`, `allowed=0`,
  `exceptions=0`
- `uv run docling-system-hygiene-check`: `new hygiene regressions: none`
- `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 20`:
  top hotspot `app/services/search.py`; Python cycle components=`5`; the
  architecture-control cycle component still contains
  `app.architecture_decisions`,
  `app.architecture_inspection`,
  `app.architecture_inspection_rules`,
  `app.hygiene`, and
  `app.services.improvement_case_intake`
- `rg -n "IC-08C078FD4F45|app/architecture_inspection.py|app/architecture_inspection_rules.py|app/services/improvement_case_intake.py|app/services/improvement_cases.py" config/improvement_cases.yaml config/hygiene_policy.yaml`:
  registry and hygiene-policy hits both confirm `IC-08C078FD4F45` owns the
  four governed architecture-governance files

## Hygiene Owner-Case Routing Boundary Milestone 0 Local Refresh

Milestone 0 is resolved locally through baseline commit `08a1a75`. The
stacked preconditions were revalidated from the live repo state, the exact
remaining milestone-owned hygiene-routing set was frozen in the active docs,
and Milestone 1 owner-case bootstrap became the next active code-changing
slice.

Results:

- confirmed the seven upstream packets named in the plan are already closed
  locally, so the hygiene-routing packet is no longer blocked on earlier
  stacked work
- confirmed the live residual set still contains exactly eight
  `owner_milestone=residual-weakness-milestone-2` entries:
  `app/architecture_inspection.py`,
  `app/architecture_inspection_rules.py`,
  `app/services/claim_support_evaluations.py`,
  `app/services/claim_support_policy_governance.py`,
  `app/services/claim_support_replay_alert_fixture_corpus.py`,
  `app/services/improvement_case_intake.py`,
  `app/services/improvement_cases.py`, and
  `app/services/semantic_governance.py`
- confirmed none of those eight residual files already have explicit owner
  cases in `config/improvement_cases.yaml`, so Milestone 1 still needs the
  planned architecture-governance, claim-support support, and
  semantic-governance owner bootstrap
- refreshed the plan, handoff, and architecture index so all three routing
  artifacts now agree that Milestone 0 is closed and Milestone 1 is next
- recorded baseline checkpoint `08a1a75` in the canonical handoff so the
  packet no longer reads like a pre-commit refresh note

Verification:

- `git status -sb`: clean worktree at baseline checkpoint `08a1a75`; local
  `main` remained ahead of `origin/main`
- `uv run docling-system-improvement-case-summary`: `case_count=33`,
  `status_counts.open=22`, `status_counts.deployed=10`,
  `status_counts.measured=1`, `actionable_buckets.open_unconverted_count=22`
- `uv run docling-system-improvement-case-validate`: `valid=true`,
  `issue_count=0`
- `uv run docling-system-hygiene-check`: `new hygiene regressions: none`
- `uv run docling-system-architecture-quality-report --summary`:
  `agent_legibility_average_score=90.0`, `broad_facade_count=2`,
  `hotspot_count=10`, `max_hotspot_risk_score=501.06`
- `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 20`:
  top hotspot `app/services/search.py`; Python cycle components=`5`

## Hygiene Owner-Case Routing Boundary Milestone 1 Owner-Case Bootstrap

Milestone 1 is resolved locally through checkpoint `d4f082c`. The packet now
has explicit family owner cases for every live residual
`owner_milestone=residual-weakness-milestone-2` surface, and Milestone 2
owner-case binding conversion became the next active code-changing slice.

Results:

- created `IC-08C078FD4F45` for the architecture-governance residual family
  anchored to `app/architecture_inspection.py` and covering
  `app/architecture_inspection.py`,
  `app/architecture_inspection_rules.py`,
  `app/services/improvement_case_intake.py`, and
  `app/services/improvement_cases.py`
- created `IC-7C73737C689F` for the claim-support support residual family
  anchored to `app/services/claim_support_policy_governance.py` and covering
  `app/services/claim_support_evaluations.py`,
  `app/services/claim_support_policy_governance.py`, and
  `app/services/claim_support_replay_alert_fixture_corpus.py`
- created `IC-81C531769EB3` for the semantic-governance residual owner
  anchored to `app/services/semantic_governance.py`
- eliminated missing-case routing for the packet: every live residual file now
  has a discoverable case ID in `config/improvement_cases.yaml`, even though
  the live hygiene policy still points at the old milestone label until
  Milestone 2 converts those entries

Verification:

- `uv run docling-system-improvement-case-summary`: `case_count=36`,
  `status_counts.open=25`, `status_counts.deployed=10`,
  `status_counts.measured=1`, `measured_case_count=31`
- `uv run docling-system-improvement-case-validate`: `valid=true`,
  `issue_count=0`
- `uv run docling-system-hygiene-check`: `new hygiene regressions: none`
- `uv run docling-system-architecture-quality-report --summary`:
  `agent_legibility_average_score=90.0`, `broad_facade_count=2`,
  `hotspot_count=10`, `max_hotspot_risk_score=501.06`
- `rg -n "app/architecture_inspection.py|app/architecture_inspection_rules.py|app/services/claim_support_evaluations.py|app/services/claim_support_policy_governance.py|app/services/claim_support_replay_alert_fixture_corpus.py|app/services/improvement_case_intake.py|app/services/improvement_cases.py|app/services/semantic_governance.py|IC-08C078FD4F45|IC-7C73737C689F|IC-81C531769EB3" config/improvement_cases.yaml`:
  all eight residual files now resolve through the three new family case IDs

## Hygiene Owner-Case Routing Boundary Milestone 2 Binding Conversion

Milestone 2 is resolved locally through closeout commit `7ef99cd`. The eight live
residual hygiene overrides that previously used
`owner_milestone=residual-weakness-milestone-2` now bind directly to explicit
owner cases, and Milestone 3 owner-case-only hygiene-contract enforcement is
the next active code-changing slice.

Results:

- replaced all eight live milestone-owned residual entries in
  `config/hygiene_policy.yaml` with `owner_case_id` bindings
- bound `app/architecture_inspection.py`,
  `app/architecture_inspection_rules.py`,
  `app/services/improvement_case_intake.py`, and
  `app/services/improvement_cases.py` to `IC-08C078FD4F45`
- bound `app/services/claim_support_evaluations.py`,
  `app/services/claim_support_policy_governance.py`, and
  `app/services/claim_support_replay_alert_fixture_corpus.py` to
  `IC-7C73737C689F`
- bound `app/services/semantic_governance.py` to `IC-81C531769EB3`
- preserved the existing ratchet ceilings while removing milestone-owned
  routing from the live hygiene policy
- refreshed the active plan, handoff, and architecture index so all routed
  governance artifacts agree that Milestone 2 is closed locally and
  Milestone 3 is next

Verification:

- `git diff --check`: pass
- `uv run docling-system-improvement-case-summary`: `case_count=36`,
  `status_counts.open=25`, `status_counts.deployed=10`,
  `status_counts.measured=1`, `measured_case_count=31`
- `uv run docling-system-improvement-case-validate`: `valid=true`,
  `issue_count=0`
- `uv run docling-system-hygiene-check`: `new hygiene regressions: none`
- `uv run docling-system-improvement-case-import --source hygiene --dry-run`:
  pass
- `uv run docling-system-architecture-quality-report --summary`:
  `agent_legibility_average_score=90.0`, `broad_facade_count=2`,
  `hotspot_count=10`, `max_hotspot_risk_score=501.06`
- `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 20`:
  top hotspot `app/services/search.py`; Python cycle components=`5`
- `rg -n "owner_milestone:" config/hygiene_policy.yaml`: no hits

## Hygiene Owner-Case Routing Boundary Milestone 3 Contract Enforcement

Milestone 3 is resolved locally through closeout commit `0dbd4c7`. The hygiene contract
now rejects `owner_milestone` as a valid ratchet owner reference. At
Milestone 3 closeout, Milestone 4 routing-packet closeout became the next
active slice.

Results:

- updated `app/hygiene_types.py` so `owner_reference` resolves only through
  `owner_case_id`
- updated `app/hygiene.py` so ratcheted budgets fail closed when
  `owner_milestone` appears and require `owner_case_id` even if a legacy
  milestone label is present
- converted the focused hygiene fixtures to explicit `owner_case_id` values and
  added a negative contract test proving `owner_milestone` is rejected
- updated `docs/improvement_loop.md` so the durable repo guidance now documents
  `owner_case_id` as the sole valid ratchet owner reference
- refreshed the active plan, handoff, and architecture index so all routed
  governance artifacts agree that Milestone 3 is closed locally and Milestone 4
  closeout is next

Verification:

- `git diff --check`: pass
- `uv run ruff check app/hygiene.py app/hygiene_types.py tests/unit/test_hygiene.py tests/unit/test_improvement_case_intake.py`:
  pass
- `uv run pytest -q tests/unit/test_hygiene.py tests/unit/test_improvement_case_intake.py`:
  pass
- `uv run docling-system-improvement-case-summary`: `case_count=36`,
  `status_counts.open=25`, `status_counts.deployed=10`,
  `status_counts.measured=1`, `measured_case_count=31`
- `uv run docling-system-improvement-case-validate`: `valid=true`,
  `issue_count=0`
- `uv run docling-system-hygiene-check`: `new hygiene regressions: none`
- `uv run docling-system-improvement-case-import --source hygiene --dry-run`:
  `candidate_count=0`, `imported_count=0`, `skipped_count=0`
- `uv run docling-system-architecture-quality-report --summary`:
  `agent_legibility_average_score=90.0`, `broad_facade_count=2`,
  `hotspot_count=10`, `max_hotspot_risk_score=501.06`
- `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 20`:
  top hotspot `app/services/search.py`; Python cycle components=`5`
- `rg -n "owner_milestone:" config/hygiene_policy.yaml`: no hits

## Hygiene Owner-Case Routing Boundary Milestone 4 Packet Closeout

Milestone 4 is resolved locally through closeout commit `9876f67`. The packet
now closes with explicit owner-case routing only, the active docs no longer
describe the residual files as milestone-owned hygiene debt, and the next
active bounded packet is
`docs/architecture_governance_cycle_boundary_milestone_plan.md`.

Results:

- reran the live hygiene-routing evidence stack after Milestone 3 contract
  enforcement and confirmed the explicit owner map remained stable at
  `case_count=36`, `status_counts.open=25`, `status_counts.deployed=10`,
  `status_counts.measured=1`, `hotspot_count=10`,
  `max_hotspot_risk_score=501.06`, and Python cycle components=`5`
- refreshed `docs/hygiene_owner_case_routing_boundary_milestone_plan.md`,
  `docs/SESSION_HANDOFF.md`, and
  `docs/agentic_architecture_index.md` so the hygiene packet is now closed in
  routed docs and the architecture-governance cycle packet is promoted into the
  active slot
- confirmed the explicit closeout owner map remains
  `IC-08C078FD4F45`, `IC-7C73737C689F`, and `IC-81C531769EB3`, with zero live
  `owner_milestone` entries remaining in `config/hygiene_policy.yaml`
- left `docs/runtime_health_orchestration_milestone_plan.md`,
  `docs/ci_release_gate_parity_milestone_plan.md`, and
  `docs/boring_change_architecture_milestone_plan.md` queued behind the
  architecture-governance cycle packet instead of letting them bypass the
  still-open governance-cycle dependency

Verification:

- `git diff --check`: pass
- `uv run docling-system-improvement-case-summary`: `case_count=36`,
  `status_counts.open=25`, `status_counts.deployed=10`,
  `status_counts.measured=1`, `measured_case_count=31`,
  `oldest_open_case_id=IC-9812A0B138D9`
- `uv run docling-system-improvement-case-validate`: `valid=true`,
  `issue_count=0`
- `uv run docling-system-hygiene-check`: `new hygiene regressions: none`
- `uv run docling-system-improvement-case-import --source hygiene --dry-run`:
  `candidate_count=0`, `imported_count=0`, `skipped_count=0`
- `uv run docling-system-architecture-quality-report --summary`:
  `agent_legibility_average_score=90.0`, `broad_facade_count=2`,
  `hotspot_count=10`, `max_hotspot_risk_score=501.06`
- `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 20`:
  top hotspot `app/services/search.py`; the targeted routed residual files
  remain large; Python cycle components=`5`
- `rg -n "owner_milestone:" config/hygiene_policy.yaml`: no hits

## Oversized Test Hotspots Boundary Local Closeout

Milestones 0 through 6 are resolved locally through closeout commit `65c0c67`
in the 2026-05-14 oversized-test closeout window. The scoped oversized-test
knot is closed: all seven selected residual files now sit below their packet
thresholds, their replacement families are routed explicitly, and the
architecture probe no longer lists any of the seven residual files among the
top 20 hotspots.

Results:

- reduced `tests/db_model_contract.py` to `159` lines and moved the shared ORM
  contract families into `tests/db_model_contract_domains/`, with all extracted
  domain files at `588` lines or below
- reduced `tests/unit/test_agent_task_context.py` to `328` lines and
  `tests/unit/test_agent_tasks_api.py` to `92` lines while moving the owner
  families into focused files; the broader owner cases remain reduced/open
  because focused successors still measure `636`, `630`, `653`, and `756`
  lines
- confirmed `tests/unit/test_evaluation_service.py` was already at `389` lines
  after the earlier evaluation-owner packet, so this closeout only refreshed
  the owner-case evidence rather than moving more assertions
- reduced `tests/unit/test_search_service.py` to `117` lines and moved the
  metadata supplement, ranking, orchestration, and persistence assertions into
  focused files; the broader case remains reduced/open because the ranking
  owner still measures `621` lines
- reduced `tests/integration/test_retrieval_learning_ledger.py` to `428` lines
  and `tests/integration/test_technical_report_harness_roundtrip.py` to
  `93` lines, kept the family-local support modules at `362` and `396` lines,
  and moved the scenario families into focused integration files; the
  retrieval-learning owner case is deployed, while the technical-report owner
  case remains reduced/open because the audit surface still measures `799`
  lines
- refreshed hotspot-prevention, hygiene, and improvement-case routing so the
  next bounded follow-on is now
  `docs/hygiene_owner_case_routing_boundary_milestone_plan.md`

At the time of this evaluations Milestone 4 closeout, the reduced or routed
follow-on cases were `IC-1D03DBFE8492` / `app/services/search.py`,
`IC-E2270F89B397` / `app/services/claim_support_policy_impacts.py`,
`IC-65AF4A6D8B1E` / `app/services/evidence_provenance_exports.py`, and
`IC-6C1B516A3F92` / `app/hotspot_prevention_classifier.py`. Current routing is
captured at the top of this handoff; after provenance-export closeout commit
`1aa8378`, `IC-65AF4A6D8B1E` now routes through
`app/services/evidence_technical_report_exports.py`.

## Semantics Service Boundary Local Closeout

Milestones 0-5 are resolved locally through closeout commit `a2eb27e` on
2026-05-13 local / 2026-05-14 UTC. The scoped semantics boundary knot under
`IC-9E6B8F5D62A1` is resolved while the broader owner case remains
reduced/open.

Results:

- extracted semantic pass lifecycle, projection refresh, and review
  persistence into `app/services/semantic_pass_lifecycle.py`
- extracted active-pass row/detail/continuity reads and helper shaping into
  `app/services/semantic_pass_reads.py`
- extracted registry preview candidate assembly and expectation-delta payload
  shaping into `app/services/semantic_registry_preview.py`
- reduced `app/services/semantics.py` to a 54-line compatibility facade that
  only re-exports the stable semantics surface and preserves the narrow
  registry-preview forwarding wrapper
- added a dedicated semantics owner case plus hotspot-prevention rule, focused
  classifier coverage, and direct owner tests for the three new modules
- refreshed `config/hygiene_policy.yaml` and `config/improvement_cases.yaml`
  so the facade, extracted owners, and classifier follow-on all reflect the
  live post-split state
- later lifecycle/read follow-on work now reduces
  `app/services/semantic_pass_lifecycle.py` to 529 lines / 3 private helpers,
  `app/services/semantic_pass_reads.py` to 372 lines / 3 private helpers,
  moves artifact ownership into
  `app/services/semantic_pass_artifacts.py` at 150 lines / 0 private helpers,
  keeps review and projection ownership in
  `app/services/semantic_pass_reviews.py` at 369 lines / 4 private helpers,
  and moves read source materialization or record shaping into
  `app/services/semantic_pass_source_records.py` at 415 lines / 4 private
  helpers, leaving the broader semantic owner family locally
  retirement-ready pending an atomic closeout commit
- local closeout commit:
  `a2eb27e`

Verification:

- `git diff --check`: pass
- `uv run ruff check app/services/semantics.py app/services/semantic_pass_lifecycle.py app/services/semantic_pass_reads.py app/services/semantic_registry_preview.py app/services/runs.py app/services/semantic_backfill.py app/services/semantic_ontology.py app/services/agent_task_verifications.py app/services/capabilities/semantics.py app/api/routers/semantics.py app/hotspot_prevention_classifier.py tests/unit/test_semantic_pass_lifecycle.py tests/unit/test_semantic_pass_reads.py tests/unit/test_semantic_registry_preview.py tests/unit/test_documents_api_semantics.py tests/unit/test_semantic_orchestration.py tests/unit/test_semantic_backfill_api.py tests/unit/test_run_logic.py tests/unit/test_agent_task_verifications.py tests/unit/test_hotspot_prevention.py`: pass
- `uv run pytest -q tests/unit/test_semantic_pass_lifecycle.py tests/unit/test_semantic_pass_reads.py tests/unit/test_semantic_registry_preview.py tests/unit/test_documents_api_semantics.py tests/unit/test_semantic_orchestration.py tests/unit/test_semantic_backfill_api.py tests/unit/test_run_logic.py tests/unit/test_agent_task_verifications.py tests/unit/test_hotspot_prevention.py tests/unit/test_semantic_candidates.py tests/unit/test_semantic_generation.py tests/unit/test_semantic_graph.py`: `95 passed`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs tests/integration/test_postgres_roundtrip.py tests/integration/test_semantic_backfill_roundtrip.py tests/integration/test_semantic_bootstrap_roundtrip.py tests/integration/test_semantic_candidate_roundtrip.py tests/integration/test_semantic_generation_roundtrip.py tests/integration/test_semantic_graph_roundtrip.py tests/integration/test_semantic_governance_ledger.py tests/integration/test_agent_task_semantic_orchestration_roundtrip.py`: `17 passed`
- `uv run docling-system-hotspot-prevention-check --strict`: `known_hotspots=11`, `changed_hotspots=1`, `blocked=0`, `allowed=31`, `exceptions=0`
- `uv run docling-system-hygiene-check`: `new hygiene regressions: none`
- `uv run docling-system-architecture-inspect`: `valid=true`, `violation_count=0`
- `uv run docling-system-capability-contracts`: `valid=true`
- `uv run docling-system-improvement-case-validate`: `valid=true`, `issue_count=0`
- `uv run docling-system-improvement-case-summary`: `case_count=29`, `status_counts.open=21`, `status_counts.deployed=7`, `status_counts.measured=1`, `measured_case_count=19`
- `uv run docling-system-architecture-quality-report --summary`: `hotspot_count=10`, `max_hotspot_risk_score=501.06`
- `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 12`: top hotspot remains `app/cli.py`, the semantics facade is absent from the top 12 churn hotspots, and the remaining Python cycle count is `5`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs`: `1926 passed`

## CLI Command Dispatch Boundary Milestone 0 Local Refresh

Milestone 0 is resolved locally through closeout commit `381ca15` on
2026-05-13 local / 2026-05-14 UTC. The stacked drafted baseline has been
replaced with the live post-semantics system state, and Milestone 1 is now
the next active CLI implementation slice.

Results:

- confirmed the prior stacked packets are closed locally as commits
  `3d7d090`, `1159297`, `1aa8378`, and `a2eb27e`
- promoted `docs/cli_command_dispatch_boundary_milestone_plan.md` from a
  queued stacked draft to the current active bounded implementation brief
- rerouted the active local follow-up owner case to
  `IC-9812A0B138D9` / `app/cli.py`
- refreshed `config/improvement_cases.yaml` and `config/hygiene_policy.yaml`
  so the active CLI owner case, live hotspot evidence, and hygiene routing
  agree before Milestone 1 begins
- refreshed the live CLI baseline: `app/cli.py` remains the top hotspot at
  `55` revisions / `1231` lines / `score 67705`, and the oldest open
  improvement case remains `IC-9812A0B138D9`
- confirmed the existing focused CLI owners remain small:
  `app/cli_commands/ingest.py` at `135` lines,
  `app/cli_commands/improvement_cases.py` at `149` lines, and
  `app/cli_commands/common.py` at `6` lines, so the remaining hotspot is
  still the direct command-body cluster in `app/cli.py`
- refreshed the downstream CLI cycle baseline to `5` Python cycle components
- local closeout commit:
  `381ca15`

Verification:

- `git diff --check`: pass
- `wc -l app/cli.py app/cli_commands/ingest.py app/cli_commands/improvement_cases.py app/cli_commands/common.py tests/unit/test_cli.py tests/unit/test_cli_search_harness.py tests/unit/test_cli_ingest.py app/agent_task_cli.py app/claim_support_replay_cli.py app/improvement_case_intake_cli.py`: refreshed live size baseline
- `uv run docling-system-architecture-quality-report --summary`: `hotspot_count=10`, `max_hotspot_risk_score=501.06`, top hotspots still include `app/cli.py`
- `uv run docling-system-improvement-case-summary`: `case_count=29`, `status_counts.open=21`, `status_counts.deployed=7`, `status_counts.measured=1`, `oldest_open_case_id=IC-9812A0B138D9`
- `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 12`: `app/cli.py` remains the top hotspot at `55` revisions / `1231` lines / `score 67705`; Python cycle components=`5`

## CLI Command Dispatch Boundary Milestone 1 Local Closeout

Milestone 1 is resolved locally through closeout commit `c674871` on
2026-05-13 local / 2026-05-14 UTC. The CLI facade-prevention ratchet is now
tightened, and Milestone 2 is the next active CLI implementation slice.

Results:

- tightened the `app/cli.py` hotspot-prevention rule so the facade now blocks
  new direct session or storage wiring plus parser-body or JSON-render
  scaffolding, in addition to the existing command-body and
  `ArgumentParser(...)` guards
- preserved the allowed seam for explicit forwarding wrappers and parser
  registration so `app.cli` can stay the compatibility dispatch surface while
  command bodies move into `app/cli_commands/*`
- added focused controlled-violation tests proving direct
  `get_session_factory()`, `with session_factory()`, `StorageService()`,
  `parser.add_argument(...)`, `parser.parse_args()`, and `json.dumps(...)`
  growth in `app/cli.py` is blocked while forwarding wrappers remain allowed
- refreshed `config/hygiene_policy.yaml` and `config/improvement_cases.yaml`
  for the classifier follow-on case `IC-6C1B516A3F92` after the stricter CLI
  gate expanded `app/hotspot_prevention_classifier.py` to `879` lines
- left `IC-9812A0B138D9` open on `app/cli.py`; the next routed CLI slice is
  still Milestone 2 runtime and maintenance command extraction
- local closeout commit:
  `c674871`

Verification:

- `git diff --check`: pass
- `uv run ruff check app/cli.py app/hotspot_prevention_classifier.py tests/unit/test_hotspot_prevention.py`: pass
- `uv run pytest -q tests/unit/test_hotspot_prevention.py`: `31 passed`
- `uv run docling-system-hotspot-prevention-check --strict`: `known_hotspots=11`, `changed_hotspots=0`, `blocked=0`, `allowed=0`, `exceptions=0`
- `uv run docling-system-hygiene-check`: `new hygiene regressions: none`
- `uv run docling-system-architecture-inspect`: `valid=true`, `violation_count=0`
- `uv run docling-system-capability-contracts`: `valid=true`, `facade_count=6`, `function_count=110`
- `uv run docling-system-architecture-quality-report --summary`: `hotspot_count=10`, `max_hotspot_risk_score=501.06`
- `uv run docling-system-improvement-case-validate`: `valid=true`, `issue_count=0`
- `uv run docling-system-improvement-case-summary`: `case_count=29`, `status_counts.open=21`, `status_counts.deployed=7`, `status_counts.measured=1`, `measured_case_count=20`
- `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 12`: `app/cli.py` remains the top hotspot at `55` revisions / `1231` lines / `score 67705`; Python cycle components=`5`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs`: `1928 passed`

## CLI Command Dispatch Boundary Milestone 2 Local Closeout

Milestone 2 is resolved locally through closeout commit `f5a4260`. The runtime
and maintenance command owner now lives in `app/cli_commands/runtime.py`, the
CLI facade is reduced, and Milestone 3 is the next active CLI implementation
slice.

Results:

- added `app/cli_commands/runtime.py` at `463` lines for the runtime and
  maintenance command family, including evaluation, audit, knowledge-base
  reset, semantic backfill, replay, evaluation-candidate, readiness, and
  ranking-dataset entrypoints
- reduced `app/cli.py` from `1231` lines to `926` by replacing the extracted
  runtime bodies with narrow zero-argument forwarding wrappers that preserve
  the stable `app.cli:run_*` entrypoint names
- moved direct runtime owner coverage into `tests/unit/test_cli_runtime.py`
  and added a focused `tests/unit/test_cli_entrypoints.py` forwarding-contract
  test while keeping `tests/unit/test_cli.py` as the legacy compatibility
  surface
- kept `app/cli_commands/common.py` at `6` lines, so the split did not create
  a generic CLI helper sink
- left `IC-9812A0B138D9` open on `app/cli.py`; the broader owner case is now
  reduced rather than resolved because `app/cli.py` still appears in the
  architecture-quality hotspot routing and still exceeds the default
  `600`-line budget even though it is no longer the top probe hotspot
- local closeout commit:
  `f5a4260`

Verification:

- `git diff --check`: pass
- `uv run ruff check app/cli.py app/cli_commands/common.py app/cli_commands/ingest.py app/cli_commands/improvement_cases.py app/cli_commands/runtime.py tests/unit/test_cli.py tests/unit/test_cli_entrypoints.py tests/unit/test_cli_runtime.py tests/unit/test_cli_improvement_cases.py tests/unit/test_cli_search_harness.py tests/unit/test_cli_ingest.py tests/unit/test_hotspot_prevention.py`: pass
- `uv run pytest -q tests/unit/test_cli.py tests/unit/test_cli_entrypoints.py tests/unit/test_cli_runtime.py tests/unit/test_cli_improvement_cases.py tests/unit/test_cli_search_harness.py tests/unit/test_cli_ingest.py tests/unit/test_hotspot_prevention.py`: `66 passed`
- `uv run docling-system-hotspot-prevention-check --strict`: `known_hotspots=11`, `changed_hotspots=2`, `blocked=0`, `allowed=2`, `exceptions=0`
- `uv run docling-system-hygiene-check`: `new hygiene regressions: none`
- `uv run docling-system-architecture-inspect`: `valid=true`, `violation_count=0`
- `uv run docling-system-capability-contracts`: `valid=true`, `facade_count=6`, `function_count=110`
- `uv run docling-system-architecture-quality-report --summary`: `hotspot_count=10`, `max_hotspot_risk_score=501.06`
- `uv run docling-system-improvement-case-validate`: `valid=true`, `issue_count=0`
- `uv run docling-system-improvement-case-summary`: `case_count=29`, `status_counts.open=21`, `status_counts.deployed=7`, `status_counts.measured=1`, `measured_case_count=20`
- `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 12`: top hotspot is `tests/unit/test_agent_tasks_api.py`; `app/cli.py` measures `55` revisions / `926` lines / `score 50930`; Python cycle components=`5`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs`: `1932 passed`

## CLI Command Dispatch Boundary Local Closeout

Milestones 3 and 4 are resolved locally through closeout commit `4a79a82`.
The scoped CLI dispatch-boundary knot under `IC-9812A0B138D9` is resolved
while the broader CLI owner case remains reduced/open, and the next active
bounded follow-on now routes to the agent-task schema aggregation packet under
`IC-24F3558D6091`.

Results:

- added `app/cli_commands/search_harness.py` at `604` lines for the
  retrieval-learning and search-harness command family, including dataset
  materialization, reranker evaluation and artifact generation, harness
  evaluation listing and detail reads, release-gate recording, audit-bundle
  creation, validation receipts, and search-harness optimization
- reduced `app/cli.py` from `926` lines to `375` by replacing the remaining
  direct command bodies with narrow forwarding wrappers that preserve the
  stable `app.cli:run_*` entrypoint names plus the legacy lazy wrapper seam
  names used by monkeypatched tests
- moved direct owner coverage into `tests/unit/test_cli_search_harness.py`,
  expanded `tests/unit/test_cli_entrypoints.py` to cover the forwarding and
  dependency contract, and reduced `tests/unit/test_cli.py` to an empty
  compatibility placeholder so the governed hotspot no longer absorbs direct
  owner assertions
- kept `app/cli_commands/runtime.py` at `463` lines and
  `app/cli_commands/common.py` at `6` lines, so the packet stayed within the
  planned two-owner CLI boundary and did not create a generic helper sink
- refreshed `config/hygiene_policy.yaml` so the CLI facade and both owner
  modules now carry exact verified ratchets, and refreshed
  `config/improvement_cases.yaml` so `IC-9812A0B138D9` records the committed
  post-split state at `375` lines / `risk_score 425.5`
- kept the broader owner case reduced/open because the architecture-quality
  summary still routes `app/cli.py` among the top hotspot paths even though
  the live architecture probe no longer lists it in the top 12 churn hotspots
- rerouted the next active bounded implementation brief to
  `docs/agent_task_schema_aggregation_boundary_milestone_plan.md` for
  `IC-24F3558D6091` / `app/schemas/agent_tasks.py`
- local closeout commit:
  `4a79a82`

Verification:

- `git diff --check`: pass
- `uv run ruff check app/cli.py app/cli_commands/common.py app/cli_commands/ingest.py app/cli_commands/improvement_cases.py app/cli_commands/runtime.py app/cli_commands/search_harness.py tests/unit/test_cli.py tests/unit/test_cli_entrypoints.py tests/unit/test_cli_runtime.py tests/unit/test_cli_improvement_cases.py tests/unit/test_cli_search_harness.py tests/unit/test_cli_ingest.py tests/unit/test_hotspot_prevention.py`: pass
- `uv run pytest -q tests/unit/test_cli.py tests/unit/test_cli_entrypoints.py tests/unit/test_cli_runtime.py tests/unit/test_cli_improvement_cases.py tests/unit/test_cli_search_harness.py tests/unit/test_cli_ingest.py tests/unit/test_hotspot_prevention.py`: `73 passed`
- `uv run docling-system-hotspot-prevention-check --strict`: `known_hotspots=11`, `changed_hotspots=2`, `blocked=0`, `allowed=3`, `exceptions=0`
- `uv run docling-system-hygiene-check`: `new hygiene regressions: none`
- `uv run docling-system-architecture-inspect`: `valid=true`, `violation_count=0`
- `uv run docling-system-capability-contracts`: `valid=true`, `facade_count=6`, `function_count=110`
- `uv run docling-system-architecture-quality-report --summary`: `hotspot_count=10`, `max_hotspot_risk_score=501.06`
- `uv run docling-system-improvement-case-validate`: `valid=true`, `issue_count=0`
- `uv run docling-system-improvement-case-summary`: `case_count=29`, `status_counts.open=21`, `status_counts.deployed=7`, `status_counts.measured=1`, `measured_case_count=20`
- `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 12`: top hotspot remains `tests/unit/test_agent_tasks_api.py`; `app/cli.py` is absent from the top 12 churn hotspots; Python cycle components=`5`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs`: `1939 passed`

## Agent Task Schema Aggregation Boundary Milestone 0 Local Refresh

Milestone 0 is resolved locally through closeout commit `5436f6f`. It
refreshed the live post-CLI state and promoted the schema
aggregation packet from a stacked drafted baseline to the active bounded
follow-on. The scoped schema-facade knot under `IC-24F3558D6091` remains
unresolved, and Milestone 1 is now the next active governance-ratchet slice.

Results:

- confirmed the five upstream packets are no longer drafted or in flight:
  `docs/claim_support_policy_impacts_boundary_milestone_plan.md`,
  `docs/evaluations_service_boundary_milestone_plan.md`,
  `docs/evidence_provenance_exports_boundary_milestone_plan.md`,
  `docs/semantics_service_boundary_milestone_plan.md`, and
  `docs/cli_command_dispatch_boundary_milestone_plan.md` are all committed
  local closeouts at `3d7d090`, `1159297`, `1aa8378`, `a2eb27e`, and
  `4a79a82`
- replaced the schema packet's drafted baseline with the live post-CLI
  evidence: `app/schemas/agent_tasks.py` remains a `461` line aggregation
  facade, its seven owner modules remain unchanged, the facade still exports
  `221` names, and the live architecture probe now records
  `app.schemas.agent_tasks` imported by `92` local modules with `5` Python
  cycle components across the repo
- confirmed the scoped issue still exists after the earlier closeouts:
  `app/schemas/agent_tasks.py` remains in the architecture-quality top-hotspot
  set even though the current top churn hotspot is
  `tests/unit/test_agent_tasks_api.py`
- refreshed the packet routing so the handoff and architecture index now agree
  that the schema aggregation plan is active and that Milestone 1, not
  Milestone 0, is the next code-changing slice
- recorded the remaining governance gap explicitly in the refreshed plan:
  `config/improvement_cases.yaml` still carries the older
  `risk_score=409.07` snapshot for `IC-24F3558D6091`, and that case is the
  live owner record Milestone 1 and later closeout work still need to refresh

Verification:

- `git status -sb`: `## main...origin/main [ahead 36]`
- `wc -l app/schemas/agent_tasks.py app/schemas/agent_task_core.py app/schemas/agent_task_claim_support.py app/schemas/agent_task_reports.py app/schemas/agent_task_search_workflows.py app/schemas/agent_task_semantic_generation.py app/schemas/agent_task_semantic_graph.py app/schemas/agent_task_semantics.py`: refreshed live size baseline
- `python - <<'PY' ... len(agent_tasks.__all__) ... PY`: `221`
- `uv run docling-system-architecture-quality-report --summary`: `hotspot_count=10`, `max_hotspot_risk_score=501.06`
- `uv run docling-system-improvement-case-summary`: `case_count=29`, `status_counts.open=21`, `status_counts.deployed=7`, `status_counts.measured=1`, `oldest_open_case_id=IC-9812A0B138D9`
- `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 12`: top hotspot `tests/unit/test_agent_tasks_api.py`; `app.schemas.agent_tasks` imported by `92` local modules; Python cycle components=`5`

## Agent Task Schema Aggregation Boundary Local Closeout

Milestones 1 through 4 are now resolved locally through closeout commit
`efe6d4e` for `IC-24F3558D6091`. The scoped schema-aggregation knot is
closed, the broader owner case remains reduced/open, and the next routed
packet is the oversized test hotspot decomposition follow-on.

Results:

- migrated every production `app/` importer named in the packet off
  `app.schemas.agent_tasks`, dropping production `app/` import fan-in to `0`
- reduced `app/schemas/agent_tasks.py` to a `38` line compatibility facade
  backed by owner-module export contracts while preserving the existing
  `221`-name public surface
- added `tests/unit/test_agent_task_schema_facade_contract.py` so the export
  union, identity forwarding, compact facade shape, no-sink rule, production
  import ban, and controlled violation fixtures are all executable
- tightened `config/hygiene_policy.yaml` to the exact verified facade ceiling
  and refreshed `IC-6C1B516A3F92` so the classifier's `1024`-line residual
  growth remains explicit rather than becoming a hidden hygiene regression
- refreshed `IC-24F3558D6091` to `risk_score=363.75`, `line_count=38`,
  `changes_90d=58`, `hygiene_finding_count=0`; the case remains reduced/open
  because the architecture-quality summary still routes the facade and `30`
  local test and integration modules still import it
- rerouted the next active bounded implementation brief to
  `docs/oversized_test_hotspots_boundary_milestone_plan.md`, with the first
  routed owner case already named as `IC-D9A84C20546B` /
  `tests/unit/test_agent_tasks_api.py`

Verification:

- `git diff --check`: pass
- `uv run ruff check app/schemas/agent_tasks.py app/schemas/agent_task_*.py app/api/routers/agent_tasks.py app/api/routers/agent_task_analytics.py app/api/routers/claim_support_policy_impacts.py app/agent_task_cli.py app/cli.py app/services/agent_tasks.py app/services/agent_task_*.py app/services/agent_actions/*.py app/services/capabilities/agent_orchestration*.py app/services/technical_report*.py app/services/semantic_generation.py app/services/search_harness_optimization.py app/services/claim_support_policy_impacts.py app/services/eval_workbench.py tests/unit/test_agent_task_schema_facade_contract.py tests/unit/test_agent_tasks.py tests/unit/test_agent_tasks_api.py tests/unit/test_agent_task_actions.py tests/unit/test_agent_task_context.py tests/unit/test_cli_agent_tasks.py tests/unit/test_hotspot_prevention.py`: pass
- `uv run pytest -q tests/unit/test_agent_task_schema_facade_contract.py tests/unit/test_agent_tasks.py tests/unit/test_agent_tasks_api.py tests/unit/test_agent_task_actions.py tests/unit/test_agent_task_context.py tests/unit/test_cli_agent_tasks.py tests/unit/test_hotspot_prevention.py`: `161 passed`
- `uv run docling-system-hotspot-prevention-check --strict`: `known_hotspots=12`, `changed_hotspots=3`, `added_lines=36`, `deleted_lines=459`, `blocked=0`, `allowed=31`, `exceptions=0`
- `uv run docling-system-hygiene-check`: `new hygiene regressions: none`
- `uv run docling-system-improvement-case-validate`: `valid=true`, `issue_count=0`
- `uv run docling-system-improvement-case-summary`: `case_count=29`, `status_counts.open=21`, `status_counts.deployed=7`, `status_counts.measured=1`, `oldest_open_case_id=IC-9812A0B138D9`
- `uv run docling-system-capability-contracts`: `valid=true`, `facade_count=6`, `function_count=110`
- `uv run docling-system-architecture-inspect`: `valid=true`, `violation_count=0`
- `uv run docling-system-architecture-quality-report --summary`: `hotspot_count=10`, `max_hotspot_risk_score=501.06`
- `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 12`: top hotspot remains `tests/unit/test_agent_tasks_api.py`; `app.schemas.agent_tasks` now routes `30` local imports; Python cycle components=`5`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs`: `1952 passed`

## Evidence Provenance Exports Boundary Local Closeout

Milestone 3 is resolved locally through closeout commit `1aa8378` on
2026-05-13. It closes the scoped provenance-export knot under
`IC-65AF4A6D8B1E` while leaving the broader evidence owner-family case
reduced/open.

Results:

- extracted provenance graph scaffolding and shared PROV assembly into
  `app/services/evidence_provenance_export_graph_core.py`
- extracted report-trace, claim-lineage, and operator-run graph ownership into
  `app/services/evidence_provenance_export_graph_report.py`
- extracted existing-artifact lookup, supersession recording, governance
  change-impact handling, persistence, freeze reuse, and fetch behavior into
  `app/services/evidence_provenance_export_lifecycle.py`
- reduced `app/services/evidence_provenance_exports.py` to a 14-line
  compatibility facade that only re-exports the stable public entrypoints and
  internal aliases required by `app/services/evidence.py`
- added a dedicated hotspot-prevention rule for
  `app/services/evidence_provenance_exports.py`, plus classifier coverage and
  focused owner tests for the three new modules
- refreshed `config/hygiene_policy.yaml` and `config/improvement_cases.yaml`
  so the compatibility facade, new owners, residual evidence-family routing,
  duplicate-helper allowlist, and classifier ratchet all match the live
  post-split state
- kept the broader evidence owner-family case reduced/open because
  `app/services/evidence_technical_report_exports.py`,
  `app/services/evidence_semantic_trace.py`,
  `app/services/evidence_claim_feedback.py`, and
  `app/services/evidence_audit_views.py` still exceed the default 600-line
  budget, and routed the next bounded implementation brief to
  `docs/semantics_service_boundary_milestone_plan.md`

Verification:

- `git diff --check`: pass
- `uv run ruff check app/services/evidence.py app/services/evidence_provenance.py app/services/evidence_provenance_exports.py app/services/evidence_provenance_export_graph_core.py app/services/evidence_provenance_export_graph_report.py app/services/evidence_provenance_export_lifecycle.py app/services/agent_task_worker.py app/services/capabilities/agent_orchestration.py app/api/routers/agent_tasks.py app/hotspot_prevention_classifier.py tests/unit/test_evidence_provenance.py tests/unit/test_evidence_provenance_export_graph_core.py tests/unit/test_evidence_provenance_export_graph_report.py tests/unit/test_evidence_provenance_export_lifecycle.py tests/unit/test_evidence_facade_contract.py tests/unit/test_agent_tasks_api.py tests/unit/test_hotspot_prevention.py`: pass
- `uv run pytest -q tests/unit/test_evidence_provenance.py tests/unit/test_evidence_provenance_export_graph_core.py tests/unit/test_evidence_provenance_export_graph_report.py tests/unit/test_evidence_provenance_export_lifecycle.py tests/unit/test_evidence_facade_contract.py tests/unit/test_agent_tasks_api.py tests/unit/test_hotspot_prevention.py`: `85 passed`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs tests/integration/test_technical_report_harness_roundtrip.py tests/integration/test_semantic_governance_ledger.py`: `3 passed`
- `uv run docling-system-hotspot-prevention-check --strict`: `known_hotspots=10`, `changed_hotspots=1`, `blocked=0`, `allowed=9`, `exceptions=0`
- `uv run docling-system-hygiene-check`: `new hygiene regressions: none`
- `uv run docling-system-architecture-inspect`: `valid=true`, `violation_count=0`
- `uv run docling-system-capability-contracts`: `valid=true`
- `uv run docling-system-improvement-case-validate`: `valid=true`, `issue_count=0`
- `uv run docling-system-improvement-case-summary`: `case_count=28`, `status_counts.open=20`, `status_counts.deployed=7`, `status_counts.measured=1`, `measured_case_count=18`
- `uv run docling-system-architecture-quality-report --summary`: `hotspot_count=10`, `max_hotspot_risk_score=501.06`
- `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 15`: top hotspot remains `app/cli.py`, the provenance-export facade is absent from the top 15 churn hotspots, and the remaining Python cycle count is `5`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs`: `1915 passed`

## Evaluations Service Boundary Milestone 4 Local Progress

Milestone 4 is resolved locally on 2026-05-13. It is the latest-read owner
extraction and final evaluation-facade reduction pass for
`IC-BF180637814C`. The scoped subsystem-knot is now resolved locally:
`app/services/evaluations.py` is reduced to `283` lines / `1` private helper,
the fixture/corpus owner remains in
`app/services/evaluation_fixtures.py` at `966` lines / `32` private helpers,
the scoring owner remains in `app/services/evaluation_scoring.py` at
`897` lines / `25` private helpers, the new read owner now lives in
`app/services/evaluation_reads.py` at `154` lines / `1` private helper, and
the broader owner case is now deployed locally because the architecture probe
no longer routes the facade in the top 15 churn hotspots or remaining Python
cycle components.

Results:

- extracted evaluation summary DTO assembly and latest-evaluation summary and
  detail reads into `app/services/evaluation_reads.py`
- kept `app/services/evaluations.py` as the stable import facade, including
  `evaluate_run(...)`, `resolve_baseline_run_id(...)`, and compatibility
  wrappers for the extracted latest-read owner helpers
- preserved `app/services/documents.py`,
  `app/services/capabilities/evaluation.py`, and the
  `/documents/{document_id}/evaluations/latest` route family without contract
  drift while adding focused read-owner coverage in
  `tests/unit/test_evaluation_reads.py` at `199` lines
- ratcheted `config/hygiene_policy.yaml` to the measured post-split ceilings:
  `app/services/evaluations.py` at `283` lines / `1` private helper,
  `app/services/evaluation_fixtures.py` at `966` lines / `32` private
  helpers, `app/services/evaluation_scoring.py` at `897` lines /
  `25` private helpers, and `app/services/evaluation_reads.py` at
  `154` lines / `1` private helper
- refreshed `docs/evaluations_service_boundary_milestone_plan.md`,
  `docs/agentic_architecture_index.md`, and this handoff so the evaluations
  packet is now resolved locally and the next active gate routes to the
  evidence provenance-export owner split
- architecture quality remains `hotspot_count=10` with
  `max_hotspot_risk_score=501.06`; the architecture-quality summary top-five
  still excludes the evaluation facade, and the architecture probe top 15 no
  longer lists `app/services/evaluations.py` or the remaining Python cycle
  components
- local closeout commit:
  `1159297`
- next routed stacked follow-on after the evaluations packet now begins with
  `docs/evidence_provenance_exports_boundary_milestone_plan.md`

Verification:

- `git diff --check`
- `uv run ruff check app/services/evaluations.py app/services/evaluation_fixtures.py app/services/evaluation_scoring.py app/services/evaluation_reads.py app/services/evaluation_execution.py app/services/documents.py app/services/runs.py app/services/quality.py app/services/semantic_backfill.py app/services/evaluation_corpus_runner.py app/services/evaluation_embedding_cache.py app/services/knowledge_base_reset.py app/services/capabilities/evaluation.py tests/unit/test_evaluation_service.py tests/unit/test_evaluation_fixtures.py tests/unit/test_evaluation_scoring.py tests/unit/test_evaluation_reads.py tests/unit/test_documents_api.py tests/unit/test_quality_service.py tests/unit/test_eval_config.py tests/unit/test_capability_contracts.py tests/unit/test_api_architecture.py tests/unit/test_hotspot_prevention.py`:
  pass
- `uv run pytest -q tests/unit/test_evaluation_reads.py tests/unit/test_evaluation_service.py tests/unit/test_documents_api.py`:
  `34 passed`
- `uv run pytest -q tests/unit/test_evaluation_service.py tests/unit/test_evaluation_fixtures.py tests/unit/test_evaluation_scoring.py tests/unit/test_evaluation_reads.py tests/unit/test_documents_api.py tests/unit/test_quality_service.py tests/unit/test_eval_config.py tests/unit/test_capability_contracts.py tests/unit/test_api_architecture.py tests/unit/test_hotspot_prevention.py`:
  `122 passed`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs tests/integration/test_postgres_roundtrip.py tests/integration/test_multivector_retrieval.py tests/integration/test_eval_workbench_roundtrip.py`:
  `12 passed`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs`:
  `1907 passed`
- `uv run docling-system-hotspot-prevention-check --strict`:
  `known_hotspots=9`, `changed_hotspots=1`, `blocked=0`, `allowed=4`,
  `exceptions=0`
- `uv run docling-system-hygiene-check`: `new hygiene regressions: none`
- `uv run docling-system-capability-contracts`: `valid=true`
- `uv run docling-system-improvement-case-validate`: `valid=true`,
  `issue_count=0`
- `uv run docling-system-improvement-case-summary`: `case_count=28`,
  `status_counts.open=20`, `status_counts.deployed=7`,
  `status_counts.measured=1`, `measured_case_count=18`
- `uv run docling-system-architecture-quality-report --summary`:
  `hotspot_count=10`, `max_hotspot_risk_score=501.06`
- `uv run docling-system-evaluation-data-readiness --output storage/evaluation_data_readiness.latest.json`:
  `regression_ready=true`, `court_grade_ready=true`, `failed_gate_count=0`
- `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 15`:
  `app/services/evaluations.py` is absent from the hotspot routing list and
  absent from the remaining Python cycle components; Python cycle component
  count remains `4`

## Claim Support Policy Impacts Boundary Milestone 4 Local Progress

Milestone 4 is closed locally as commit `3d7d090`. It is a
behavior-preserving claim-support policy-impact modularization pass behind the
existing `app/services/claim_support_policy_impacts.py` compatibility facade.

Results:

- added `app/services/claim_support_policy_impact_views.py`
- added `app/services/claim_support_policy_impact_replay.py`
- moved list, summary, worklist, alerts, escalation, and detail read-model
  logic into the views owner while keeping the stable
  `app.services.claim_support_policy_impacts` import surface through explicit
  forwarding wrappers
- moved replay queueing, replay-status refresh, replay-closure governance, and
  integrity enforcement into the replay owner while keeping the route and
  agent-task contracts stable
- hardened `config/hotspot_prevention.yaml` and
  `app/hotspot_prevention_classifier.py` so new read-model, alert, and
  replay-lifecycle bodies are blocked directly in the compatibility facade
- added focused owner-module coverage in
  `tests/unit/test_claim_support_policy_impact_views.py` and
  `tests/unit/test_claim_support_policy_impact_replay.py`
- reduced `app/services/claim_support_policy_impacts.py` from `2011` lines /
  `42` private helpers to `184` lines / `0` private helpers, governed
  `app/services/claim_support_policy_impact_views.py` at `899` lines /
  `16` private helpers, and governed
  `app/services/claim_support_policy_impact_replay.py` at `898` lines /
  `11` private helpers under `owner_case_id: IC-E2270F89B397`
- updated `config/improvement_cases.yaml` so `IC-E2270F89B397` records the
  reduced-but-still-open owner state after the split
- local closeout commit: `3d7d090`
- next routed stacked follow-on is
  `docs/evaluations_service_boundary_milestone_plan.md`

Verification:

- `git diff --check`
- `uv run ruff check app/services/claim_support_policy_impacts.py app/services/claim_support_policy_impact_views.py app/services/claim_support_policy_impact_replay.py app/services/claim_support_replay_alert_promotions.py app/api/routers/claim_support_policy_impacts.py app/api/routers/agent_tasks.py app/hotspot_prevention_classifier.py tests/unit/test_claim_support_policy_impacts.py tests/unit/test_claim_support_policy_impact_views.py tests/unit/test_claim_support_policy_impact_replay.py tests/unit/test_agent_tasks_api.py tests/unit/test_hotspot_prevention.py`
- `uv run pytest -q tests/unit/test_claim_support_policy_impacts.py tests/unit/test_claim_support_policy_impact_views.py tests/unit/test_claim_support_policy_impact_replay.py tests/unit/test_agent_tasks_api.py tests/unit/test_hotspot_prevention.py`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs tests/integration/test_claim_support_policy_activation_roundtrip.py tests/integration/test_claim_support_policy_activation_change_impacts_roundtrip.py tests/integration/test_claim_support_policy_change_impacts_roundtrip.py tests/integration/test_claim_support_policy_change_impacts_replay_alert_prevalidation.py tests/integration/test_claim_support_policy_change_impacts_replay_alert_promotions.py tests/integration/test_claim_support_policy_change_impacts_replay_alert_governance.py tests/integration/test_claim_support_policy_mined_failures_roundtrip.py tests/integration/test_claim_support_judge_evaluation_roundtrip.py`
- `uv run docling-system-hotspot-prevention-check --strict`
- `uv run docling-system-hygiene-check`
- `uv run docling-system-architecture-inspect`
- `uv run docling-system-capability-contracts`
- `uv run docling-system-architecture-quality-report --summary`
- `uv run docling-system-improvement-case-validate`
- `uv run docling-system-improvement-case-summary`
- `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 12`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs`

## Search Execution Orchestration Boundary Milestone 1 Local Progress

Milestone 1 is closed locally as commit `dae5e4f`. It is a behavior-preserving search
service modularization pass behind the existing `app/services/search.py`
compatibility facade.

Results:

- added `app/services/search_execution_orchestration.py`
- moved `_load_keyword_candidates`, `_load_semantic_candidates`,
  `_apply_metadata_supplement_stage`, `_resolve_candidate_items`,
  `_build_search_execution_details`, and `execute_search(...)` into that owner
  module while keeping the public `app.services.search` import surface stable
  through an explicit forwarding wrapper
- hardened `config/hotspot_prevention.yaml` and
  `app/hotspot_prevention_classifier.py` so execution-orchestration,
  candidate-loading, and search-detail assembly growth are blocked directly in
  `app/services/search.py`
- added focused owner-module coverage in
  `tests/unit/test_search_execution_orchestration.py`
- reduced `app/services/search.py` from `2089` lines / `37` private helpers to
  `1592` lines / `32` private helpers and governed
  `app/services/search_execution_orchestration.py` at `532` lines /
  `6` private helpers under `owner_case_id: IC-1D03DBFE8492`
- updated `config/improvement_cases.yaml` so `IC-1D03DBFE8492` records the
  reduced-but-still-open search hotspot state after the orchestration split
- local closeout commit: `dae5e4f`
- next routed stacked follow-on is
  `docs/claim_support_policy_impacts_boundary_milestone_plan.md`

Verification:

- `git diff --check`
- `uv run ruff check app/services/search.py app/services/search_execution_orchestration.py app/services/search_execution_persistence.py app/services/search_hydration.py app/hotspot_prevention_classifier.py tests/unit/test_search_service.py tests/unit/test_search_execution_orchestration.py tests/unit/test_search_execution_persistence.py tests/unit/test_hotspot_prevention.py`
- `uv run pytest -q tests/unit/test_search_service.py tests/unit/test_search_execution_orchestration.py tests/unit/test_search_execution_persistence.py tests/unit/test_hotspot_prevention.py`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs tests/integration/test_postgres_roundtrip.py tests/integration/test_multivector_retrieval.py`
- `uv run docling-system-hotspot-prevention-check --strict`
- `uv run docling-system-hygiene-check`
- `uv run docling-system-architecture-inspect`
- `uv run docling-system-architecture-quality-report --summary`
- `uv run docling-system-capability-contracts`
- `uv run docling-system-improvement-case-summary`
- `uv run docling-system-improvement-case-validate`
- `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 12`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs`

## Search Execution Persistence Boundary Milestone 1 Local Progress

Milestone 1 is closed locally. It is a behavior-preserving search service
modularization pass behind the existing `app/services/search.py`
compatibility facade.

Results:

- added `app/services/search_execution_persistence.py`
- moved ranked-result evidence payload assembly, search request/result
  persistence, result-span persistence, and knowledge-operator trace
  persistence into that owner module while keeping the original service surface
  import-stable through alias forwarding
- hardened `config/hotspot_prevention.yaml` and
  `app/hotspot_prevention_classifier.py` so new persistence and
  operator-trace payload growth in `app/services/search.py` is blocked
- added focused owner-module coverage in
`tests/unit/test_search_execution_persistence.py`
- reduced `app/services/search.py` from `2496` lines / `42` private helpers to
  `2089` lines / `37` private helpers and governed
  `app/services/search_execution_persistence.py` at `423` lines /
  `6` private helpers under `owner_case_id: IC-1D03DBFE8492`
- updated `config/improvement_cases.yaml` so `IC-1D03DBFE8492` records the
  reduced-but-still-open search hotspot state after the persistence split
- local closeout commit: `f55b474`
- the next routed implementation slice inside the same owner case is the
  remaining execution-orchestration cluster in `execute_search(...)` and
  adjacent candidate-loading/detail assembly paths

Verification:

- `git diff --check`
- `uv run ruff check app/services/search.py app/services/search_execution_persistence.py tests/unit/test_search_service.py tests/unit/test_search_execution_persistence.py tests/unit/test_hotspot_prevention.py`
- `uv run pytest -q tests/unit/test_search_service.py tests/unit/test_search_execution_persistence.py tests/unit/test_hotspot_prevention.py`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs tests/integration/test_postgres_roundtrip.py tests/integration/test_multivector_retrieval.py`
- `uv run docling-system-hotspot-prevention-check --strict`
- `uv run docling-system-hygiene-check`
- `uv run docling-system-architecture-inspect`
- `uv run docling-system-architecture-quality-report --summary`
- `uv run docling-system-capability-contracts`
- `uv run docling-system-improvement-case-validate`
- `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 12`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs`

## Search Hydration Boundary Milestone 1 Local Progress

Milestone 1 is closed locally as commit `14390ad`. It is a behavior-preserving search service
modularization pass behind the existing `app/services/search.py`
compatibility facade.

Results:

- added `app/services/search_hydration.py`
- moved span-backed query builders, ranked-result hydration,
  selected-result evidence-span loading, and late-interaction hydration into
  that owner module while keeping the original service surface import-stable
  through alias forwarding
- added focused compatibility coverage in
  `tests/unit/test_search_hydration.py`
- reduced `app/services/search.py` from `2851` lines / `53` private helpers to
  `2496` lines / `42` private helpers and governed
  `app/services/search_hydration.py` at `392` lines / `11` private helpers
  under `owner_case_id: IC-1D03DBFE8492`
- updated `config/improvement_cases.yaml` so `IC-1D03DBFE8492` records the
  reduced-but-still-open search hotspot state after the hydration split
- local closeout commit: `14390ad`
- the next routed implementation slice inside the same owner case is search
  execution persistence and operator-trace payload assembly

Verification:

- `git diff --check`
- `uv run ruff check app/services/search.py app/services/search_hydration.py tests/unit/test_search_service.py tests/unit/test_search_hydration.py`
- `uv run pytest -q tests/unit/test_search_hydration.py tests/unit/test_search_service.py tests/unit/test_hotspot_prevention.py`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs tests/integration/test_postgres_roundtrip.py tests/integration/test_multivector_retrieval.py`
- `uv run docling-system-hotspot-prevention-check --strict`
- `uv run docling-system-hygiene-check`
- `uv run docling-system-architecture-inspect`
- `uv run docling-system-architecture-quality-report --summary`
- `uv run docling-system-capability-contracts`
- `uv run docling-system-improvement-case-validate`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs`

## Agent-Task Orchestration Boundary Milestone 5 Local Progress

Milestone 5 is closed locally as commit `7cf7465` and closes the agent-task
orchestration boundary. Because the Milestone 4 semantic-family extraction
remained uncommitted before closeout, the current packet includes both the
Milestone 4 owner-family move and the Milestone 5 lifecycle alignment.

Results:

- moved the remaining semantic analysis executors into
  `app/services/agent_actions/semantic_analysis_actions.py`
- moved the remaining semantic drafting executors into
  `app/services/agent_actions/semantic_drafting_actions.py`
- moved the remaining semantic verification and disagreement-triage executors
  into `app/services/agent_actions/semantic_verification_actions.py`
- moved the matching semantic context builders into
  `app/services/agent_task_context_semantic_analysis.py`,
  `app/services/agent_task_context_semantic_drafting.py`, and
  `app/services/agent_task_context_semantic_verification.py`
- moved the still-central technical report builder family into
  `app/services/agent_task_context_technical_reports.py` so the compatibility
  facade stays purely compositional
- preserved the public `list_agent_task_actions()`, action index output,
  validation defaults, context-builder lookup names, and worker execution
  semantics while updating focused tests to patch the new owner modules
  directly
- reduced `app/services/agent_task_actions.py` from 782 lines / 16 private
  helpers to 163 lines / 1 private helper and reduced
  `app/services/agent_task_context.py` from 1,879 lines / 21 private helpers
  to 121 lines / 0 private helpers
- removed the now-obsolete central context reflow exceptions from
  `config/hotspot_prevention.yaml`; strict mode now passes with zero
  exceptions
- tightened `config/hygiene_policy.yaml` so the narrowed facades and
  under-budget owner modules now use exact verified ceilings, while the
  oversized extracted owner modules keep explicit inherited ratchets
- transitioned `IC-A1E186A34097` and `IC-E52B6C7B22FD` to deployed locally in
  `config/improvement_cases.yaml`
- refreshed `docs/architecture_boundaries.md`,
  `docs/agentic_architecture_index.md`, and
  `docs/agent_task_orchestration_boundary_milestone_plan.md` so the resolved
  boundary shape and next routed hotspot are recorded
- local closeout commit: `7cf7465`

Verification:

- `git diff --check`
- `uv run ruff check app/services/agent_task_actions.py app/services/agent_actions/search_harness.py app/services/agent_actions/semantic_governance_actions.py app/services/agent_actions/semantic_analysis_actions.py app/services/agent_actions/semantic_drafting_actions.py app/services/agent_actions/semantic_verification_actions.py app/services/agent_actions/report_actions.py app/services/agent_task_context.py app/services/agent_task_context_semantic.py app/services/agent_task_context_search_harness.py app/services/agent_task_context_semantic_governance.py app/services/agent_task_context_semantic_analysis.py app/services/agent_task_context_semantic_drafting.py app/services/agent_task_context_semantic_verification.py app/services/agent_task_context_technical_reports.py tests/unit/test_agent_action_contracts.py tests/unit/test_agent_task_actions.py tests/unit/test_agent_task_context.py tests/unit/test_agent_task_context_semantic.py tests/unit/test_agent_task_action_lookup.py tests/unit/test_agent_tasks.py tests/unit/test_agent_task_worker.py tests/unit/test_agent_tasks_api.py tests/unit/test_agent_task_actions_semantic_registry.py tests/unit/test_agent_task_actions_ontology.py tests/unit/test_agent_task_actions_semantic_documents.py tests/unit/test_agent_task_actions_semantic_graph.py tests/unit/test_agent_task_triage.py tests/unit/test_hotspot_prevention.py`
- `uv run pytest -q tests/unit/test_agent_action_contracts.py tests/unit/test_agent_task_actions.py tests/unit/test_agent_task_context.py tests/unit/test_agent_task_context_semantic.py tests/unit/test_agent_task_action_lookup.py tests/unit/test_agent_tasks.py tests/unit/test_agent_task_worker.py tests/unit/test_agent_tasks_api.py tests/unit/test_agent_task_actions_semantic_registry.py tests/unit/test_agent_task_actions_ontology.py tests/unit/test_agent_task_actions_semantic_documents.py tests/unit/test_agent_task_actions_semantic_graph.py tests/unit/test_agent_task_triage.py tests/unit/test_hotspot_prevention.py`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs tests/integration/test_agent_task_semantic_orchestration_roundtrip.py tests/integration/test_agent_task_triage_roundtrip.py tests/integration/test_claim_support_judge_evaluation_roundtrip.py`
- `uv run docling-system-agent-task-action-index`
- `uv run docling-system-capability-contracts`
- `uv run docling-system-hotspot-prevention-check --strict`
- `uv run docling-system-hygiene-check`
- `uv run docling-system-architecture-inspect`
- `uv run docling-system-architecture-quality-report --summary`
- `uv run docling-system-improvement-case-summary`
- `uv run docling-system-improvement-case-validate`
- `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 12`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs`

Verified results:

- `git diff --check`: pass
- focused ruff checks: pass
- focused unit suites: `175 passed`
- semantic orchestration, triage, and claim-support integration suites:
  `13 passed`
- action index: `schema_name=agent_action_index`, `schema_version=1.0`
- capability contracts: `valid=true`, `facade_count=6`, `function_count=110`
- strict hotspot prevention: `known_hotspots=7`, `changed_hotspots=2`,
  `blocked=0`, `exceptions=0`
- hygiene: `new hygiene regressions: none`
- architecture inspection: `valid=true`, `violation_count=0`
- architecture quality: `hotspot_count=10`, `max_hotspot_risk_score=531.06`
- improvement-case summary: `case_count=28`, `status_counts.open=21`,
  `status_counts.deployed=6`, `status_counts.measured=1`
- improvement-case validation: `valid=true`, `issue_count=0`
- architecture probe: top hotspot is now `app/services/search.py`;
  `app/services/agent_task_actions.py` and
  `app/services/agent_task_context.py` are both out of the top 12 churn
  hotspots; Python cycle components remain `3`
- full DB-backed suite: `1875 passed`

Residual risk and next boundary:

- Milestone 5 closes the remaining central ownership ambiguity in the
  orchestration boundary, but the extracted owner modules still carry explicit
  inherited hygiene ratchets where they remain above 600 lines.
- The next routed architecture hotspot is
  `IC-1D03DBFE8492` / `app/services/search.py`.
- Do not mix this milestone with the unrelated evidence owner-family follow-up
  when staging a commit.

## Evidence Hotspot Owner Plan Local Closeout

This closeout implements the dedicated evidence hotspot execution brief end to
end under local verification.

Results:

- added `app/services/evidence_claim_feedback.py`,
  `app/services/evidence_release_readiness.py`,
  `app/services/evidence_manifests.py`,
  `app/services/evidence_semantic_trace.py`,
  `app/services/evidence_claim_support_impacts.py`,
  `app/services/evidence_claim_support_replay_alerts.py`,
  `app/services/evidence_provenance_exports.py`, and
  `app/services/evidence_audit_views.py` for the remaining evidence owner
  families
- reduced `app/services/evidence.py` from 6,307 lines / 81 private helpers to
  a 141-line / 4-private-helper compatibility facade
- preserved the public `app.services.evidence` surface, including the
  settings-aware provenance wrappers used by tests, and added
  `tests/unit/test_evidence_facade_contract.py` to hold that contract
- updated `config/hotspot_prevention.yaml`,
  `config/hygiene_policy.yaml`, and `config/improvement_cases.yaml` so the
  facade is gated explicitly and the residual oversized owner-family debt is
  routed into `IC-65AF4A6D8B1E`

Verification:

- `git diff --check`
- `uv run ruff check app/services/evidence.py app/services/evidence_*.py tests/unit/test_evidence_*.py`
- `uv run pytest -q tests/unit/test_evidence_common.py tests/unit/test_evidence_records.py tests/unit/test_evidence_facade_contract.py tests/unit/test_evidence_provenance.py tests/unit/test_replay_alert_waiver_integrity.py tests/unit/test_evidence_technical_report_exports.py tests/unit/test_technical_reports.py`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs tests/integration/test_technical_report_harness_roundtrip.py tests/integration/test_claim_support_policy_change_impacts_replay_alert_prevalidation.py tests/integration/test_claim_support_policy_change_impacts_replay_alert_promotions.py`
- `uv run docling-system-hotspot-prevention-check --strict`
- `uv run docling-system-architecture-inspect`
- `uv run docling-system-capability-contracts`
- `uv run docling-system-hygiene-check`
- `uv run docling-system-improvement-case-summary`
- `uv run docling-system-improvement-case-validate`
- `uv run docling-system-architecture-quality-report --summary`
- `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 12`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs`
- `uv run docling-system-evaluation-data-readiness --output storage/evaluation_data_readiness.latest.json`
- `uv run docling-system-agent-trace-review --limit 5 --skip-hygiene`

Verified results:

- focused unit suites: `45 passed`
- focused DB-backed integration suites: `3 passed`
- strict hotspot prevention: pass, `blocked=0`
- architecture inspection: `valid=true`, `violation_count=0`
- capability contracts: `valid=true`, `facade_count=6`, `function_count=110`
- hygiene: `new hygiene regressions: none`
- improvement-case summary: `case_count=27`, `status_counts.open=22`,
  `status_counts.deployed=4`, `status_counts.measured=1`
- architecture quality: `hotspot_count=10`, `max_hotspot_risk_score=541.06`
- architecture probe: top hotspot is `app/services/agent_task_actions.py`;
  `app/services/evidence.py` is out of the top 12 churn hotspots
- full DB-backed suite: `1867 passed`
- evaluation-data readiness: `passed_gate_count=11`, `failed_gate_count=0`
- agent-trace review: `observation_count=0`

## Audit Bundle And Retrieval Learning Hotspots Milestone 5 Closeout

Milestone 5 is the final compatibility-facade closeout for
`IC-2112B1ADC5E8` / `app/services/audit_bundles.py` and
`IC-0D58F1624037` / `app/services/retrieval_learning.py`. It proves both
surfaces now operate as narrow compatibility facades with explicit owner
families, updated improvement-case evidence, and exact no-growth ratchets.

Results:

- added `app/services/audit_bundle_release_payload_serialization.py` for
  search-harness release payload and reference serialization
- added `app/services/audit_bundle_release_payload_validation.py` for release
  payload schema, source-integrity, and semantic-governance validation
- added `app/services/audit_bundle_release_payload_prov.py` for PROV graph
  construction and JSON-LD validation
- added `app/services/audit_bundle_release_payloads.py` for release payload
  orchestration
- reduced `app/services/audit_bundles.py` from 2,203 lines / 41 private
  helpers to 595 lines / 20 private helpers while preserving the public
  audit-bundle entrypoints
- kept `app/services/retrieval_learning.py` at 143 lines / 0 private helpers
  and added both focused facade-delegation tests plus exact facade-shape gates
  for the public function surface and helper budget
- closed the follow-up drift the first Milestone 5 closeout created:
  `app/services/audit_bundles.py` is now below the default 600-line facade
  budget, improvement-case deployed refs now point at `d85cd90`, and the
  facade contract tests now prevent silent surface regrowth
- updated `config/hygiene_policy.yaml`,
  `config/improvement_cases.yaml`,
  `docs/audit_bundle_and_retrieval_learning_hotspots_milestone_plan.md`,
  `docs/agentic_architecture_index.md`,
  `docs/improvement_loop.md`, and this handoff so the routed next step stays
  explicit
- the next routed implementation step is now
  `IC-050E60059A34` / `app/services/evidence.py`

Verification:

- `git diff --check`
- `uv run ruff check app/services/audit_bundles.py app/services/audit_bundle_release_payload_serialization.py app/services/audit_bundle_release_payload_validation.py app/services/audit_bundle_release_payload_prov.py app/services/audit_bundle_release_payloads.py tests/unit/test_audit_bundles_facade_contract.py tests/unit/test_audit_bundle_release_payload_validation.py tests/unit/test_retrieval_learning_facade_contract.py`
- `uv run pytest -q tests/unit/test_audit_bundles_facade_contract.py tests/unit/test_audit_bundle_release_payload_validation.py tests/unit/test_retrieval_learning_facade_contract.py tests/unit/test_audit_bundle_training_runs.py tests/unit/test_audit_bundle_validation_receipts.py tests/unit/test_retrieval_learning_datasets.py tests/unit/test_search_api_harnesses.py tests/unit/test_agent_tasks_api.py tests/unit/test_retrieval_learning_replay_alert_sources.py`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs tests/integration/test_search_harness_releases.py tests/integration/test_semantic_governance_ledger.py tests/integration/test_retrieval_learning_ledger.py tests/integration/test_technical_report_harness_roundtrip.py`
- `uv run docling-system-architecture-inspect`
- `uv run docling-system-capability-contracts`
- `uv run docling-system-architecture-quality-report --summary`
- `uv run docling-system-hygiene-check`
- `uv run docling-system-improvement-case-summary`
- `uv run docling-system-improvement-case-validate`
- `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 12`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs`
- `uv run docling-system-evaluation-data-readiness --output storage/evaluation_data_readiness.latest.json`
- `uv run docling-system-agent-trace-review --limit 5 --skip-hygiene`

Verified results:

- `git diff --check`: pass
- focused `ruff` check: pass
- focused unit and route suite: `61 passed`
- focused DB-backed integration suite: `14 passed`
- `uv run docling-system-architecture-inspect`: `valid=true`,
  `violation_count=0`
- `uv run docling-system-capability-contracts`: `valid=true`,
  `facade_count=6`, `function_count=110`
- `uv run docling-system-architecture-quality-report --summary`:
  `hotspot_count=10`, `max_hotspot_risk_score=561.06`
- `uv run docling-system-hygiene-check`: `new hygiene regressions: none`
- `uv run docling-system-improvement-case-summary`: `case_count=26`,
  `status_counts.open=22`, `status_counts.deployed=3`,
  `status_counts.measured=1`, `oldest_open_case_id=IC-050E60059A34`
- `uv run docling-system-improvement-case-validate`: `valid=true`,
  `issue_count=0`
- architecture probe reports `app/services/evidence.py` as the top churn
  hotspot while `app/services/audit_bundles.py` and
  `app/services/retrieval_learning.py` are out of the top 12 churn hotspots
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs`: `1859 passed`
- `uv run docling-system-evaluation-data-readiness --output storage/evaluation_data_readiness.latest.json`:
  `passed_gate_count=11`, `failed_gate_count=0`
- `uv run docling-system-agent-trace-review --limit 5 --skip-hygiene`:
  `observation_count=0`

## Audit Bundle And Retrieval Learning Hotspots Milestone 3 Progress

Milestone 3 is the audit-bundle slice for
`IC-2112B1ADC5E8` / `app/services/audit_bundles.py`. It reduces the broad
compatibility facade by routing retrieval-training-run payload and provenance
construction into a focused owner module without changing the public service
surface.

Results:

- added `app/services/audit_bundle_training_runs.py` for retrieval-training-run
  payload serialization, semantic-governance loading, provenance graph
  construction, and bundle row materialization
- reduced `app/services/audit_bundles.py` from 3,018 lines / 51 private
  helpers to 2,203 lines / 41 private helpers while preserving the
  compatibility facade and existing release-bundle entrypoints
- committed the milestone locally as `7b26bc4`
  (`services: complete hotspot milestone 3 audit-bundle training split`)
- added focused owner tests in
  `tests/unit/test_audit_bundle_training_runs.py`
- updated `config/hygiene_policy.yaml`,
  `config/improvement_cases.yaml`,
  `docs/audit_bundle_and_retrieval_learning_hotspots_milestone_plan.md`,
  `docs/agentic_architecture_index.md`,
  `docs/improvement_loop.md`, and this handoff so the current local milestone
  state and next routed follow-up stay explicit
- the durable closeout remains aligned to the committed Milestone 3 state while
  the next routed implementation step stays the retrieval-learning dataset and
  governance split

Verification:

- `git diff --check`
- `uv run ruff check app tests`
- `uv run docling-system-architecture-inspect`
- `uv run docling-system-capability-contracts`
- `uv run docling-system-architecture-quality-report --summary`
- `uv run docling-system-hygiene-check`
- `uv run docling-system-improvement-case-summary`
- `uv run docling-system-improvement-case-validate`
- `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 12`
- `uv run pytest -q tests/unit/test_audit_bundle_training_runs.py tests/unit/test_audit_bundle_validation_receipts.py tests/unit/test_search_api_harnesses.py tests/unit/test_search_api_learning_audit.py`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs tests/integration/test_search_harness_releases.py`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs tests/integration/test_retrieval_learning_ledger.py`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs tests/integration/test_semantic_governance_ledger.py`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs tests/integration/test_technical_report_harness_roundtrip.py`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs`
- `uv run docling-system-evaluation-data-readiness --output storage/evaluation_data_readiness.latest.json`
- `uv run docling-system-agent-trace-review --limit 5 --skip-hygiene`

Verified results:

- `git diff --check`: pass
- `uv run ruff check app tests`: pass
- `uv run docling-system-architecture-inspect`: `valid=true`,
  `violation_count=0`
- `uv run docling-system-capability-contracts`: `valid=true`,
  `facade_count=6`, `function_count=110`
- `uv run docling-system-architecture-quality-report --summary`:
  `hotspot_count=10`, `max_hotspot_risk_score=561.06`
- `uv run docling-system-hygiene-check`: `new hygiene regressions: none`
- `uv run docling-system-improvement-case-summary`: `case_count=26`,
  `status_counts.open=24`, `status_counts.deployed=1`,
  `status_counts.measured=1`, `oldest_open_case_id=IC-050E60059A34`
- `uv run docling-system-improvement-case-validate`: `valid=true`,
  `issue_count=0`
- architecture probe reports `app/services/audit_bundles.py` is reduced to
  2,203 lines and no longer appears in the top 12 churn hotspots
- `uv run pytest -q tests/unit/test_audit_bundle_training_runs.py tests/unit/test_audit_bundle_validation_receipts.py tests/unit/test_search_api_harnesses.py tests/unit/test_search_api_learning_audit.py`:
  `18 passed`
- `uv run pytest -q tests/unit/test_agent_tasks_api.py`: `37 passed`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs tests/integration/test_search_harness_releases.py`:
  `1 passed`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs tests/integration/test_retrieval_learning_ledger.py`:
  `10 passed`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs tests/integration/test_semantic_governance_ledger.py`:
  `2 passed`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs tests/integration/test_technical_report_harness_roundtrip.py`:
  `1 passed`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs`: `1847 passed`
- `uv run docling-system-evaluation-data-readiness --output storage/evaluation_data_readiness.latest.json`:
  `passed_gate_count=11`, `failed_gate_count=0`
- `uv run docling-system-agent-trace-review --limit 5 --skip-hygiene`:
  `observation_count=0`

Next routed follow-up:

- owner case remains `IC-2112B1ADC5E8`
- next milestone in the active plan is the retrieval-learning dataset and
  governance split for `IC-0D58F1624037` / `app/services/retrieval_learning.py`

## Audit Bundle And Retrieval Learning Hotspots Milestone 2 Progress

Milestone 2 is the retrieval-learning slice for
`IC-0D58F1624037` / `app/services/retrieval_learning.py`. It reduces the broad
compatibility facade by routing candidate evaluation and reranker-artifact
flows into focused owner modules without changing the public service surface.

Results:

- added `app/services/retrieval_learning_candidates.py` for candidate package
  assembly, threshold resolution, evaluation row creation, and evaluation
  summary or detail response assembly
- added `app/services/retrieval_learning_artifacts.py` for reranker artifact
  request normalization, change-impact reporting, feature weight candidate
  derivation, and artifact summary or detail response assembly
- reduced `app/services/retrieval_learning.py` from 2,482 lines / 46 private
  helpers to 1,470 lines / 25 private helpers while preserving the
  compatibility facade and existing route-test monkeypatch seams
- committed the milestone locally as `a5f090a`
  (`services: complete hotspot milestone 2 retrieval-learning split`)
- added focused owner tests in
  `tests/unit/test_retrieval_learning_candidates.py` and
  `tests/unit/test_retrieval_learning_artifacts.py`
- updated `config/hygiene_policy.yaml`,
  `config/improvement_cases.yaml`,
  `docs/audit_bundle_and_retrieval_learning_hotspots_milestone_plan.md`,
  `docs/agentic_architecture_index.md`,
  `docs/improvement_loop.md`, and this handoff so the current local milestone
  state and next routed follow-up stay explicit

Verification:

- `git diff --check`
- `uv run ruff check app tests`
- `uv run docling-system-architecture-inspect`
- `uv run docling-system-capability-contracts`
- `uv run docling-system-architecture-quality-report --summary`
- `uv run docling-system-hygiene-check`
- `uv run docling-system-improvement-case-summary`
- `uv run docling-system-improvement-case-validate`
- `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 12`
- `uv run pytest -q tests/unit/test_retrieval_learning_candidates.py tests/unit/test_retrieval_learning_artifacts.py tests/unit/test_retrieval_learning_replay_alert_sources.py tests/unit/test_search_api_harnesses.py tests/unit/test_search_api_learning_audit.py`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs tests/integration/test_retrieval_learning_ledger.py`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs`
- `uv run docling-system-evaluation-data-readiness --output storage/evaluation_data_readiness.latest.json`
- `uv run docling-system-agent-trace-review --limit 5 --skip-hygiene`

Verified results:

- `git diff --check`: pass
- `uv run ruff check app tests`: pass
- `uv run docling-system-architecture-inspect`: `valid=true`,
  `violation_count=0`
- `uv run docling-system-capability-contracts`: `valid=true`,
  `facade_count=6`, `function_count=110`
- `uv run docling-system-architecture-quality-report --summary`:
  `hotspot_count=10`, `max_hotspot_risk_score=561.06`
- `uv run docling-system-hygiene-check`: `new hygiene regressions: none`
- `uv run docling-system-improvement-case-summary`: `case_count=26`,
  `status_counts.open=24`, `status_counts.deployed=1`,
  `status_counts.measured=1`, `oldest_open_case_id=IC-050E60059A34`
- `uv run docling-system-improvement-case-validate`: `valid=true`,
  `issue_count=0`
- architecture probe reports `app/services/evidence.py` as the top churn
  hotspot; `app/services/retrieval_learning.py` is no longer listed in the
  top 12 churn hotspots
- `uv run pytest -q tests/unit/test_retrieval_learning_candidates.py tests/unit/test_retrieval_learning_artifacts.py tests/unit/test_retrieval_learning_replay_alert_sources.py tests/unit/test_search_api_harnesses.py tests/unit/test_search_api_learning_audit.py`:
  `19 passed`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs tests/integration/test_retrieval_learning_ledger.py`:
  `10 passed`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs`: `1844 passed`
- `uv run docling-system-evaluation-data-readiness --output storage/evaluation_data_readiness.latest.json`:
  `passed_gate_count=11`, `failed_gate_count=0`
- `uv run docling-system-agent-trace-review --limit 5 --skip-hygiene`:
  `observation_count=0`

Next routed follow-up:

- owner case remains `IC-0D58F1624037`
- next milestone in the active plan is the audit-bundle payload and PROV split
  for `IC-2112B1ADC5E8` / `app/services/audit_bundles.py`

## DB Models Compatibility Facade Milestone 2 Progress

Milestone 2 is the ownership-closeout slice for
`IC-F2A8110185EB` / `app/db/models.py`. It resolves the remaining
`unclear_ownership` issue without changing the public import contract.

Results:

- added `app/db/_model_enums.py` as the private owner for the 29 `StrEnum`
  definitions still living in the public facade
- reduced `app/db/models.py` from 345 lines to 159 while keeping
  `app.db.models` as the only caller-facing public import path
- tightened `tests/unit/test_db_models_facade_contract.py` so any top-level
  class definition in `app/db/models.py` now fails
- extended `tests/unit/test_db_model_import_compatibility.py` so the enum
  re-exports are proven to resolve back to `app/db._model_enums`
- added a repo-private import guard that prevents
  `app/db/_model_enums.py` from becoming a second informal public surface
- updated `config/hygiene_policy.yaml`, `config/improvement_cases.yaml`,
  `docs/data_model_boundary_plan.md`, `docs/agentic_architecture_index.md`,
  `docs/improvement_loop.md`, and this handoff so the closeout artifacts agree
  on the live facade state and next routed owner case

Verification:

- `git diff --check`
- `uv run ruff check app tests`
- `uv run pytest -q tests/unit/test_db_model_import_compatibility.py`
- `uv run pytest -q tests/unit/test_db_models_facade_contract.py`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs tests/integration/test_db_model_metadata.py`
- `uv run --extra dev alembic heads`
- `uv run --extra dev alembic current`
- `uv run --extra dev alembic upgrade head`
- `uv run --extra dev alembic check`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs`
- `uv run docling-system-improvement-case-validate`
- `uv run docling-system-improvement-case-summary`
- `uv run docling-system-architecture-inspect`
- `uv run docling-system-capability-contracts`
- `uv run docling-system-architecture-quality-report --summary`
- `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 12`

Verified results:

- `git diff --check`: pass
- `uv run ruff check app tests`: pass
- `uv run pytest -q tests/unit/test_db_model_import_compatibility.py`:
  `569 passed`
- `uv run pytest -q tests/unit/test_db_models_facade_contract.py`:
  `6 passed`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs tests/integration/test_db_model_metadata.py`:
  `335 passed`
- `uv run --extra dev alembic heads`: `0076_claim_feedback_replay_src (head)`
- `uv run --extra dev alembic current`: `0076_claim_feedback_replay_src (head)`
- `uv run --extra dev alembic upgrade head`: pass
- `uv run --extra dev alembic check`: `No new upgrade operations detected.`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs`:
  `1840 passed in 55.47s`
- `uv run docling-system-improvement-case-validate`: `valid=true`,
  `issue_count=0`
- `uv run docling-system-improvement-case-summary`: `case_count=26`,
  `status_counts.open=24`, `status_counts.deployed=1`,
  `status_counts.measured=1`, `oldest_open_case_id=IC-050E60059A34`
- `uv run docling-system-architecture-inspect`: `valid=true`,
  `violation_count=0`
- `uv run docling-system-capability-contracts`: `valid=true`,
  `facade_count=6`, `function_count=110`
- `uv run docling-system-architecture-quality-report --summary`:
  `hotspot_count=10`, `max_hotspot_risk_score=561.06`
- architecture probe reports `app.db.models` import fan-in=`166`; the facade
  is not listed in the top 12 churn hotspots

Next routed follow-up:

- verified owner case: `IC-F2A8110185EB`
- next oldest open case: `IC-050E60059A34`
- next bounded milestone should target `app/services/evidence.py`

## DB Models Compatibility Facade Milestone 1 Progress

Milestone 1 is the gate-first compatibility-facade slice for
`IC-F2A8110185EB` / `app/db/models.py`. It does not close the owner case; it
creates the explicit contract that Milestone 2 must satisfy.

Results:

- added `tests/unit/test_db_models_facade_contract.py`
- extended `tests/db_model_contract.py` so the governed facade export set now
  includes 111 supported public symbols
- tightened `app/db/models.py` so non-underscore support imports are no longer
  leaked through the facade
- preserved the import-compatible `app.db.models` ORM surface while adding
  public coverage for `DOCUMENT_METADATA_NORMALIZE_SQL` and
  `DOCUMENT_METADATA_TEXTSEARCH_SQL`
- kept `app/db/models.py` at 345 lines while making the facade structure
  machine-checked

Verification:

- `git diff --check`
- `uv run ruff check app tests`
- `uv run pytest -q tests/unit/test_db_models_facade_contract.py`
- `uv run pytest -q tests/unit/test_db_model_import_compatibility.py`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs tests/integration/test_db_model_metadata.py`
- `uv run --extra dev alembic heads`
- `uv run --extra dev alembic current`
- `uv run --extra dev alembic upgrade head`
- `uv run --extra dev alembic check`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs`

Verified results:

- `git diff --check`: pass
- `uv run ruff check app tests`: pass
- `uv run pytest -q tests/unit/test_db_models_facade_contract.py`: `5 passed`
- `uv run pytest -q tests/unit/test_db_model_import_compatibility.py`:
  `568 passed`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs tests/integration/test_db_model_metadata.py`:
  `335 passed`
- `uv run --extra dev alembic heads`: `0076_claim_feedback_replay_src (head)`
- `uv run --extra dev alembic current`: `0076_claim_feedback_replay_src (head)`
- `uv run --extra dev alembic upgrade head`: pass
- `uv run --extra dev alembic check`: `No new upgrade operations detected.`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs`:
  `1838 passed in 52.05s`
- `uv run docling-system-improvement-case-validate`: `valid=true`,
  `issue_count=0`
- `uv run docling-system-improvement-case-summary`: `case_count=26`,
  `status_counts.open=25`, `status_counts.measured=1`
- `uv run docling-system-architecture-inspect`: `valid=true`,
  `violation_count=0`
- `uv run docling-system-capability-contracts`: `valid=true`,
  `facade_count=6`, `function_count=110`
- `uv run docling-system-architecture-quality-report --summary`:
  `hotspot_count=10`, `max_hotspot_risk_score=598.8`
- architecture probe reports `app.db.models` import fan-in=`166`; the facade
  is not listed in the top 12 churn hotspots

Next routed follow-up:

- owner case remains `IC-F2A8110185EB`
- next bounded slice is Milestone 2 facade ownership narrowing from
  `docs/db_models_compatibility_facade_milestone_plan.md`

The completed implementation brief for the new route lives in
`docs/semantic_memory_model_domain_milestone_plan.md`. It scopes `resolved` to
the semantic-memory concern itself
(`SemanticOntologySnapshot`,
`WorkspaceSemanticState`,
`SemanticGraphSnapshot`,
`WorkspaceSemanticGraphState`,
`SemanticConcept`,
`SemanticCategory`,
`SemanticTerm`,
`SemanticConceptTerm`,
`SemanticConceptCategoryBinding`,
`DocumentSemanticConceptReview`,
`DocumentSemanticCategoryReview`,
`DocumentRunSemanticPass`,
`SemanticAssertion`,
`SemanticAssertionCategoryBinding`,
`SemanticAssertionEvidence`,
`SemanticEntity`,
`SemanticFact`,
`SemanticFactEvidence`,
`SemanticGovernanceEvent`) and treats the broader
`IC-F2A8110185EB` owner case as only `reduced` unless the live
architecture-quality report stops flagging `app/db/models.py`. The next
remaining follow-up if model work continues is now a compatibility-facade /
public-import-contract milestone for `app/db/models.py`.

## Semantic Memory Model-Domain Milestone 1 Progress

Milestone 1 is the semantic-memory contract and owner split for
`IC-F2A8110185EB` / `app/db/models.py`. It is a behavior-preserving ORM owner
split behind the existing `app.db.models` compatibility facade.

Results:

- added `app/db/model_domains/semantic_memory.py`
- moved `SemanticOntologySnapshot`,
  `WorkspaceSemanticState`,
  `SemanticGraphSnapshot`,
  `WorkspaceSemanticGraphState`,
  `SemanticConcept`,
  `SemanticCategory`,
  `SemanticTerm`,
  `SemanticConceptTerm`,
  `SemanticConceptCategoryBinding`,
  `DocumentSemanticConceptReview`,
  `DocumentSemanticCategoryReview`,
  `DocumentRunSemanticPass`,
  `SemanticAssertion`,
  `SemanticAssertionCategoryBinding`,
  `SemanticAssertionEvidence`,
  `SemanticEntity`,
  `SemanticFact`,
  `SemanticFactEvidence`, and
  `SemanticGovernanceEvent` out of `app/db/models.py`
- kept `app.db.models` import-compatible by re-exporting the moved classes
  through import-forwarder aliases
- extended `tests/db_model_contract.py`,
  `tests/unit/test_db_model_import_compatibility.py`, and
  `tests/integration/test_db_model_metadata.py` to cover semantic-memory table
  columns, exact index column ordering, and exact unique-constraint column
  ordering
- ratcheted `config/hygiene_policy.yaml` so `app/db/models.py` now has
  `ratchet_max_lines: 345`, and the new owner module
  `app/db/model_domains/semantic_memory.py` is governed under the same owner
  case with `ratchet_max_lines: 979`
- refreshed `docs/semantic_memory_model_domain_milestone_plan.md`,
  `docs/data_model_boundary_plan.md`,
  `docs/agentic_architecture_index.md`,
  `docs/improvement_loop.md`, and this handoff so the routed follow-up now
  points to the next compatibility-facade concern
- reduced `app/db/models.py` from 1,301 lines to 345 and reduced the
  architecture-quality `max_hotspot_risk_score` from `619.67` to `584.8` on
  the current checkout

Verification:

- `git diff --check`
- `uv run ruff check app tests`
- `uv run pytest -q tests/unit/test_db_model_import_compatibility.py`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs tests/integration/test_db_model_metadata.py`
- `uv run --extra dev alembic heads`
- `uv run --extra dev alembic current`
- `uv run --extra dev alembic upgrade head`
- `uv run --extra dev alembic check`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs`
- `uv run docling-system-improvement-case-validate`
- `uv run docling-system-improvement-case-summary`
- `uv run docling-system-architecture-inspect`
- `uv run docling-system-capability-contracts`
- `uv run docling-system-architecture-quality-report --summary`
- `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 12`

Verified results:

- `uv run pytest -q tests/unit/test_db_model_import_compatibility.py`:
  `566 passed`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs tests/integration/test_db_model_metadata.py`:
  `335 passed`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs`:
  `1831 passed in 50.38s`
- `uv run docling-system-improvement-case-validate`: `valid=true`,
  `issue_count=0`
- `uv run docling-system-improvement-case-summary`: `case_count=26`,
  `status_counts.open=25`, `status_counts.measured=1`,
  `oldest_open_case_id=IC-F2A8110185EB`
- `uv run docling-system-architecture-inspect`: `valid=true`,
  `violation_count=0`
- `uv run docling-system-capability-contracts`: `valid=true`,
  `facade_count=6`, `function_count=110`
- `uv run docling-system-architecture-quality-report --summary`:
  `hotspot_count=10`, `max_hotspot_risk_score=584.8`
- architecture probe reports `app/db/models.py` at `345` lines and no longer
  lists it in the top 12 churn hotspots

## Claim Support Model-Domain Milestone 1 Progress

Milestone 1 is the claim-support contract and owner split for
`IC-F2A8110185EB` / `app/db/models.py`. It is a behavior-preserving ORM owner
split behind the existing `app.db.models` compatibility facade.

Results:

- added `app/db/model_domains/claim_support.py`
- moved `ClaimSupportReplayAlertFixtureCoverageWaiverLedger`,
  `ClaimSupportReplayAlertFixtureCoverageWaiverEscalation`,
  `ClaimSupportFixtureSet`,
  `ClaimSupportReplayAlertFixtureCorpusSnapshot`,
  `ClaimSupportReplayAlertFixtureCorpusRow`,
  `ClaimSupportCalibrationPolicy`,
  `ClaimSupportEvaluation`,
  `ClaimSupportEvaluationCase`, and
  `ClaimSupportPolicyChangeImpact` out of `app/db/models.py`
- kept `app.db.models` import-compatible by re-exporting the moved classes
  through import-forwarder aliases
- extended `tests/db_model_contract.py`,
  `tests/unit/test_db_model_import_compatibility.py`, and
  `tests/integration/test_db_model_metadata.py` to cover claim-support table
  columns, exact index column ordering, and exact unique-constraint column
  ordering
- ratcheted `config/hygiene_policy.yaml` so `app/db/models.py` now has
  `ratchet_max_lines: 1301`, and the new owner module
  `app/db/model_domains/claim_support.py` is governed under the same owner
  case with `ratchet_max_lines: 829`
- refreshed `docs/claim_support_model_domain_milestone_plan.md`,
  `docs/data_model_boundary_plan.md`,
  `docs/agentic_architecture_index.md`,
  `docs/improvement_loop.md`, and this handoff so the routed follow-up now
  points to the next remaining model-domain concern
- reduced `app/db/models.py` from 2,089 lines to 1,301 and reduced the
  architecture-quality `max_hotspot_risk_score` from `631.43` to `612.67` on
  the current checkout

Verification:

- `git diff --check`
- `uv run ruff check app tests`
- `uv run pytest -q tests/unit/test_db_model_import_compatibility.py`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs tests/integration/test_db_model_metadata.py`
- `uv run --extra dev alembic heads`
- `uv run --extra dev alembic current`
- `uv run --extra dev alembic upgrade head`
- `uv run --extra dev alembic check`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs`
- `uv run docling-system-improvement-case-validate`
- `uv run docling-system-improvement-case-summary`
- `uv run docling-system-architecture-inspect`
- `uv run docling-system-capability-contracts`
- `uv run docling-system-architecture-quality-report --summary`
- `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 12`

Verified results:

- `uv run pytest -q tests/unit/test_db_model_import_compatibility.py`:
  `486 passed`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs tests/integration/test_db_model_metadata.py`:
  `256 passed`
- `uv run docling-system-improvement-case-validate`: `valid=true`,
  `issue_count=0`
- `uv run docling-system-improvement-case-summary`: `case_count=26`,
  `status_counts.open=25`, `status_counts.measured=1`,
  `oldest_open_case_id=IC-F2A8110185EB`
- `uv run docling-system-architecture-quality-report --summary`:
  `hotspot_count=10`, `max_hotspot_risk_score=612.67`
- architecture probe reports `app/db/models.py` at `1301` lines with hotspot
  score `101478`

## Audit And Evidence Model-Domain Milestone 1 Progress

Milestone 1 is the audit-and-evidence contract and owner split for
`IC-F2A8110185EB` / `app/db/models.py`. It is a behavior-preserving ORM owner
split behind the existing `app.db.models` compatibility facade.

Results:

- added `app/db/model_domains/audit_and_evidence.py`
- moved `AuditBundleExport`,
  `AuditBundleValidationReceipt`,
  `EvidencePackageExport`,
  `EvidenceManifest`,
  `TechnicalReportReleaseReadinessDbGate`,
  `TechnicalReportClaimRetrievalFeedback`,
  `EvidenceTraceNode`,
  `EvidenceTraceEdge`, and
  `ClaimEvidenceDerivation` out of `app/db/models.py`
- kept `app.db.models` import-compatible by re-exporting the moved classes
  through import-forwarder aliases
- extended `tests/db_model_contract.py`,
  `tests/unit/test_db_model_import_compatibility.py`, and
  `tests/integration/test_db_model_metadata.py` to cover audit-and-evidence
  table columns, exact index column ordering, and exact unique-constraint
  column ordering
- ratcheted `config/hygiene_policy.yaml` so `app/db/models.py` now has
  `ratchet_max_lines: 2089`, and the new owner module
  `app/db/model_domains/audit_and_evidence.py` is governed under the same
  owner case with `ratchet_max_lines: 1053`
- refreshed `docs/audit_and_evidence_model_domain_milestone_plan.md`,
  `docs/data_model_boundary_plan.md`,
  `docs/agentic_architecture_index.md`, and this handoff so the routed
  follow-up now points to the next remaining model-domain concern
- reduced `app/db/models.py` from 3,090 lines to 2,089 and reduced the
  architecture-quality `max_hotspot_risk_score` from `649.6` to `631.43` on
  the current checkout

Verification:

- `git diff --check`
- `uv run ruff check app tests`
- `uv run pytest -q tests/unit/test_db_model_import_compatibility.py`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs tests/integration/test_db_model_metadata.py`
- `uv run --extra dev alembic heads`
- `uv run --extra dev alembic current`
- `uv run --extra dev alembic upgrade head`
- `uv run --extra dev alembic check`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs`
- `uv run docling-system-improvement-case-validate`
- `uv run docling-system-improvement-case-summary`
- `uv run docling-system-architecture-inspect`
- `uv run docling-system-capability-contracts`
- `uv run docling-system-architecture-quality-report --summary`
- `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 12`

Verified results:

- `uv run pytest -q tests/unit/test_db_model_import_compatibility.py`:
  `444 passed`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs tests/integration/test_db_model_metadata.py`:
  `215 passed`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs`:
  `1589 passed in 53.56s`
- `uv run docling-system-architecture-quality-report --summary`:
  `hotspot_count=10`, `max_hotspot_risk_score=631.43`
- architecture probe reports `app/db/models.py` at `2089` lines with hotspot
  score `162942`

## Agent Task Model-Domain Milestone 1 Progress

Milestone 1 is the agent-task contract and owner split for
`IC-F2A8110185EB` / `app/db/models.py`. It is a behavior-preserving ORM owner
split behind the existing `app.db.models` compatibility facade.

Results:

- added `app/db/model_domains/agent_tasks.py`
- moved `AgentTask`,
  `AgentTaskDependency`,
  `AgentTaskAttempt`,
  `AgentTaskArtifact`,
  `AgentTaskArtifactImmutabilityEvent`,
  `AgentTaskOutcome`,
  `AgentTaskVerification`,
  `KnowledgeOperatorRun`,
  `KnowledgeOperatorInput`, and
  `KnowledgeOperatorOutput` out of `app/db/models.py`
- kept `app.db.models` import-compatible by re-exporting the moved classes
  through import-forwarder aliases
- extended `tests/db_model_contract.py`,
  `tests/unit/test_db_model_import_compatibility.py`, and
  `tests/integration/test_db_model_metadata.py` to cover agent-task table
  columns, exact index column ordering, and exact unique-constraint column
  ordering
- ratcheted `config/hygiene_policy.yaml` so `app/db/models.py` now has
  `ratchet_max_lines: 3090`, and the new owner module
  `app/db/model_domains/agent_tasks.py` is governed under the same owner case
- refreshed `docs/agent_task_model_domain_milestone_plan.md`,
  `docs/data_model_boundary_plan.md`,
  `docs/agentic_architecture_index.md`, and this handoff so the routed
  follow-up now points to the next remaining model-domain concern
- reduced `app/db/models.py` from 3,570 lines to 3,090 and reduced the
  architecture-quality `max_hotspot_risk_score` from `660.8` to `649.6`

Verification:

- `git diff --check`
- `uv run ruff check app tests`
- `uv run pytest -q tests/unit/test_db_model_import_compatibility.py`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs tests/integration/test_db_model_metadata.py`
- `uv run --extra dev alembic heads`
- `uv run --extra dev alembic current`
- `uv run --extra dev alembic upgrade head`
- `uv run --extra dev alembic check`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs`
- `uv run docling-system-improvement-case-validate`
- `uv run docling-system-improvement-case-summary`
- `uv run docling-system-architecture-inspect`
- `uv run docling-system-capability-contracts`
- `uv run docling-system-architecture-quality-report --summary`
- `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 12`

Verified results:

- `uv run pytest -q tests/unit/test_db_model_import_compatibility.py`:
  `406 passed`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs tests/integration/test_db_model_metadata.py`:
  `178 passed`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs`:
  `1514 passed in 50.23s`
- `uv run --extra dev alembic heads`: single head
  `0076_claim_feedback_replay_src`
- `uv run --extra dev alembic current`: `0076_claim_feedback_replay_src`
- `uv run --extra dev alembic check`: `No new upgrade operations detected.`
- `uv run docling-system-improvement-case-summary`: `case_count=26`,
  `status_counts.open=25`, `status_counts.measured=1`,
  `oldest_open_case_id=IC-F2A8110185EB`
- `uv run docling-system-architecture-quality-report --summary`:
  `hotspot_count=10`, `max_hotspot_risk_score=649.6`
- architecture probe reports `app/db/models.py` at `3090` lines with hotspot
  score `237930`

## Evaluation Feedback Model-Domain Milestone 1 Progress

Milestone 1 is the evaluation-feedback contract and owner split for
`IC-F2A8110185EB` / `app/db/models.py`. It is a behavior-preserving ORM owner
split behind the existing `app.db.models` compatibility facade, committed
locally as `b69c4f6`.

Results:

- added `app/db/model_domains/evaluation_feedback.py`
- moved `EvalObservation` and `EvalFailureCase` out of `app/db/models.py`
- kept `app.db.models` import-compatible by re-exporting the moved classes
  through import-forwarder aliases
- extended `tests/db_model_contract.py`,
  `tests/unit/test_db_model_import_compatibility.py`, and
  `tests/integration/test_db_model_metadata.py` to cover evaluation-feedback
  table columns, exact index column ordering, and exact unique-constraint
  column ordering
- ratcheted `config/hygiene_policy.yaml` so `app/db/models.py` now has
  `ratchet_max_lines: 3570`, and the new owner module
  `app/db/model_domains/evaluation_feedback.py` is governed under the same
  owner case
- refreshed `config/improvement_cases.yaml`,
  `docs/evaluation_feedback_model_domain_milestone_plan.md`,
  `docs/data_model_boundary_plan.md`,
  `docs/agentic_architecture_index.md`, and this handoff so the routed
  follow-up now points to the next remaining model-domain concern
- reduced `app/db/models.py` from 3,782 lines to 3,570 and reduced the
  architecture-quality `max_hotspot_risk_score` from `658.21` to `653.8`

Verification:

- `git diff --check`
- `uv run ruff check app tests`
- `uv run pytest -q tests/unit/test_db_model_import_compatibility.py`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs tests/integration/test_db_model_metadata.py`
- `uv run --extra dev alembic heads`
- `uv run --extra dev alembic current`
- `uv run --extra dev alembic upgrade head`
- `uv run --extra dev alembic check`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs`
- `uv run docling-system-improvement-case-validate`
- `uv run docling-system-improvement-case-summary`
- `uv run docling-system-architecture-inspect`
- `uv run docling-system-capability-contracts`
- `uv run docling-system-architecture-quality-report --summary`
- `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 12`

Verified results:

- `uv run pytest -q tests/unit/test_db_model_import_compatibility.py`:
  `369 passed`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs tests/integration/test_db_model_metadata.py`:
  `142 passed`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs`:
  `1441 passed in 51.95s`
- `uv run --extra dev alembic heads`: single head
  `0076_claim_feedback_replay_src`
- `uv run --extra dev alembic current`: `0076_claim_feedback_replay_src`
- `uv run --extra dev alembic check`: `No new upgrade operations detected.`
- `uv run docling-system-improvement-case-validate`: `valid=true`,
  `issue_count=0`
- `uv run docling-system-improvement-case-summary`: `case_count=26`,
  `status_counts.open=25`, `status_counts.measured=1`,
  `oldest_open_case_id=IC-F2A8110185EB`
- `uv run docling-system-architecture-inspect`: `valid=true`,
  `violation_count=0`
- `uv run docling-system-capability-contracts`: `valid=true`,
  `facade_count=6`, `function_count=110`
- `uv run docling-system-architecture-quality-report --summary`:
  `hotspot_count=10`, `max_hotspot_risk_score=653.8`
- architecture probe now reports `app/services/evidence.py` as the top churn
  hotspot and `app/db/models.py` at `3570` lines with hotspot score `267750`

## Evaluation Feedback Model-Domain Milestone 0 Progress

Milestone 0 is the preflight baseline-lock slice for the
`IC-F2A8110185EB` / `app/db/models.py` evaluation-feedback follow-up. It is a
governance-and-verification checkpoint, not an ORM move.

Results:

- confirmed that `docs/evaluation_feedback_model_domain_milestone_plan.md`,
  `docs/data_model_boundary_plan.md`, `docs/agentic_architecture_index.md`,
  and this handoff all route the next model-domain candidate to
  `EvalObservation` and `EvalFailureCase`
- refreshed the live architecture-quality baseline at
  `max_hotspot_risk_score=658.21` with `app/db/models.py` still first in
  `top_hotspot_paths`
- confirmed that `config/improvement_cases.yaml` still reports
  `IC-F2A8110185EB` as the oldest open owner case with `app/db/models.py` at
  3,782 lines
- confirmed the DB-backed preflight posture required before code movement:
  Alembic is at a single head with no drift, and the focused import plus
  Postgres metadata gates are green
- closed Milestone 0 without moving `EvalObservation` or `EvalFailureCase`;
  the missing dedicated evaluation-feedback metadata contract coverage remains
  the first implementation step of Milestone 1

Verification:

- `git diff --check`
- `uv run docling-system-improvement-case-validate`
- `uv run docling-system-improvement-case-summary`
- `uv run docling-system-architecture-quality-report --summary`
- `uv run --extra dev alembic heads`
- `uv run --extra dev alembic current`
- `uv run --extra dev alembic check`
- `uv run pytest -q tests/unit/test_db_model_import_compatibility.py`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs tests/integration/test_db_model_metadata.py`

Verified results:

- `uv run docling-system-improvement-case-validate`: `valid=true`,
  `issue_count=0`
- `uv run docling-system-improvement-case-summary`: `case_count=26`,
  `status_counts.open=25`, `status_counts.measured=1`,
  `oldest_open_case_id=IC-F2A8110185EB`
- `uv run docling-system-architecture-quality-report --summary`:
  `hotspot_count=10`, `max_hotspot_risk_score=658.21`
- `uv run --extra dev alembic heads`: single head
  `0076_claim_feedback_replay_src`
- `uv run --extra dev alembic current`: `0076_claim_feedback_replay_src`
- `uv run --extra dev alembic check`: `No new upgrade operations detected.`
- `uv run pytest -q tests/unit/test_db_model_import_compatibility.py`:
  `358 passed`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs tests/integration/test_db_model_metadata.py`:
  `132 passed`

## High Value Technical Paydown Milestone 10 Closeout

Milestone 10 closes the High Value Technical Paydown plan against live
post-Milestone 9 artifacts and routes the next owner-scoped follow-up.

Results:

- recorded the Milestone 9 deployment ref `faed562` and the reduced
  `app/db/models.py` line-count measurement in `config/improvement_cases.yaml`
- completed the stale closeout checklist in
  `docs/high_value_technical_paydown_milestone_plan.md`
- refreshed `README.md` and `SYSTEM_PLAN.md` so the repo's top-level
  current-state snapshot matches the Milestone 10 closeout route and live
  architecture metrics
- refreshed `docs/improvement_loop.md`,
  `docs/agentic_architecture_index.md`,
  `docs/architecture_plan_01.md`, and this handoff so the committed
  retrieval-learning split and the plan closeout route agree
- closed the plan locally through Milestone 10 instead of leaving Milestone 8
  and 9 out of the milestone sequence
- routed the next follow-up by the current architecture-quality report:
  `IC-F2A8110185EB` / `app/db/models.py` remains the top governed hotspot, and
  `docs/data_model_boundary_plan.md` now names `evaluation feedback`
  (`EvalObservation`, `EvalFailureCase`) as the next bounded model-domain
  candidate when model work resumes

## High Value Technical Paydown Milestone 9 Progress

Milestone 9 is the retrieval-learning model-domain split for
`IC-F2A8110185EB` / `app/db/models.py`. It is a behavior-preserving ORM owner
split behind the existing `app.db.models` compatibility facade.

Results:

- added `app/db/model_domains/retrieval_learning_examples.py`
- added `app/db/model_domains/retrieval_learning_artifacts.py`
- moved `RetrievalJudgmentSet`, `RetrievalJudgment`,
  `RetrievalHardNegative`, `RetrievalTrainingRun`,
  `RetrievalLearningCandidateEvaluation`, and
  `RetrievalRerankerArtifact` out of `app/db/models.py`
- kept `app.db.models` import-compatible by re-exporting the moved classes
  through import-forwarder aliases that satisfy the hotspot-prevention gate
- added explicit ORM relationships on retrieval-learning artifact rows so
  existing integration fixtures flush `RetrievalJudgmentSet` before dependent
  training rows without changing schema shape
- extended `tests/db_model_contract.py`,
  `tests/unit/test_db_model_import_compatibility.py`, and
  `tests/integration/test_db_model_metadata.py` to cover retrieval learning
  and replay/release governance table columns, exact index column ordering,
  and exact unique-constraint column ordering
- ratcheted `config/hygiene_policy.yaml` so `app/db/models.py` now has
  `ratchet_max_lines: 3782`, and the new owner modules
  `app/db/model_domains/retrieval_learning_examples.py` and
  `app/db/model_domains/retrieval_learning_artifacts.py` are governed under
  the same owner case
- updated `docs/high_value_technical_paydown_milestone_plan.md`,
  `docs/data_model_boundary_plan.md`, and this handoff so the routed follow-up
  now points to final plan closeout
- reduced `app/db/models.py` from 4,525 lines to 3,782 and reduced the
  architecture-quality `max_hotspot_risk_score` from `668.17` to `656.21`

Verification:

- `git diff --check`
- `uv run ruff check app tests`
- `uv run pytest -q tests/unit/test_db_model_import_compatibility.py`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs tests/integration/test_db_model_metadata.py`
- `uv run --extra dev alembic heads`
- `uv run --extra dev alembic current`
- `uv run --extra dev alembic upgrade head`
- `uv run --extra dev alembic check`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs`
- `uv run docling-system-evaluation-data-readiness --output storage/evaluation_data_readiness.latest.json`
- `uv run docling-system-agent-trace-review --limit 5 --skip-hygiene`
- `uv run docling-system-improvement-case-validate`
- `uv run docling-system-improvement-case-summary`
- `uv run docling-system-architecture-inspect`
- `uv run docling-system-capability-contracts`
- `uv run docling-system-architecture-quality-report --summary`
- `uv run docling-system-hotspot-prevention-check --strict`
- `uv run docling-system-hygiene-check`
- `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 12`

Verified results:

- `uv run pytest -q tests/unit/test_db_model_import_compatibility.py`:
  `358 passed`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs tests/integration/test_db_model_metadata.py`:
  `132 passed`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs`: `1420 passed in 48.03s`
- `uv run --extra dev alembic heads`: single head
  `0076_claim_feedback_replay_src`
- `uv run --extra dev alembic current`: `0076_claim_feedback_replay_src`
- `uv run --extra dev alembic check`: `No new upgrade operations detected.`
- `uv run docling-system-evaluation-data-readiness --output storage/evaluation_data_readiness.latest.json`:
  `regression_ready=true`, `court_grade_ready=true`, `failed_gate_count=0`
- `uv run docling-system-agent-trace-review --limit 5 --skip-hygiene`:
  `observation_count=0`
- `uv run docling-system-architecture-inspect`: `valid=true`,
  `violation_count=0`
- `uv run docling-system-capability-contracts`: `valid=true`,
  `facade_count=6`, `function_count=110`
- `uv run docling-system-architecture-quality-report --summary`:
  `hotspot_count=10`, `max_hotspot_risk_score=656.21`
- `uv run docling-system-hotspot-prevention-check --strict`: `blocked=0`
- `uv run docling-system-hygiene-check`: `new hygiene regressions: none`
- architecture probe now reports `app/services/evidence.py` as the top churn
  hotspot, while `app/db/models.py` remains the top governed hotspot at
  `3782` lines and score `279868`

## High Value Technical Paydown Milestone 8 Progress

Milestone 8 is the retrieval replay and release governance model-domain split
for `IC-F2A8110185EB` / `app/db/models.py`. It is a behavior-preserving ORM
owner split behind the existing `app.db.models` compatibility facade.

Closeout commit:

- `47a86d1` (`architecture: split replay release governance models`)

Results:

- added `app/db/model_domains/retrieval_replay_governance.py`
- moved `SearchReplayRun`, `SearchReplayQuery`, `SearchHarnessEvaluation`,
  `SearchHarnessEvaluationSource`, `SearchHarnessRelease`, and
  `SearchHarnessReleaseReadinessAssessment` out of `app/db/models.py`
- kept `app.db.models` import-compatible by re-exporting the moved classes
  through import-forwarder aliases that satisfy the hotspot-prevention gate
- extended `tests/db_model_contract.py`,
  `tests/unit/test_db_model_import_compatibility.py`, and
  `tests/integration/test_db_model_metadata.py` to cover replay/release
  governance table columns, exact index column ordering, and exact
  unique-constraint column ordering
- ratcheted `config/hygiene_policy.yaml` so `app/db/models.py` now has
  `ratchet_max_lines: 4525`, and the new owner module
  `app/db/model_domains/retrieval_replay_governance.py` is governed under the
  same owner case
- updated `config/improvement_cases.yaml`,
  `docs/high_value_technical_paydown_milestone_plan.md`,
  `docs/data_model_boundary_plan.md`, `docs/architecture_plan_01.md`,
  `docs/agentic_architecture_index.md`, `docs/improvement_loop.md`, and this
  handoff so the routed follow-up now points to retrieval learning
- reduced `app/db/models.py` from 5,067 lines to 4,525 and reduced the
  architecture-quality `max_hotspot_risk_score` from `673.78` to `668.17`

Verification:

- `git diff --check`
- `uv run ruff check app tests`
- `uv run pytest -q tests/unit/test_db_model_import_compatibility.py`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs tests/integration/test_db_model_metadata.py`
- `uv run --extra dev alembic heads`
- `uv run --extra dev alembic current`
- `uv run --extra dev alembic upgrade head`
- `uv run --extra dev alembic check`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs`
- `uv run docling-system-evaluation-data-readiness --output storage/evaluation_data_readiness.latest.json`
- `uv run docling-system-agent-trace-review --limit 5 --skip-hygiene`
- `uv run docling-system-improvement-case-validate`
- `uv run docling-system-improvement-case-summary`
- `uv run docling-system-architecture-inspect`
- `uv run docling-system-capability-contracts`
- `uv run docling-system-architecture-quality-report --summary`
- `uv run docling-system-hotspot-prevention-check --strict`
- `uv run docling-system-hygiene-check`
- `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 12`

Verified results:

- `uv run pytest -q tests/unit/test_db_model_import_compatibility.py`:
  `314 passed`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs tests/integration/test_db_model_metadata.py`:
  `84 passed`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs`: `1328 passed in 52.06s`
- `uv run --extra dev alembic heads`: single head
  `0076_claim_feedback_replay_src`
- `uv run --extra dev alembic current`: `0076_claim_feedback_replay_src`
- `uv run --extra dev alembic check`: `No new upgrade operations detected.`
- `uv run docling-system-evaluation-data-readiness --output storage/evaluation_data_readiness.latest.json`:
  `regression_ready=true`, `court_grade_ready=true`, `failed_gate_count=0`
- `uv run docling-system-agent-trace-review --limit 5 --skip-hygiene`:
  `observation_count=0`
- `uv run docling-system-architecture-inspect`: `valid=true`,
  `violation_count=0`
- `uv run docling-system-capability-contracts`: `valid=true`,
  `facade_count=6`, `function_count=110`
- `uv run docling-system-architecture-quality-report --summary`:
  `hotspot_count=10`, `max_hotspot_risk_score=668.17`
- `uv run docling-system-hotspot-prevention-check --strict`: `blocked=0`
- `uv run docling-system-hygiene-check`: `new hygiene regressions: none`
- architecture probe still reports `app/db/models.py` as the top hotspot, but
  now at `4525` lines and score `330325`

## High Value Technical Paydown Milestone 7 Progress

Milestone 7 is the closeout and reroute pass for the High Value Technical
Paydown plan. It proves the completed Milestones 1-6 still align with live
repo metrics and records the next highest-value residual debt explicitly.

Results:

- refreshed `docs/high_value_technical_paydown_milestone_plan.md`,
  `docs/improvement_loop.md`, `docs/agentic_architecture_index.md`,
  `docs/data_model_boundary_plan.md`, and this handoff against live closeout
  verification outputs
- updated `config/improvement_cases.yaml` so completed Milestone 5 and 6 cases
  `IC-40CA7C1FFA84`, `IC-934588120F94`, and `IC-1B643BA0AD90` now carry
  deployment refs and measurement payloads
- reran the full DB-backed suite and refreshed the readiness and trace-review
  artifacts instead of carrying the pre-closeout Milestone 6 metrics forward
- closed the routing gap by returning the next implementation slice to the top
  remaining owner case `IC-F2A8110185EB` / `app/db/models.py`, starting with
  the retrieval replay and release governance model-domain candidate

Verification:

- `git diff --check`
- `uv run ruff check app tests`
- `uv run docling-system-improvement-case-validate`
- `uv run docling-system-improvement-case-summary`
- `uv run docling-system-architecture-inspect`
- `uv run docling-system-capability-contracts`
- `uv run docling-system-architecture-quality-report --summary`
- `uv run docling-system-hotspot-prevention-check --strict`
- `uv run docling-system-hygiene-check`
- `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 12`
- `uv run docling-system-evaluation-data-readiness --output storage/evaluation_data_readiness.latest.json`
- `uv run docling-system-agent-trace-review --limit 5 --skip-hygiene`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs`
- `python /Users/chunkstand/.codex/skills/milestone-plan-writer/scripts/lint_milestone_plan.py --strict docs/high_value_technical_paydown_milestone_plan.md`

Verified results:

- full DB-backed suite: `1321 passed in 52.08s`
- evaluation-data readiness: `regression_ready=true`,
  `court_grade_ready=true`, `passed_gate_count=11`, `failed_gate_count=0`
- agent-trace review: `observation_count=0`
- architecture quality summary: `agent_legibility_average_score=90.0`,
  `broad_facade_count=2`, `hotspot_count=10`,
  `max_hotspot_risk_score=680.78`

- `config/hotspot_prevention.yaml`
- `config/hygiene_policy.yaml`
- `config/improvement_cases.yaml`
- `app/cli_commands/common.py`
- `app/cli_commands/ingest.py`
- `app/db/model_domains/document_artifacts.py`
- `app/db/model_domains/ingest.py`
- `app/db/model_domains/retrieval_interactions.py`
- `app/hotspot_prevention.py`
- `app/hotspot_prevention_policy.py`
- `app/hotspot_prevention_diff.py`
- `app/hotspot_prevention_classifier.py`
- `app/hygiene.py`
- `app/hygiene_ruff.py`
- `app/hygiene_types.py`
- `app/services/improvement_case_intake.py`
- `app/services/agent_task_action_lookup.py`
- `app/services/agent_actions/report_actions.py`
- `app/services/audit_bundle_replay_alert_corpus.py`
- `app/services/evidence_manifest_traces.py`
- `app/services/evidence_operator_runs.py`
- `app/services/evidence_technical_report_exports.py`
- `app/services/evidence_task_payloads.py`
- `app/ui/modules/shared.js`
- `app/ui/modules/landing.js`
- `app/ui/modules/documents.js`
- `app/ui/modules/search.js`
- `app/ui/modules/evals.js`
- `app/ui/modules/semantics.js`
- `app/ui/modules/agents.js`
- `app/services/claim_support_replay_alert_promotions.py`
- `app/services/retrieval_learning_replay_alert_sources.py`
- `app/services/search_ranking.py`
- `tests/unit/test_agent_task_action_lookup.py`
- `tests/unit/test_agent_task_actions.py`
- `tests/unit/test_hotspot_prevention.py`
- `tests/unit/test_hygiene.py`
- `tests/unit/test_improvement_case_intake.py`
- `tests/unit/test_cli_ingest.py`
- `tests/unit/test_cli.py`
- `tests/unit/test_cli_agent_tasks.py`
- `tests/unit/test_cli_agent_task_analytics.py`
- `tests/unit/test_cli_claim_support.py`
- `tests/unit/test_cli_improvement_cases.py`
- `tests/unit/test_evidence_operator_runs.py`
- `tests/unit/test_evidence_technical_report_exports.py`
- `tests/unit/test_evidence_task_payloads.py`
- `tests/unit/test_retrieval_learning_replay_alert_sources.py`
- `tests/unit/test_search_api.py`
- `tests/unit/test_search_api_replays.py`
- `tests/unit/test_search_api_harnesses.py`
- `tests/unit/test_search_api_learning_audit.py`
- `tests/unit/test_search_ranking.py`
- `tests/unit/test_db_model_import_compatibility.py`
- `tests/unit/test_ui.py`
- `tests/unit/test_ui_static_assets.py`
- `tests/unit/test_documents_api.py`
- `tests/unit/test_documents_api_artifacts.py`
- `tests/unit/test_documents_api_semantics.py`
- `tests/integration/test_db_model_metadata.py`
- `tests/db_model_contract.py`
- `docs/hotspot_prevention_gate_milestone_plan.md`
- `docs/residual_weakness_resolution_milestone_plan.md`
- `docs/high_value_technical_paydown_milestone_plan.md`
- `docs/data_model_boundary_plan.md`
- `docs/improvement_loop.md`
- `docs/architecture_boundaries.md`
- `docs/architecture_plan_01.md`
- `docs/agentic_architecture_index.md`
- `docs/hotspot_owner_resolution_plan.md`
- `docs/SESSION_HANDOFF.md`
- `README.md`
- `SYSTEM_PLAN.md`

## High Value Technical Paydown Milestone 6 Progress

Milestone 6 is the UI monolith split for `IC-1B643BA0AD90`. It is a
behavior-preserving decomposition of the shipped operator UI from one
JavaScript implementation surface into shared runtime and page-family owner
modules.

Results:

- reduced `app/ui/app.js` from `4335` to `107` lines and kept it as the shipped
  bootstrap/composition surface
- moved the shared runtime and page-family logic into
  `app/ui/modules/shared.js`,
  `app/ui/modules/landing.js`,
  `app/ui/modules/documents.js`,
  `app/ui/modules/search.js`,
  `app/ui/modules/evals.js`,
  `app/ui/modules/semantics.js`, and
  `app/ui/modules/agents.js`
- kept the shipped HTML entrypoints stable while loading the new module family
  before `/ui/app.js`
- added focused UI smoke coverage in `tests/unit/test_ui_static_assets.py` so
  module asset inclusion and static asset serving are validated alongside the
  existing UI page-content checks in `tests/unit/test_ui.py`
- updated `config/improvement_cases.yaml`,
  `docs/high_value_technical_paydown_milestone_plan.md`,
  `docs/improvement_loop.md`,
  `docs/agentic_architecture_index.md`, and this handoff to record the
  narrowed UI owner surface and reroute the next milestone

Verification:

- `find app/ui -name '*.js' -print0 | xargs -0 -n1 node --check`
- `uv run pytest -q tests/unit/test_ui.py tests/unit/test_ui_static_assets.py`
- `git diff --check`
- `uv run ruff check app tests`
- `uv run docling-system-improvement-case-validate`
- `uv run docling-system-improvement-case-summary`
- `uv run docling-system-architecture-inspect`
- `uv run docling-system-capability-contracts`
- `uv run docling-system-architecture-quality-report --summary`
- `uv run docling-system-hotspot-prevention-check --strict`
- `uv run docling-system-hygiene-check`
- `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 12`

Verified results:

- UI smoke pack: `10 passed in 3.74s`
- `uv run docling-system-improvement-case-summary`: `case_count=26`,
  `status_counts.open=25`, `status_counts.measured=1`,
  `measured_case_count=13`
- `uv run docling-system-architecture-quality-report --summary`:
  `agent_legibility_average_score=90.0`, `broad_facade_count=2`,
  `hotspot_count=10`, `max_hotspot_risk_score=680.78`; the top hotspot paths
  remain the large Python service surfaces and no longer include the former UI
  monolith
- `uv run docling-system-hygiene-check`: `new hygiene regressions: none`

## High Value Technical Paydown Milestone 5 Progress

Milestone 5 is the test hotspot split pack B for `IC-934588120F94` and
`IC-40CA7C1FFA84`. It is a behavior-preserving split of the agent-task action
and claim-support judge roundtrip test monoliths into focused owner files.

Results:

- kept `tests/unit/test_agent_task_actions.py` as the compatibility and
  registry-metadata surface and moved search-harness, semantic registry,
  ontology, semantic graph, and semantic document coverage into
  `tests/unit/test_agent_task_actions_search_harness.py`,
  `tests/unit/test_agent_task_actions_semantic_registry.py`,
  `tests/unit/test_agent_task_actions_ontology.py`,
  `tests/unit/test_agent_task_actions_semantic_graph.py`, and
  `tests/unit/test_agent_task_actions_semantic_documents.py`
- kept `tests/integration/test_claim_support_judge_evaluation_roundtrip.py` as
  the core evaluation surface and moved activation and waiver coverage into
  `tests/integration/test_claim_support_policy_activation_roundtrip.py`,
  core terminal-closure coverage into
  `tests/integration/test_claim_support_policy_change_impacts_roundtrip.py`,
  and mined-failure governance coverage into
  `tests/integration/test_claim_support_policy_mined_failures_roundtrip.py`
- added shared non-test support surfaces
  `tests/unit/agent_task_actions_support.py` and
  `tests/integration/claim_support_judge_evaluation_roundtrip_support.py` so
  the split files reuse helper payloads and DB-backed support routines instead
  of duplicating them
- closed the residual Milestone 5 alignment gap by splitting the
  2,297-line replay-alert change-impact surface into
  `tests/integration/test_claim_support_policy_activation_change_impacts_roundtrip.py`,
  `tests/integration/test_claim_support_policy_change_impacts_replay_alert_prevalidation.py`,
  `tests/integration/test_claim_support_policy_change_impacts_replay_alert_promotions.py`,
  `tests/integration/test_claim_support_policy_change_impacts_replay_alert_governance.py`,
  and `tests/integration/claim_support_policy_change_impacts_replay_alert_support.py`,
  reducing `tests/integration/test_claim_support_policy_change_impacts_roundtrip.py`
  to 354 lines
- reduced `tests/unit/test_agent_task_actions.py` from `4161` to `417` lines
  and `tests/integration/test_claim_support_judge_evaluation_roundtrip.py`
  from `4368` to `337` lines
- updated `config/improvement_cases.yaml`,
  `docs/high_value_technical_paydown_milestone_plan.md`,
  `docs/improvement_loop.md`, `docs/agentic_architecture_index.md`, and this
  handoff to record the narrowed owner surfaces and reroute the next milestone

Verification:

- `uv run ruff check tests/unit/test_agent_task_actions.py tests/unit/agent_task_actions_support.py tests/unit/test_agent_task_actions_search_harness.py tests/unit/test_agent_task_actions_semantic_registry.py tests/unit/test_agent_task_actions_ontology.py tests/unit/test_agent_task_actions_semantic_graph.py tests/unit/test_agent_task_actions_semantic_documents.py tests/integration/claim_support_judge_evaluation_roundtrip_support.py tests/integration/claim_support_policy_change_impacts_replay_alert_support.py tests/integration/test_claim_support_judge_evaluation_roundtrip.py tests/integration/test_claim_support_policy_activation_roundtrip.py tests/integration/test_claim_support_policy_activation_change_impacts_roundtrip.py tests/integration/test_claim_support_policy_change_impacts_roundtrip.py tests/integration/test_claim_support_policy_change_impacts_replay_alert_prevalidation.py tests/integration/test_claim_support_policy_change_impacts_replay_alert_promotions.py tests/integration/test_claim_support_policy_change_impacts_replay_alert_governance.py tests/integration/test_claim_support_policy_mined_failures_roundtrip.py`
- `uv run pytest -q tests/unit/test_agent_task_actions.py tests/unit/test_agent_task_actions_search_harness.py tests/unit/test_agent_task_actions_semantic_registry.py tests/unit/test_agent_task_actions_ontology.py tests/unit/test_agent_task_actions_semantic_graph.py tests/unit/test_agent_task_actions_semantic_documents.py`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q tests/integration/test_claim_support_policy_activation_change_impacts_roundtrip.py tests/integration/test_claim_support_policy_change_impacts_roundtrip.py tests/integration/test_claim_support_policy_change_impacts_replay_alert_prevalidation.py tests/integration/test_claim_support_policy_change_impacts_replay_alert_promotions.py tests/integration/test_claim_support_policy_change_impacts_replay_alert_governance.py tests/integration/test_claim_support_policy_activation_roundtrip.py tests/integration/test_claim_support_policy_mined_failures_roundtrip.py`
- `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 20`
- `git diff --check`
- `uv run docling-system-improvement-case-validate`
- `uv run docling-system-improvement-case-summary`
- `uv run docling-system-architecture-inspect`
- `uv run docling-system-capability-contracts`
- `uv run docling-system-architecture-quality-report --summary`
- `uv run docling-system-hotspot-prevention-check --strict`
- `uv run docling-system-hygiene-check`
- `uv run docling-system-evaluation-data-readiness --output storage/evaluation_data_readiness.latest.json`
- `uv run docling-system-agent-trace-review --limit 5 --skip-hygiene`
- `python /Users/chunkstand/.codex/skills/milestone-plan-writer/scripts/lint_milestone_plan.py --strict docs/high_value_technical_paydown_milestone_plan.md`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs`

Verified results:

- focused unit split pack: `52 passed in 0.93s`
- focused DB-backed claim-support split pack: `15 passed in 4.59s`
- architecture probe: the original hotspot files
  `tests/unit/test_agent_task_actions.py` and
  `tests/integration/test_claim_support_judge_evaluation_roundtrip.py` no
  longer appear in the current top 20 hotspot list, and the residual
  replay-alert split files no longer appear in the current top 20 largest
  files or hotspot list
- full integration-backed suite: `1319 passed in 49.94s`
- `uv run docling-system-improvement-case-summary`: `case_count=26`,
  `status_counts.open=25`, `status_counts.measured=1`,
  `measured_case_count=13`
- `uv run docling-system-architecture-quality-report --summary`:
  `agent_legibility_average_score=90.0`, `broad_facade_count=2`,
  `hotspot_count=10`, `max_hotspot_risk_score=673.78`, and the top hotspot
  paths still route through the core service surfaces rather than the split
  Milestone 5 tests
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs`:
  `1317 passed in 51.44s`

## High Value Technical Paydown Milestone 4 Progress

Milestone 4 is the test hotspot split pack A for `IC-FD18EE2D3309`,
`IC-03D7EFA03213`, and `IC-23F2C79C8AA7`. It is a behavior-preserving split of
the CLI, search API, and document API test monoliths into focused owner files.

Results:

- kept `tests/unit/test_cli.py` as the core `app.cli` compatibility surface and
  moved agent-task, claim-support replay, and improvement-case coverage into
  `tests/unit/test_cli_agent_tasks.py`,
  `tests/unit/test_cli_agent_task_analytics.py`,
  `tests/unit/test_cli_claim_support.py`, and
  `tests/unit/test_cli_improvement_cases.py`, then moved the remaining
  search-harness CLI coverage into `tests/unit/test_cli_search_harness.py`
- kept `tests/unit/test_search_api.py` as the core search-route surface and
  moved replay, harness/release, and learning/audit coverage into
  `tests/unit/test_search_api_replays.py`,
  `tests/unit/test_search_api_harnesses.py`, and
  `tests/unit/test_search_api_learning_audit.py`
- kept `tests/unit/test_documents_api.py` as the core document-route surface
  and moved artifact and semantics coverage into
  `tests/unit/test_documents_api_artifacts.py` and
  `tests/unit/test_documents_api_semantics.py`
- reduced `tests/unit/test_cli.py` from `2210` to `424` lines,
  `tests/unit/test_search_api.py` from `1660` to `436` lines, and
  `tests/unit/test_documents_api.py` from `1273` to `613` lines
- updated `config/improvement_cases.yaml`,
  `docs/high_value_technical_paydown_milestone_plan.md`,
  `docs/improvement_loop.md`, `docs/agentic_architecture_index.md`, and this
  handoff to record the narrowed owner surfaces and reroute the next milestone

Verification:

- `git diff --check`
- `uv run ruff check tests/unit/test_cli.py tests/unit/test_cli_agent_tasks.py tests/unit/test_cli_agent_task_analytics.py tests/unit/test_cli_claim_support.py tests/unit/test_cli_improvement_cases.py tests/unit/test_cli_search_harness.py tests/unit/test_search_api.py tests/unit/test_search_api_replays.py tests/unit/test_search_api_harnesses.py tests/unit/test_search_api_learning_audit.py tests/unit/test_documents_api.py tests/unit/test_documents_api_artifacts.py tests/unit/test_documents_api_semantics.py`
- `uv run pytest -q tests/unit/test_cli.py tests/unit/test_cli_agent_tasks.py tests/unit/test_cli_agent_task_analytics.py tests/unit/test_cli_claim_support.py tests/unit/test_cli_improvement_cases.py tests/unit/test_cli_search_harness.py tests/unit/test_search_api.py tests/unit/test_search_api_replays.py tests/unit/test_search_api_harnesses.py tests/unit/test_search_api_learning_audit.py tests/unit/test_documents_api.py tests/unit/test_documents_api_artifacts.py tests/unit/test_documents_api_semantics.py`
- `uv run docling-system-improvement-case-validate`
- `uv run docling-system-improvement-case-summary`
- `uv run docling-system-architecture-inspect`
- `uv run docling-system-capability-contracts`
- `uv run docling-system-architecture-quality-report --summary`
- `uv run docling-system-hotspot-prevention-check --strict`
- `uv run docling-system-hygiene-check`
- `uv run docling-system-evaluation-data-readiness --output storage/evaluation_data_readiness.latest.json`
- `uv run docling-system-agent-trace-review --limit 5 --skip-hygiene`
- `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 12`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs`

Verified results:

- focused split-pack tests plus the final CLI search-harness owner split:
  `119 passed in 4.13s`
- `uv run docling-system-improvement-case-validate`: `valid=true`
- `uv run docling-system-improvement-case-summary`: `case_count=26`,
  `status_counts.open=25`, `status_counts.measured=1`,
  `measured_case_count=11`
- `uv run docling-system-architecture-inspect`: `valid=true`,
  `violation_count=0`
- `uv run docling-system-capability-contracts`: `valid=true`,
  `facade_count=6`, `function_count=110`
- `uv run docling-system-architecture-quality-report --summary`:
  `agent_legibility_average_score=90.0`, `broad_facade_count=2`,
  `hotspot_count=10`, `max_hotspot_risk_score=673.78`, and the top hotspot
  paths no longer include the three split test files
- `uv run docling-system-hotspot-prevention-check --strict`: `blocked=0`,
  `allowed=7`
- `uv run docling-system-hygiene-check`: `new hygiene regressions: none`
- `uv run docling-system-evaluation-data-readiness --output storage/evaluation_data_readiness.latest.json`:
  `regression_ready=true`, `court_grade_ready=true`, `failed_gate_count=0`
- `uv run docling-system-agent-trace-review --limit 5 --skip-hygiene`:
  `observation_count=0`
- architecture probe: `tests/unit/test_cli.py` is now 424 lines and no longer
  appears in the current top 20 hotspot list; the largest-files view also no
  longer includes `tests/unit/test_cli.py`, `tests/unit/test_search_api.py`,
  or `tests/unit/test_documents_api.py`; Python cycle components remain at `3`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs`:
  `1317 passed in 52.04s`

## High Value Technical Paydown Milestone 3 Progress

Milestone 3 is the agent action-family continuation for
`IC-A1E186A34097` / `app/services/agent_task_actions.py`. It is a
behavior-preserving report action-definition split behind the existing
`app.services.agent_task_actions` compatibility registry facade.

Results:

- added `app/services/agent_actions/report_actions.py`
- moved the technical-report action definition family for
  `plan_technical_report`, `build_report_evidence_cards`,
  `prepare_report_agent_harness`,
  `evaluate_document_generation_context_pack`, `draft_technical_report`, and
  `verify_technical_report` out of `app/services/agent_task_actions.py`
- kept `app.services.agent_task_actions` import-compatible by composing the
  new owner registry into the existing action index and leaving
  `app/services/agent_task_action_lookup.py` unchanged as the narrow lookup
  seam
- added focused registry-composition coverage in
  `tests/unit/test_agent_task_actions.py`
- ratcheted `config/hygiene_policy.yaml` so
  `app/services/agent_task_actions.py` now has `ratchet_max_lines: 2746` and
  `ratchet_max_private_helpers: 36`, while
  `app/services/agent_actions/report_actions.py` is now governed under
  `IC-A1E186A34097`
- updated `config/improvement_cases.yaml` so `IC-A1E186A34097` records the
  narrowed 2,746-line hotspot, reduced fan-out 36, and the new owner-module
  placement
- reduced `app/services/agent_task_actions.py` architecture-probe lines from
  `2884` to `2746`, hotspot score from `170156` to `162014`, and fan-out from
  `39` to `36`

Verification:

- `git diff --check`
- `uv run ruff check app/services/agent_actions/report_actions.py app/services/agent_task_actions.py tests/unit/test_agent_task_actions.py tests/unit/test_agent_task_action_lookup.py`
- `uv run pytest -q tests/unit/test_agent_task_actions.py tests/unit/test_agent_task_action_lookup.py`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs`
- `uv run docling-system-improvement-case-validate`
- `uv run docling-system-improvement-case-summary`
- `uv run docling-system-architecture-inspect`
- `uv run docling-system-capability-contracts`
- `uv run docling-system-architecture-quality-report --summary`
- `uv run docling-system-hotspot-prevention-check --strict`
- `uv run docling-system-hygiene-check`
- `uv run docling-system-evaluation-data-readiness --output storage/evaluation_data_readiness.latest.json`
- `uv run docling-system-agent-trace-review --limit 5 --skip-hygiene`
- `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 12`

Verified results:

- `uv run pytest -q tests/unit/test_agent_task_actions.py tests/unit/test_agent_task_action_lookup.py`:
  `55 passed in 1.91s`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs`: `1317 passed in 56.34s`
- `uv run docling-system-improvement-case-validate`: `valid=true`
- `uv run docling-system-improvement-case-summary`: `case_count=26`,
  `status_counts.open=25`, `status_counts.measured=1`,
  `measured_case_count=8`
- `uv run docling-system-architecture-inspect`: `valid=true`,
  `violation_count=0`
- `uv run docling-system-capability-contracts`: `valid=true`,
  `facade_count=6`, `function_count=110`
- `uv run docling-system-architecture-quality-report --summary`:
  `agent_legibility_average_score=90.0`, `broad_facade_count=2`,
  `hotspot_count=10`, `max_hotspot_risk_score=673.78`
- `uv run docling-system-hotspot-prevention-check --strict`: `blocked=0`,
  `allowed=6`
- `uv run docling-system-hygiene-check`: `new hygiene regressions: none`;
  `app/services/agent_task_actions.py` inherited ratchet now records 2,746
  lines and 36 private helpers
- `uv run docling-system-evaluation-data-readiness --output storage/evaluation_data_readiness.latest.json`:
  `regression_ready=true`, `court_grade_ready=true`, `failed_gate_count=0`
- `uv run docling-system-agent-trace-review --limit 5 --skip-hygiene`:
  `observation_count=0`
- architecture probe: `app/services/agent_task_actions.py` is 2,746
  probe-counted lines with hotspot score `162014`; Python cycle components
  remain at `3`

## High Value Technical Paydown Milestone 2 Progress

Milestone 2 is the evidence owner-family continuation for
`IC-050E60059A34` / `app/services/evidence.py`. It is a behavior-preserving
technical-report derivation/export split behind the existing
`app.services.evidence` compatibility facade.

Results:

- added `app/services/evidence_technical_report_exports.py`
- moved the technical-report derivation package builder, provenance-lock
  assembly, export persistence, attach helpers, and claim-derivation payload
  helpers out of `app/services/evidence.py`
- kept `app.services.evidence` import-compatible for
  `build_technical_report_derivation_package`,
  `apply_technical_report_derivation_links`,
  `persist_technical_report_evidence_export`,
  `attach_artifact_to_evidence_export`, and
  `attach_operator_run_to_evidence_export`
- added focused facade/owner coverage in
  `tests/unit/test_evidence_technical_report_exports.py`
- ratcheted `config/hygiene_policy.yaml` so `app/services/evidence.py` now has
  `ratchet_max_lines: 6307` and `ratchet_max_private_helpers: 81`, while the
  new owner module is governed at `ratchet_max_lines: 884`
- updated `config/improvement_cases.yaml` so
  `IC-050E60059A34` records the narrowed 6,307-line hotspot and the new owner
  module placement
- reduced `app/services/evidence.py` architecture-probe lines from `7143` to
  `6307` and hotspot score from `342864` to `302736`

Verification:

- `git diff --check`
- `uv run ruff check app tests`
- `uv run pytest -q tests/unit/test_evidence_technical_report_exports.py tests/unit/test_technical_reports.py`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs tests/integration/test_technical_report_harness_roundtrip.py`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs`
- `uv run docling-system-improvement-case-validate`
- `uv run docling-system-improvement-case-summary`
- `uv run docling-system-architecture-inspect`
- `uv run docling-system-architecture-quality-report --summary`
- `uv run docling-system-hotspot-prevention-check --strict`
- `uv run docling-system-hygiene-check`
- `uv run docling-system-evaluation-data-readiness --output storage/evaluation_data_readiness.latest.json`
- `uv run docling-system-agent-trace-review --limit 5 --skip-hygiene`
- `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 12`

Verified results:

- `uv run pytest -q tests/unit/test_evidence_technical_report_exports.py tests/unit/test_technical_reports.py`:
  `15 passed`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs tests/integration/test_technical_report_harness_roundtrip.py`:
  `1 passed`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs`:
  `1316 passed in 53.75s`
- `uv run docling-system-improvement-case-validate`: `valid=true`
- `uv run docling-system-improvement-case-summary`: `case_count=26`,
  `status_counts.open=25`, `status_counts.measured=1`,
  `measured_case_count=7`
- `uv run docling-system-architecture-inspect`: `valid=true`,
  `violation_count=0`
- `uv run docling-system-architecture-quality-report --summary`:
  `agent_legibility_average_score=90.0`, `broad_facade_count=2`,
  `hotspot_count=10`, `max_hotspot_risk_score=673.78`
- `uv run docling-system-hotspot-prevention-check --strict`: `blocked=0`
- `uv run docling-system-hygiene-check`: `new hygiene regressions: none`;
  `app/services/evidence.py` inherited ratchet now records 6,307 lines and 81
  private helpers; `app/services/evidence_technical_report_exports.py` is now
  governed as inherited budget debt at 884 lines under `IC-050E60059A34`
- `uv run docling-system-evaluation-data-readiness --output storage/evaluation_data_readiness.latest.json`:
  `regression_ready=true`, `court_grade_ready=true`, `failed_gate_count=0`
- `uv run docling-system-agent-trace-review --limit 5 --skip-hygiene`:
  `observation_count=0`
- architecture probe: `app/services/evidence.py` is 6,307 probe-counted lines
  with hotspot score `302736`; Python cycle components remain at `3`

## High Value Technical Paydown Milestone 1 Progress

Milestone 1 is the retrieval-interaction model-domain split for
`IC-F2A8110185EB` / `app/db/models.py`. It is a behavior-preserving ORM owner
split behind the existing `app.db.models` compatibility facade.

Results:

- added `app/db/model_domains/retrieval_interactions.py`
- moved `SearchRequestRecord`, `SearchRequestResult`,
  `RetrievalEvidenceSpan`, `RetrievalEvidenceSpanMultiVector`,
  `SearchRequestResultSpan`, `SearchFeedback`, `ChatAnswerRecord`, and
  `ChatAnswerFeedback` out of `app/db/models.py`
- kept `app.db.models` import-compatible by re-exporting the moved classes
  through import-forwarder aliases that satisfy the hotspot-prevention gate
- extended `tests/db_model_contract.py`,
  `tests/unit/test_db_model_import_compatibility.py`, and
  `tests/integration/test_db_model_metadata.py` to cover retrieval-interaction
  table columns, exact index column ordering, exact unique-constraint column
  ordering, vector dimensions, and computed TSVECTOR SQL
- ratcheted `config/hygiene_policy.yaml` so `app/db/models.py` now has
  `ratchet_max_lines: 5067`, and the new owner module
  `app/db/model_domains/retrieval_interactions.py` is governed under the same
  owner case
- reduced `app/db/models.py` from 5,537 lines to 5,067 lines
- reduced the architecture-quality `max_hotspot_risk_score` from `688.91` at
  Milestone 0 closeout to `673.78`

Verification:

- `git diff --check`
- `uv run ruff check app tests`
- `uv run pytest -q tests/unit/test_db_model_import_compatibility.py`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs tests/integration/test_db_model_metadata.py`
- `uv run --extra dev alembic heads`
- `uv run --extra dev alembic current`
- `uv run --extra dev alembic upgrade head`
- `uv run --extra dev alembic check`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs`
- `uv run docling-system-evaluation-data-readiness --output storage/evaluation_data_readiness.latest.json`
- `uv run docling-system-agent-trace-review --limit 5 --skip-hygiene`
- `uv run docling-system-architecture-inspect`
- `uv run docling-system-capability-contracts`
- `uv run docling-system-architecture-quality-report --summary`
- `uv run docling-system-hotspot-prevention-check --strict`
- `uv run docling-system-hygiene-check`
- `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 12`

Verified results:

- `uv run pytest -q tests/unit/test_db_model_import_compatibility.py`:
  `307 passed`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs tests/integration/test_db_model_metadata.py`:
  `84 passed`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs`: `1311 passed`
- `uv run --extra dev alembic heads`: single head
  `0076_claim_feedback_replay_src`
- `uv run --extra dev alembic current`: `0076_claim_feedback_replay_src`
- `uv run --extra dev alembic check`: `No new upgrade operations detected.`
- `uv run docling-system-evaluation-data-readiness --output storage/evaluation_data_readiness.latest.json`:
  `regression_ready=true`, `court_grade_ready=true`, `failed_gate_count=0`
- `uv run docling-system-agent-trace-review --limit 5 --skip-hygiene`:
  `observation_count=0`
- `uv run docling-system-architecture-inspect`: `valid=true`,
  `violation_count=0`
- `uv run docling-system-capability-contracts`: `valid=true`,
  `facade_count=6`, `function_count=110`
- `uv run docling-system-architecture-quality-report --summary`:
  `hotspot_count=10`, `max_hotspot_risk_score=673.78`
- `uv run docling-system-hotspot-prevention-check --strict`: `blocked=0`
- `uv run docling-system-hygiene-check`: `new hygiene regressions: none`
- architecture probe still reports `app/db/models.py` as the top hotspot, but
  now at `5067` lines and score `364824`

## High Value Technical Paydown Milestone 0 Progress

Milestone 0 is the baseline-lock and UI owner-bootstrap slice for the new
high-value paydown plan. It is a governance-and-doc checkpoint, not a runtime
behavior change.

Results:

- corrected the UI milestone verification command in
  `docs/high_value_technical_paydown_milestone_plan.md` from the nonexistent
  `tests/unit/test_ui_static_assets.py` to `tests/unit/test_ui.py`
- added improvement case `IC-1B643BA0AD90` for `app/ui/app.js`
- recorded in the plan and handoff that `app/ui/app.js` is governed through the
  improvement-case registry and architecture-probe verification because
  `uv run docling-system-hygiene-check` only scans Python files under `app/`
- updated `docs/agentic_architecture_index.md` and `docs/improvement_loop.md`
  so the next routed milestone is the retrieval-interaction split, not another
  owner-bootstrap pass

Verification:

- `git diff --check`
- `python /Users/chunkstand/.codex/skills/milestone-plan-writer/scripts/lint_milestone_plan.py --strict docs/high_value_technical_paydown_milestone_plan.md`
- `uv run docling-system-improvement-case-validate`
- `uv run docling-system-improvement-case-summary`
- `uv run pytest -q tests/unit/test_ui.py`
- `uv run docling-system-hygiene-check`
- `uv run docling-system-architecture-quality-report --summary`
- `uv run docling-system-architecture-inspect`
- `uv run docling-system-capability-contracts`
- `uv run docling-system-hotspot-prevention-check --strict`
- `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 12`

Verified results:

- `uv run docling-system-improvement-case-validate`: `valid=true`,
  `issue_count=0`
- `uv run docling-system-improvement-case-summary`: `case_count=26`,
  `status_counts.open=25`, `status_counts.measured=1`,
  `measured_case_count=7`
- `uv run pytest -q tests/unit/test_ui.py`: `8 passed in 5.32s`
- `uv run docling-system-hygiene-check`: `new hygiene regressions: none`,
  `improvement-case findings: none`, `architecture findings: none`
- `uv run docling-system-architecture-quality-report --summary`:
  `hotspot_count=10`, `max_hotspot_risk_score=688.91`
- `uv run docling-system-architecture-inspect`: `valid=true`,
  `violation_count=0`
- `uv run docling-system-capability-contracts`: `valid=true`,
  `facade_count=6`, `function_count=110`
- `uv run docling-system-hotspot-prevention-check --strict`: `blocked=0`,
  `allowed=0`
- architecture probe still reports `app/ui/app.js` as a hotspot with
  `4335` lines and score `108375`, which is now the explicitly routed UI debt
  surface for Milestone 6 rather than an untracked side note

## Hotspot Owner Resolution Milestone 0 Closeout

Milestone 0 is the owner-bootstrap and baseline-lock slice for the hotspot
owner resolution plan. It is a governance-and-doc alignment milestone, not a
runtime behavior change.

Commit:

- `33c7855` (`architecture: complete hotspot owner milestone 0 bootstrap`)

Results:

- `config/improvement_cases.yaml` now contains explicit open owner cases
  `IC-2112B1ADC5E8` for `app/services/audit_bundles.py` and
  `IC-0D58F1624037` for `app/services/retrieval_learning.py`.
- `config/hygiene_policy.yaml` now routes both surfaces through
  `owner_case_id` instead of
  `owner_milestone=residual-weakness-milestone-2`.
- `uv run docling-system-improvement-case-summary` now reports
  `case_count=25`, `open=24`, `measured=1`.
- `uv run docling-system-hygiene-check` shows both surfaces under explicit case
  ownership with no new hygiene regressions.
- `docs/hotspot_owner_resolution_plan.md`, `docs/agentic_architecture_index.md`,
  `docs/improvement_loop.md`, and this handoff now agree on the owner bootstrap
  result and route the next implementation slice to Milestone 1.

Verification:

- `git diff --check`
- `uv run ruff check app tests`
- `uv run docling-system-improvement-case-validate`
- `uv run docling-system-improvement-case-summary`
- `uv run docling-system-architecture-inspect`
- `uv run docling-system-capability-contracts`
- `uv run docling-system-architecture-quality-report --summary`
- `uv run docling-system-hotspot-prevention-check --strict`
- `uv run docling-system-hygiene-check`
- `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 12`

## Hotspot Owner Resolution Milestone 1 Closeout

Milestone 1 is the `app/db/models.py` document-artifacts domain continuation.
It is a behavior-preserving ORM ownership split behind the existing
`app.db.models` compatibility facade.

Commit:

- `060b537` (`architecture: complete hotspot owner milestone 1 document-artifacts`)

Results:

- Added `app/db/model_domains/document_artifacts.py`.
- Moved `DocumentRunEvaluation`, `DocumentRunEvaluationQuery`,
  `DocumentChunk`, `DocumentTable`, `DocumentTableSegment`, and
  `DocumentFigure` out of `app/db/models.py`.
- Kept `app.db.models` import-compatible by re-exporting the moved classes.
- Extended the shared metadata contract to cover document-artifact table
  columns, required index names, exact index column ordering, required unique
  constraint names, and exact unique-constraint column ordering.
- Reduced `app/db/models.py` from 5,800 lines to 5,537 lines.
- Ratcheted `config/hygiene_policy.yaml` so `app/db/models.py` now has
  `ratchet_max_lines: 5537`.
- Reduced the architecture-quality `max_hotspot_risk_score` from `692.67` to
  `681.91` while leaving `app/db/models.py` as the top hotspot.

Verification:

- `git diff --check`
- `uv run ruff check app tests`
- `uv run pytest -q tests/unit/test_db_model_import_compatibility.py`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs tests/integration/test_db_model_metadata.py`
- `uv run --extra dev alembic heads`
- `uv run --extra dev alembic current`
- `uv run --extra dev alembic upgrade head`
- `uv run --extra dev alembic check`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs`
- `uv run docling-system-architecture-inspect`
- `uv run docling-system-capability-contracts`
- `uv run docling-system-architecture-quality-report --summary`
- `uv run docling-system-hotspot-prevention-check --strict`
- `uv run docling-system-hygiene-check`
- `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 12`

Verified closeout results:

- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs`: `1236 passed in 51.40s`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs tests/integration/test_db_model_metadata.py`: `50 passed`
- `uv run pytest -q tests/unit/test_db_model_import_compatibility.py`: `271 passed`
- `uv run docling-system-architecture-quality-report --summary`:
  `hotspot_count=10`, `max_hotspot_risk_score=681.91`

## Hotspot Owner Resolution Milestone 2 Closeout

Milestone 2 is the evidence and audit bundle split pack. It is a
behavior-preserving service modularization pass behind the existing
`app/services/evidence.py` and `app/services/audit_bundles.py` facades.

Commit:

- `a0bd36b` (`architecture: complete hotspot owner milestone 2 evidence-audit`)

Results:

- Added `app/services/evidence_manifest_traces.py` and moved the technical
  report evidence trace graph build, persistence, and integrity concern behind
  the existing `get_agent_task_evidence_trace` and manifest refresh flows.
- Added `app/services/audit_bundle_replay_alert_corpus.py` and moved retrieval
  training replay-alert corpus lineage payload assembly and bundle freshness
  status checks behind the existing audit-bundle entry points.
- Reduced `app/services/evidence.py` from 8,076 lines to 7,143 and
  `app/services/audit_bundles.py` from 3,862 lines to 3,306.
- Added a hygiene ratchet entry for `app/services/evidence_manifest_traces.py`
  under `owner_case_id: IC-050E60059A34` with `ratchet_max_lines: 980`, which
  keeps the new owner module governed without reopening new hygiene debt.
- Kept `docling-system-hotspot-prevention-check --strict` green by reducing
  the `evidence` facade change to allowed import-forwarder delegation only.
- `uv run docling-system-evaluation-data-readiness --output storage/evaluation_data_readiness.latest.json`
  remains `regression_ready=true`, `court_grade_ready=true`, and
  `failed_gate_count=0`.
- `uv run docling-system-agent-trace-review --limit 5 --skip-hygiene` reports
  `observation_count=0`.
- The next routed implementation slice is Milestone 3: Claim Support Policy
  Impacts Split.

Verification:

- `git diff --check`
- `uv run ruff check app tests`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q tests/integration/test_technical_report_harness_roundtrip.py::test_technical_report_harness_roundtrip -rs`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q tests/integration/test_retrieval_learning_ledger.py -k "claim_support_replay_alert or training_audit_bundle or release_audit" -rs`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs`
- `uv run docling-system-architecture-inspect`
- `uv run docling-system-capability-contracts`
- `uv run docling-system-architecture-quality-report --summary`
- `uv run docling-system-hotspot-prevention-check --strict`
- `uv run docling-system-hygiene-check`
- `uv run docling-system-evaluation-data-readiness --output storage/evaluation_data_readiness.latest.json`
- `uv run docling-system-agent-trace-review --limit 5 --skip-hygiene`
- `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 12`

Verified closeout results:

- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs`: `1236 passed in 56.65s`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q tests/integration/test_technical_report_harness_roundtrip.py::test_technical_report_harness_roundtrip -rs`: `1 passed`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q tests/integration/test_retrieval_learning_ledger.py -k "claim_support_replay_alert or training_audit_bundle or release_audit" -rs`: `2 passed, 8 deselected`
- `uv run docling-system-architecture-quality-report --summary`:
  `hotspot_count=10`, `max_hotspot_risk_score=688.91`
- `uv run docling-system-hotspot-prevention-check --strict`:
  `blocked=0`, `allowed=6`
- `uv run docling-system-agent-trace-review --limit 5 --skip-hygiene`:
  `observation_count=0`

## Hotspot Owner Resolution Milestone 3 Closeout

Milestone 3 is the claim-support replay-alert fixture coverage split. It is a
behavior-preserving service modularization pass behind the existing
`app/services/claim_support_policy_impacts.py` compatibility facade.

Commit:

- `afc324a` (`architecture: complete hotspot owner milestone 3 claim-support`)

Results:

- Added `app/services/claim_support_replay_alert_promotions.py`.
- Moved replay-alert fixture coverage summary, candidate derivation, fixture
  promotion, and waiver-closure governance out of
  `app/services/claim_support_policy_impacts.py` while keeping the original
  public service surface import-stable.
- Reduced `app/services/claim_support_policy_impacts.py` from 3,477 lines to
  2,011 and ratcheted it to `ratchet_max_lines: 2011` and
  `ratchet_max_private_helpers: 42`.
- Added a hygiene ratchet entry for
  `app/services/claim_support_replay_alert_promotions.py` under
  `owner_case_id: IC-E2270F89B397` with `ratchet_max_lines: 1536` and
  `ratchet_max_private_helpers: 24`.
- Updated `config/improvement_cases.yaml` so
  `IC-E2270F89B397` records the verified Milestone 3 reduction result.
- The next routed implementation slice is Milestone 4: Retrieval Learning
  Split.

Verification:

- `git diff --check`
- `uv run ruff check app tests`
- `uv run pytest -q tests/unit/test_claim_support_policy_impacts.py tests/unit/test_agent_tasks_api.py -k "fixture_candidates or fixture_promotion"`
- `uv run pytest -q tests/unit/test_api_architecture.py tests/unit/test_architecture_inspection.py -q`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs`
- `uv run docling-system-improvement-case-validate`
- `uv run docling-system-improvement-case-summary`
- `uv run docling-system-architecture-inspect`
- `uv run docling-system-capability-contracts`
- `uv run docling-system-architecture-quality-report --summary`
- `uv run docling-system-hotspot-prevention-check --strict`
- `uv run docling-system-hygiene-check`
- `uv run docling-system-evaluation-data-readiness --output storage/evaluation_data_readiness.latest.json`
- `uv run docling-system-agent-trace-review --limit 5 --skip-hygiene`

Verified closeout results:

- `uv run pytest -q tests/unit/test_claim_support_policy_impacts.py tests/unit/test_agent_tasks_api.py -k "fixture_candidates or fixture_promotion"`:
  `4 passed, 34 deselected`
- `uv run pytest -q tests/unit/test_api_architecture.py tests/unit/test_architecture_inspection.py -q`:
  `21 passed`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs`:
  `1236 passed in 54.83s`
- `uv run docling-system-architecture-quality-report --summary`:
  `hotspot_count=10`, `max_hotspot_risk_score=688.91`
- `uv run docling-system-hotspot-prevention-check --strict`:
  `blocked=0`, `allowed=0`
- `uv run docling-system-agent-trace-review --limit 5 --skip-hygiene`:
  `observation_count=0`

## Hotspot Owner Resolution Milestone 4 Closeout

Milestone 4 is the retrieval-learning replay-alert corpus split. It is a
behavior-preserving service modularization pass behind the existing
`app/services/retrieval_learning.py` compatibility facade.

Commit:

- `13e8b1c` (`architecture: complete hotspot owner milestone 4 retrieval-learning`)

Results:

- Added `app/services/retrieval_learning_replay_alert_sources.py`.
- Moved replay-alert corpus lineage validation, judgment materialization, and
  hard-negative construction out of `app/services/retrieval_learning.py`
  while keeping the original public service surface import-stable.
- Reduced `app/services/retrieval_learning.py` from 3,028 lines to 2,482 and
  ratcheted it to `ratchet_max_lines: 2482` and
  `ratchet_max_private_helpers: 46`.
- Added a hygiene budget entry for
  `app/services/retrieval_learning_replay_alert_sources.py` under
  `owner_case_id: IC-0D58F1624037` with `max_lines: 578` and
  `max_private_helpers: 10`.
- Updated `config/improvement_cases.yaml` so `IC-0D58F1624037` records the
  verified Milestone 4 reduction result.
- The next routed implementation slice is Milestone 5: Search Core Split
  Continuation.

Verification:

- `git diff --check`
- `uv run ruff check app/services/retrieval_learning.py app/services/retrieval_learning_replay_alert_sources.py tests/unit/test_retrieval_learning_candidates.py tests/unit/test_retrieval_learning_replay_alert_sources.py tests/integration/test_retrieval_learning_ledger.py`
- `uv run pytest -q tests/unit/test_retrieval_learning_candidates.py tests/unit/test_retrieval_learning_replay_alert_sources.py`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q tests/integration/test_retrieval_learning_ledger.py -k "replay_alert_corpus" -rs`
- `uv run pytest -q tests/unit/test_api_architecture.py tests/unit/test_architecture_inspection.py`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs`
- `uv run docling-system-improvement-case-validate`
- `uv run docling-system-improvement-case-summary`
- `uv run docling-system-architecture-inspect`
- `uv run docling-system-capability-contracts`
- `uv run docling-system-architecture-quality-report --summary`
- `uv run docling-system-hotspot-prevention-check --strict`
- `uv run docling-system-hygiene-check`
- `uv run docling-system-evaluation-data-readiness --output storage/evaluation_data_readiness.latest.json`
- `uv run docling-system-agent-trace-review --limit 5 --skip-hygiene`

Verified closeout results:

- `uv run pytest -q tests/unit/test_retrieval_learning_candidates.py tests/unit/test_retrieval_learning_replay_alert_sources.py`:
  `4 passed`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q tests/integration/test_retrieval_learning_ledger.py -k "replay_alert_corpus" -rs`:
  `4 passed, 6 deselected`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs`:
  `1238 passed in 59.61s`
- `uv run docling-system-improvement-case-summary`:
  `case_count=25`, `status_counts.open=24`, `status_counts.measured=1`, and
  `measured_case_count=3`
- `uv run docling-system-architecture-quality-report --summary`:
  `hotspot_count=10`, `max_hotspot_risk_score=688.91`
- `uv run docling-system-hotspot-prevention-check --strict`:
  `blocked=0`, `allowed=0`
- `uv run docling-system-evaluation-data-readiness --output storage/evaluation_data_readiness.latest.json`:
  `regression_ready=true`, `court_grade_ready=true`, `failed_gate_count=0`
- `uv run docling-system-agent-trace-review --limit 5 --skip-hygiene`:
  `observation_count=0`

## Hotspot Owner Resolution Milestone 5 Closeout

Milestone 5 is the search-ranking split. It is a behavior-preserving service
modularization pass behind the existing `app/services/search.py`
compatibility facade.

Commit:

- `c871dd9` (`architecture: complete hotspot owner milestone 5 search-ranking`)

Results:

- Added `app/services/search_ranking.py`.
- Moved ranking helpers, reranking, hybrid-result merging, result rendering,
  and ranked-result utility types out of `app/services/search.py` while
  keeping the original public service surface import-stable.
- Reduced `app/services/search.py` from 3,250 lines to 2,851 and ratcheted it
  to `ratchet_max_lines: 2851`; the facade still carries 53 private helpers
  under an aligned helper ceiling of 65.
- Added a hygiene budget entry for `app/services/search_ranking.py` under
  `owner_case_id: IC-1D03DBFE8492` with `max_lines: 467` and
  `max_private_helpers: 0`.
- Updated `config/improvement_cases.yaml` so `IC-1D03DBFE8492` records the
  verified Milestone 5 reduction result.
- The next routed implementation slice is Milestone 6: Closeout And Case
  Lifecycle Alignment.

Verification:

- `git diff --check`
- `uv run ruff check app/services/search.py app/services/search_ranking.py tests/unit/test_search_service.py tests/unit/test_search_ranking.py`
- `uv run pytest -q tests/unit/test_search_service.py tests/unit/test_search_ranking.py`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q tests/integration/test_postgres_roundtrip.py -k "search" -rs`
- `uv run pytest -q tests/unit/test_api_architecture.py tests/unit/test_architecture_inspection.py`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs`
- `uv run docling-system-improvement-case-validate`
- `uv run docling-system-improvement-case-summary`
- `uv run docling-system-architecture-inspect`
- `uv run docling-system-capability-contracts`
- `uv run docling-system-architecture-quality-report --summary`
- `uv run docling-system-hotspot-prevention-check --strict`
- `uv run docling-system-hygiene-check`
- `uv run docling-system-evaluation-data-readiness --output storage/evaluation_data_readiness.latest.json`
- `uv run docling-system-agent-trace-review --limit 5 --skip-hygiene`

## Hotspot Owner Resolution Milestone 6 Closeout

Milestone 6 is the docs-and-case lifecycle closeout for the hotspot owner
resolution plan. It is a governance milestone, not another code split.

Commit:

- `76526ef` (`architecture: complete hotspot owner milestone 6 closeout`)

Results:

- Updated `config/improvement_cases.yaml` so the six targeted hotspot owner
  cases now carry the correct post-milestone deployment refs and measurement
  evidence for Milestones 1-5.
- Corrected the stale owner-case payload on `IC-F2A8110185EB`, which had been
  carrying claim-support reduction data instead of the
  `app/db/models.py` Milestone 1 result.
- Confirmed all six targeted surfaces now route through explicit `owner_case_id`
  entries in `config/hygiene_policy.yaml`; no selected hotspot remains routed
  through `owner_milestone=residual-weakness-milestone-2`.
- Added the missing Milestone 3 commit reference and aligned this handoff,
  `docs/agentic_architecture_index.md`, and
  `docs/hotspot_owner_resolution_plan.md` to the same completed-sequence state.
- The hotspot owner resolution plan is now complete locally. At that closeout
  checkpoint, the next owner-scoped implementation route was
  `IC-F2A8110185EB` / `app/db/models.py`; active follow-on routing now lives in
  the High Value Technical Paydown plan.

Verification:

- `git diff --check`
- `uv run docling-system-improvement-case-validate`
- `uv run docling-system-improvement-case-summary`
- `uv run docling-system-architecture-inspect`
- `uv run docling-system-capability-contracts`
- `uv run docling-system-architecture-quality-report --summary`
- `uv run docling-system-hotspot-prevention-check --strict`
- `uv run docling-system-hygiene-check`

## Milestone 6 Regression Readiness Closeout

Milestone 6 is a runtime-and-data milestone, not a code-change milestone. The
implemented result is a rebuilt local evaluation corpus and replay baseline that
now satisfy the regression tier of
`uv run docling-system-evaluation-data-readiness`.

Results:

- `regression_ready=true`, `court_grade_ready=false`,
  `regression_blockers=[]`, `failed_gate_count=7`
- active documents: 26
- completed evaluations: 26
- passed evaluation queries: 52
- auto-generated corpus coverage: 26 documents, 26 table queries, 25 chunk
  queries
- manual reviewed seed coverage: 1 document, 1 table query, 1 chunk query, 1
  cross-document query
- completed replay coverage present for `evaluation_queries`,
  `live_search_gaps`, and `cross_document_prose_regressions`, with passing
  replay cases now present in the latter two lanes

Operational notes:

- The empty baseline was reset with
  `uv run docling-system-knowledge-base-reset --execute --confirm CLEAR_KNOWLEDGE_BASE --allow-active-work`,
  which created a fresh local database and archived the prior state under
  `reset-archives/20260510T041438Z`.
- Host CLI ingest plus the Docker worker did not share a safe source-file path
  contract for this milestone, and the Docker worker later hit a Docling TLS
  assertion. To keep the milestone scoped to data readiness, the corpus build
  used a host worker against the same local Postgres DB instead of changing
  runtime code.
- `docs/evaluation_corpus.yaml` is no longer empty. It now contains a reviewed
  one-document seed fixture for `regression_doc_03.pdf`. Because manual corpus
  loading is opt-in by design, the persisted manual-fixture evaluation rows were
  created with
  `DOCLING_SYSTEM_MANUAL_EVALUATION_CORPUS_PATH=docs/evaluation_corpus.yaml uv run docling-system-eval-corpus`.
- The first closeout commit for this milestone is
  `4e257e8 docs: close residual weakness milestone 6`. This handoff revision
  records the follow-up hardening that turned the empty `live_search_gaps` and
  `cross_document_prose_regressions` lanes into passing replay coverage.
- The host worker completed the representative corpus build and document
  evaluations cleanly. The Docker `api`, `worker`, and `agent-worker` services
  were stopped during the milestone execution.

## Milestone 7 Court-Grade Readiness Closeout

Milestone 7 extends the runtime-and-data work from the regression tier to the
court-grade evaluation-data tier. The live DB now passes
`uv run docling-system-evaluation-data-readiness` with
`court_grade_ready=true`.

Results:

- `regression_ready=true`, `court_grade_ready=true`,
  `regression_blockers=[]`, `court_grade_blockers=[]`,
  `passed_gate_count=11`, `failed_gate_count=0`
- manual reviewed corpus coverage: 5 documents, 10 table queries, 20 chunk
  queries, 5 cross-document queries, 5 answer queries
- operator feedback coverage: 25 rows total, with 5 rows each for
  `relevant`, `irrelevant`, `missing_table`, `missing_chunk`, and `no_answer`
- technical-report claim feedback: 25 rows total, with learning labels
  `positive=10`, `negative=10`, `missing=5`, support statuses
  `supported=5`, `weak=5`, `missing=5`, `contradicted=5`, `rejected=5`, and
  `traceability_issue_counts={}`
- claim-support replay-alert corpus: 1 active snapshot with 5 governed rows
- completed replay coverage present for `evaluation_queries`, `feedback`,
  `live_search_gaps`, `cross_document_prose_regressions`, and
  `technical_report_claim_feedback`
- harness evaluation source coverage: one completed source row for each
  required replay source
- retrieval learning: 1 judgment set, 1 completed training run, 122 training
  examples

Operational notes:

- `docs/evaluation_corpus.yaml` now carries the reviewed court-grade seed set,
  not just the earlier single-document regression seed.
- Court-grade feedback replay intentionally includes `no_answer` cases that
  should replay to zero search results. `app/agent_trace_review.py` now treats
  successful `feedback` replay runs with zero-result queries as expected
  coverage instead of false-positive replay regressions.
- The runtime/data milestone remained scoped: the court-grade closeout reused
  the existing replay, harness-evaluation, and retrieval-learning services
  rather than adding a new bootstrap command.

## Milestone 8 Residual Weakness Closeout

Milestone 8 is the closeout-and-alignment pass for the full residual-weakness
sequence. It does not claim new runtime functionality; it proves the remaining
weaknesses are now either prevented, reduced, or explicitly routed through
owner-scoped follow-up surfaces.

Results:

- hotspot prevention remains active and clean on the current diff:
  `known_hotspots=6`, `changed_hotspots=0`, `blocked=0`
- architecture quality shows no new hotspot growth:
  `hotspot_count=10`, `max_hotspot_risk_score=692.67`, top hotspots unchanged
- the general architecture probe still reports no large agent-task cycle
  component and only the two previously accepted small Python cycle components
- hygiene remains in the ratcheted state:
  `ruff regressions=none`, `new hygiene regressions=none`, inherited debt only
- evaluation-data readiness remains fully green:
  `regression_ready=true`, `court_grade_ready=true`,
  `passed_gate_count=11`, `failed_gate_count=0`
- the improvement-case registry is now the explicit residual-risk routing
  surface: `case_count=23`, `open=22`, `measured=1`

Operational notes:

- This milestone is a docs-and-governance closeout, not a new architecture
  split or runtime-data bootstrap.
- Remaining debt is no longer routed as another broad residual-weakness
  milestone. Future work should target owner-scoped improvement cases or new
  focused milestone plans tied to one governed debt surface at a time.

The current system is a local-first, durable document-intelligence platform with:

- active-run-gated PDF ingest, parsing, validation, and promotion
- mixed chunk/table retrieval, grounded chat, search replay, and harness governance
- figure, table, chunk, span, evidence, and audit-bundle provenance in Postgres plus canonical JSON artifacts
- authenticated remote mode with route capability contracts and mutation-key gates
- additive semantic ontology, fact-graph, and graph-memory workflows
- technical-report generation with context-pack evaluation, claim provenance locks, support-judge calibration, and audit bundles
- DB-backed agent-task orchestration with typed actions, context refs, approvals, attempts, outcomes, traces, and cost/performance telemetry
- architecture, capability, decision, hygiene, improvement-case, and trace-review governance commands

## Recent Local Milestone Commits Since `origin/main`

The most recent routed milestone commits ahead of `origin/main` before the
current alignment pass are:

- `e59f9bf` (`architecture: split agent task models`), which moves the
  agent-task and knowledge-operator ORM family into
  `app/db/model_domains/agent_tasks.py`, expands the shared metadata contract
  harness, refreshes the owner-case registry and routing docs, and leaves the
  broader `IC-F2A8110185EB` owner case reduced rather than resolved

- `b69c4f6` (`architecture: split evaluation feedback models`), which moves
  `EvalObservation` and `EvalFailureCase` into
  `app/db/model_domains/evaluation_feedback.py`, expands the shared metadata
  contract harness, refreshes the owner-case registry and routing docs, and
  leaves the broader `IC-F2A8110185EB` owner case reduced rather than resolved

- `81f6260` (`docs: close evaluation feedback milestone 0 preflight`), which
  closes the evaluation-feedback Milestone 0 baseline lock, records the live
  preflight verification outputs in the handoff and active plan, and routes the
  next implementation slice to Milestone 1
- `f8f4590` (`docs: add evaluation feedback milestone preflight`), which adds
  the bounded evaluation-feedback model-domain plan for
  `IC-F2A8110185EB` / `app/db/models.py`
- `b0bf19c` (`docs: align current-state snapshots with milestone 10`), which
  closes the High Value Technical Paydown plan through Milestone 10 and routes
  the next owner-scoped follow-up to the evaluation-feedback candidate

These commits add the dedicated evaluation-feedback follow-up brief, close the
Milestone 0 preflight slice that had to pass before the ORM move began, and
commit the evaluation-feedback owner split that now routes the broader
`app/db/models.py` owner case to the agent-task family.

## Current Architecture And Governance State

Current read-only gates from this checkout:

```text
uv run docling-system-architecture-inspect
  valid=true, violation_count=0, api_route_count=130,
  agent_action_count=51, contract_count=10, inspection_rule_count=13

uv run docling-system-capability-contracts
  valid=true, facade_count=6, function_count=111, issues=[]

uv run docling-system-architecture-quality-report --summary
  agent_legibility_average_score=90.0
  broad_facade_count=2
  hotspot_count=10
  max_hotspot_risk_score=501.06
  top_hotspot_paths=[
    app/db/models.py,
    app/services/agent_task_actions.py,
    app/cli.py,
    app/schemas/agent_tasks.py,
    app/services/evidence.py
  ]

python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 20
  Python cycle components=3
  claim-support policy_impacts/promotions cycle removed
  remaining cycles: search/documents/evaluations/runs/semantics,
  evidence-provenance export graph, evidence-search packages/trace-store

uv run docling-system-improvement-case-summary
  case_count=38, measured=1, deployed=15, open=22,
  source_type_counts={hygiene_finding: 6, architecture_governance: 32}

uv run docling-system-hotspot-prevention-check --strict
  known_hotspots=27, changed_hotspots=7, added_lines=521, deleted_lines=5546,
  blocked=0, allowed=7, exceptions=0

uv run docling-system-hygiene-check
  ruff regressions=none
  inherited budget debt listed with owner_case_id or owner_milestone
  new hygiene regressions=none
  improvement-case findings=none
  architecture findings=none
```

The architecture boundary model is clean, but hotspot debt remains real. The
current top governed split targets are `app/db/models.py`,
`app/services/agent_task_actions.py`, `app/cli.py`,
`app/schemas/agent_tasks.py`, and `app/services/evidence.py`. The
claim-support residual owner family is no longer part of the live cycle backlog
or inherited hygiene debt set.

Strict hygiene debt also remains real, but it is now ratcheted: the current
file/helper overages are non-blocking inherited entries while unchanged, and any
growth beyond their `ratchet_max_*` ceilings is a blocking hygiene regression.
The remaining inherited list still includes the hotspot-prevention classifier
at `999` lines under `IC-6C1B516A3F92`, while both claim-support owner cases
are now deployed locally.

`app/services/agent_task_actions.py` remains a high fan-out action-orchestration
entrypoint, not a context/task dependency. `app/services/agent_task_context.py`,
`app/services/agent_task_context_store.py`, and `app/services/agent_tasks.py`
must use `app/services/agent_task_action_lookup.py` for action lookup and
validation so the static back edge does not return.

## Runtime Gate Snapshot

Milestone 0 restored the DB-backed runtime gate on 2026-05-09.

Commands run:

```bash
open -a Docker
docker version
docker compose config --quiet
docker compose up -d db
docker compose ps
uv run --extra dev alembic heads
uv run --extra dev alembic current
uv run --extra dev alembic upgrade head
DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs
uv run ruff check app tests
uv run docling-system-architecture-inspect
uv run docling-system-capability-contracts
uv run docling-system-architecture-quality-report --summary
uv run docling-system-evaluation-data-readiness
uv run docling-system-agent-trace-review --limit 5 --skip-hygiene
```

Results:

```text
Docker Desktop: running after `open -a Docker`.
Compose config: valid.
Compose runtime: `docling-system-db` healthy on localhost:5432; `worker` and `agent-worker` running.
Alembic heads: `0076_claim_feedback_replay_src (head)`.
Alembic current: `0076_claim_feedback_replay_src (head)`.
Alembic upgrade head: completed with no pending migrations.
Full DB-backed tests: `872 passed in 51.00s`.
Ruff: All checks passed.
Architecture inspection: valid, `violation_count=0`.
Capability contracts: valid, `facade_count=6`, `function_count=110`, `issues=[]`.
Architecture quality summary: `agent_legibility_average_score=90.0`, `broad_facade_count=2`, `hotspot_count=10`.
Evaluation-data readiness: command runs against Postgres; `regression_ready=false`, `court_grade_ready=false`, `failed_gate_count=11`.
Agent trace review: command runs against Postgres; `observation_count=0`.
```

## Data Model Compatibility Harness Snapshot

Milestone 1 implemented, verified, and locally committed the pre-split
compatibility harness on 2026-05-09. No ORM classes moved.

Files added or updated for the harness:

- `app/db/models.py`
- `tests/db_model_contract.py`
- `tests/unit/test_db_model_import_compatibility.py`
- `tests/integration/test_db_model_metadata.py`
- `docs/data_model_boundary_plan.md`
- `docs/architecture_plan_01.md`

Focused verification:

```bash
uv run pytest -q tests/unit/test_db_model_import_compatibility.py
DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs tests/integration/test_db_model_metadata.py
DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs tests/integration
DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs
uv run ruff check app tests
uv run docling-system-architecture-inspect
uv run docling-system-capability-contracts
uv run docling-system-architecture-quality-report --summary
uv run --extra dev alembic check
```

Results:

```text
model import compatibility: 221 passed.
Postgres model metadata/create-all check: 3 passed.
Postgres integration suite: 72 passed.
Full DB-backed suite: 1096 passed in 47.41s.
Ruff: passed.
Architecture inspection: valid, violation_count=0.
Capability contracts: valid.
Architecture quality summary: hotspot_count=10, max_hotspot_risk_score=674.68.
Alembic check: no new upgrade operations detected.
```

The harness protects 109 public `app.db.models` symbols: 29 enums and 80 ORM
model classes. It also asserts the full 80-table `Base.metadata` contract and
checks schema-scoped Postgres `Base.metadata.create_all(...)`. During closeout,
the harness also closed a pre-existing Alembic metadata drift by declaring the
migrated `ix_document_runs_status_completed_at` index on `DocumentRun` metadata
and testing required model indexes in unit and Postgres create-all paths.

## Data Model Domain Split Snapshot

Milestone 2 implemented, verified, and locally committed the first physical ORM
model-domain split on 2026-05-09.

Files added or updated for the split:

- `app/db/model_domains/__init__.py`
- `app/db/model_domains/platform.py`
- `app/db/models.py`
- `tests/db_model_contract.py`
- `tests/unit/test_db_model_import_compatibility.py`
- `tests/integration/test_db_model_metadata.py`
- `docs/data_model_boundary_plan.md`
- `docs/architecture_plan_01.md`

Implemented result:

- `ApiIdempotencyKey` moved to `app/db/model_domains/platform.py`.
- `app/db/models.py` remains import-compatible by re-exporting
  `ApiIdempotencyKey`.
- No other ORM classes moved.
- `api_idempotency_keys` table name, columns, JSONB response storage,
  `ix_api_idempotency_keys_created_at`, and
  `uq_api_idempotency_keys_scope_key` are preserved and covered.
- The platform-support contract now checks exact index and unique-constraint
  column ordering in both unit metadata and Postgres create-all paths.
- `app/db/models.py` is now 6,006 lines; the new platform domain module is
  35 lines.

Focused verification:

```bash
git diff --check
uv run ruff check app tests
uv run pytest -q tests/unit/test_db_model_import_compatibility.py
DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs tests/integration/test_db_model_metadata.py
uv run --extra dev alembic heads
uv run --extra dev alembic current
uv run --extra dev alembic upgrade head
uv run --extra dev alembic check
DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs
uv run docling-system-architecture-inspect
uv run docling-system-capability-contracts
uv run docling-system-architecture-quality-report --summary
```

Results:

```text
model import compatibility: 226 passed.
Postgres model metadata/create-all check: 7 passed.
Alembic heads/current: 0076_claim_feedback_replay_src (head).
Alembic upgrade head: completed with no pending migrations.
Alembic check: no new upgrade operations detected.
Full DB-backed suite: 1105 passed in 48.41s.
Ruff: passed.
Architecture inspection: valid, violation_count=0.
Capability contracts: valid, facade_count=6, function_count=110.
Architecture quality summary: hotspot_count=10, max_hotspot_risk_score=687.04.
```

## Evidence Service Split Snapshot

Milestone 3 implemented, verified, and locally committed the first physical
evidence-service split on 2026-05-09.

Files added or updated for the split:

- `app/services/evidence.py`
- `app/services/evidence_common.py`
- `app/services/evidence_records.py`
- `app/services/evidence_search_packages.py`
- `app/services/evidence_search_trace_graph.py`
- `app/services/evidence_search_trace_store.py`
- `tests/unit/test_evidence_search_packages.py`
- `docs/architecture_plan_01.md`
- `docs/agentic_architecture_index.md`
- `docs/agentic_architecture_milestone_audit.md`
- `docs/agentic_architecture_milestone_plan.md`
- `docs/SESSION_HANDOFF.md`

Implemented result:

- Search evidence package assembly, export persistence, trace graph
  persistence, trace integrity, and response assembly moved out of
  `app/services/evidence.py`.
- `app.services.evidence` remains import-compatible for
  `get_search_evidence_package`, `persist_search_evidence_package_export`,
  `export_search_evidence_package`, and
  `get_search_evidence_package_export_trace`.
- Shared trace row/spec helpers now live in `app/services/evidence_common.py`;
  the shared evidence export payload helper lives in
  `app/services/evidence_records.py`.
- `app/services/evidence.py` is now 8,608 lines. The new search-evidence
  modules are 338, 421, and 296 lines.

Focused verification:

```bash
git diff --check
uv run ruff check app tests
uv run pytest -q tests/unit/test_evidence_common.py tests/unit/test_evidence_records.py tests/unit/test_evidence_provenance.py tests/unit/test_evidence_search_packages.py
uv run pytest -q tests/unit/test_search_api.py tests/unit/test_search_service.py tests/unit/test_search_history.py
DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs tests/integration/test_evidence_operator_runs_roundtrip.py
uv run docling-system-architecture-inspect
uv run docling-system-capability-contracts
uv run docling-system-architecture-decisions
uv run docling-system-architecture-quality-report --summary
uv run docling-system-hygiene-check
DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs
```

Results:

```text
Evidence helper tests: 27 passed.
Search API/service/history tests: 70 passed.
Search evidence operator-run roundtrip: 1 passed.
Full DB-backed suite: 1109 passed in 47.48s.
Ruff: passed.
Architecture inspection: valid, violation_count=0.
Capability contracts: valid, facade_count=6, function_count=110.
Architecture decisions: valid, decision_count=9.
Architecture quality summary: hotspot_count=10, max_hotspot_risk_score=687.04.
Hygiene: no ruff, vulture, duplicate-helper, improvement-case, or architecture
findings; inherited file/helper budget debt remains.
```

## Agent Action Registry Split Snapshot

Milestone 4 implemented, verified, and locally committed the first physical
agent-action registry family split on 2026-05-09.

Files added or updated for the split:

- `app/services/agent_task_actions.py`
- `app/services/agent_actions/search_harness.py`
- `tests/unit/test_agent_action_contracts.py`
- `docs/architecture_plan_01.md`
- `docs/agentic_architecture_index.md`
- `docs/agentic_architecture_milestone_audit.md`
- `docs/agentic_architecture_milestone_plan.md`
- `docs/SESSION_HANDOFF.md`

Implemented result:

- Search-harness action contract metadata and helper logic moved into
  `app/services/agent_actions/search_harness.py`.
- `app.services.agent_task_actions` remains the public action registry facade
  and execution entrypoint; current executor import paths remain available.
- Covered search-harness action types are
  `optimize_search_harness_from_case`,
  `draft_harness_config_update_from_optimization`, `replay_search_request`,
  `run_search_replay_suite`, `evaluate_search_harness`,
  `verify_search_harness_evaluation`, `draft_harness_config_update`,
  `verify_draft_harness_config`, `triage_replay_regression`, and
  `apply_harness_config_update`.
- `app/services/agent_task_actions.py` is now 2,884 lines; the new
  search-harness registry/helper module is 539 lines.

Focused verification:

```bash
git diff --check
uv run ruff check app tests
uv run pytest -q tests/unit/test_agent_task_actions.py tests/unit/test_agent_action_contracts.py tests/unit/test_agent_tasks_api.py tests/unit/test_agent_tasks.py tests/unit/test_agent_task_worker.py tests/unit/test_agent_task_triage.py
DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs tests/integration/test_agent_task_semantic_orchestration_roundtrip.py tests/integration/test_agent_task_triage_roundtrip.py
uv run docling-system-agent-task-action-index
uv run docling-system-architecture-inspect
uv run docling-system-capability-contracts
uv run docling-system-architecture-decisions
uv run docling-system-architecture-quality-report --summary
uv run docling-system-hygiene-check
DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs
```

Results:

```text
Focused agent-action and adjacent agent-task tests: 136 passed.
DB-backed semantic and triage orchestration roundtrips: 9 passed.
Full DB-backed suite: 1110 passed in 48.43s.
Ruff: passed.
Agent task action index: generated successfully.
Architecture inspection: valid, violation_count=0.
Capability contracts: valid, facade_count=6, function_count=110.
Architecture decisions: valid, decision_count=9.
Architecture quality summary: hotspot_count=10, max_hotspot_risk_score=687.04.
Hygiene: no ruff, vulture, improvement-case, or architecture findings;
inherited file/helper budget debt remains.
```

Alignment check:

```text
Architecture probe:
  command: python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown
  result: 3 Python cycle components remain.
  agent_task_actions: 2,884 lines, fan-out 39 local modules, still part of the
  large agent-task cycle component.

Registry composition:
  command: uv run python -c '<import action registry and print counts/modules>'
  result: total_actions=51, search_harness_actions=10,
  executor_modules=['app.services.agent_task_actions'].

Closeout gates:
  git diff --check: passed.
  uv run ruff check app tests: passed.
  uv run pytest -q tests/unit/test_agent_action_contracts.py: 9 passed.
  uv run docling-system-agent-task-action-index: generated successfully.
  uv run docling-system-architecture-inspect: valid, violation_count=0.
  uv run docling-system-capability-contracts: valid, facade_count=6,
  function_count=110.
  uv run docling-system-architecture-decisions: valid, decision_count=9.
  uv run docling-system-architecture-quality-report --summary:
  agent_legibility_average_score=90.0, broad_facade_count=2,
  hotspot_count=10, max_hotspot_risk_score=687.04.
  DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs:
  1110 passed in 49.04s.
```

Milestone 4 should therefore be read as the first search-harness registry/helper
split, not as an executor implementation move. The next action-family split
target is a search-harness executor dependency seam, or a semantic executor
family with more isolated dependencies, before moving executor implementations
out of the compatibility facade.

## CLI Command Group Split Snapshot

Milestone 5 implemented the first `app/cli.py` command-group split on
2026-05-10.

Implemented result:

- Introduced `app/cli_commands/`.
- Moved the improvement-case validate/list/summary/record command
  implementations into `app/cli_commands/improvement_cases.py`.
- Kept the existing console scripts on `app.cli:run_improvement_case_validate`,
  `app.cli:run_improvement_case_list`, `app.cli:run_improvement_case_summary`,
  and `app.cli:run_improvement_case_record`.
- Alignment pass replaced a lint-suppressed import re-export with explicit
  forwarding functions in `app.cli`, so console entrypoints resolve to stable
  `app.cli` callables while implementation logic stays in
  `app/cli_commands/improvement_cases.py`.
- Added parser/help coverage for the moved command group in
  `tests/unit/test_cli.py`.
- Reduced `app/cli.py` from 1,452 lines to 1,283 lines; the new command module
  is 149 lines.

Focused verification:

```bash
uv run ruff check app tests
uv run pytest -q tests/unit/test_cli.py
uv run python -c '<import app.cli and print moved callable modules>'
uv run docling-system-architecture-quality-report --summary
python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown
```

Results:

```text
Ruff: passed.
Focused CLI tests: 55 passed.
Entrypoint compatibility: moved run_improvement_case_* console scripts resolve
through app.cli forwarding functions and preserve their callable names.
Architecture quality summary: agent_legibility_average_score=90.0,
broad_facade_count=2, hotspot_count=10, max_hotspot_risk_score=687.04.
Architecture probe: app/cli.py is 1,283 probe-counted lines and its hotspot
score is 67,999; the remaining Python cycle components are outside this CLI
slice.
Full DB-backed suite: 1111 passed in 49.25s.
```

## Search Core Split Snapshot

Milestone 6 implemented the first `app/services/search.py` core concern split
on 2026-05-10.

Implemented result:

- Added `app/services/search_query_features.py` as the focused owner for
  query-intent classification, tabular-query detection, identifier lookup
  detection, normalized query feature sets, token/phrase coverage helpers, and
  metadata-query token extraction.
- Kept `app.services.search` import-compatible for existing query helper names,
  including `QueryFeatureSet`, `is_tabular_query`, `_classify_query_intent`,
  `_looks_like_identifier_lookup`, `_build_query_feature_set`,
  `_token_coverage`, and `_strong_document_phrase_match`.
- Preserved search API, ranking, metadata-supplement, replay, telemetry, and
  `execute_search` / `search_documents` contracts.
- Added focused compatibility tests in `tests/unit/test_search_query_features.py`.
- Reduced `app/services/search.py` from 3,429 lines to 3,250 lines; the new
  query-feature owner module is 199 lines.
- Reduced the architecture-probe hotspot score for `app/services/search.py`
  from 89,154 to 87,750 while keeping the general architecture-probe cycle
  count at the prior 3 known components. The post-commit score includes the
  Milestone 6 closeout commit itself in the architecture-probe churn window.

Focused verification:

```bash
git diff --check
uv run ruff check app tests
uv run pytest -q tests/unit/test_search_query_features.py tests/unit/test_search_service.py tests/unit/test_search_api.py
uv run pytest -q tests/unit/test_search_history.py tests/unit/test_search_replays.py tests/unit/test_search_release_gate.py
DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs tests/integration/test_search_replays_roundtrip.py tests/integration/test_search_harness_releases.py
uv run docling-system-run-replay-suite --help
uv run docling-system-architecture-inspect
uv run docling-system-capability-contracts
uv run docling-system-architecture-quality-report --summary
python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 12
DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs
```

Results:

```text
Ruff: passed across app and tests.
Search query feature/service/API tests: 70 passed.
Search history/replay/release-gate tests: 20 passed.
DB-backed search replay/release roundtrips: 4 passed.
Replay-suite CLI help: resolved successfully.
Architecture inspection: valid, violation_count=0.
Capability contracts: valid, facade_count=6, function_count=110.
Architecture quality summary: agent_legibility_average_score=90.0,
broad_facade_count=2, hotspot_count=10, max_hotspot_risk_score=687.04.
Architecture probe: app/services/search.py is 3,250 probe-counted lines and
87,750 hotspot score; Python cycle components remain at 3.
Full DB-backed suite: 1114 passed in 48.38s.
```

Alignment closeout:

```text
Focused query-helper compatibility coverage now proves every forwarded
app.services.search query-feature helper resolves to the focused
app.services.search_query_features owner module.
Architecture probe was rerun after the closeout commit and the current
post-commit app/services/search.py hotspot score is 87,750.
Alignment closeout full DB-backed suite: 1114 passed in 49.01s.
```

## Evidence Provenance Split Snapshot

Milestone 7 implemented the second `app/services/evidence.py` concern split on
2026-05-10.

Implemented result:

- Added `app/services/evidence_provenance.py` as the focused owner for technical
  report PROV export constants, PROV entity/activity/relation helpers, relation
  reference validation, immutable export freeze payloads, hash-chain receipts,
  signing, and receipt integrity checks.
- Kept `app.services.evidence` import-compatible for existing PROV export helper
  names, including `_prov_identifier`, `_prov_entity`, `_prov_activity`,
  `_prov_relation`, `_prov_export_integrity_payload`,
  `_frozen_prov_export_payload`, `_frozen_export_sha256`,
  `_frozen_export_receipt`, and `_prov_export_receipt_integrity`.
- Preserved technical-report evidence manifests, evidence traces, PROV export
  artifact kind/path contracts, semantic-governance links, and audit-bundle
  behavior.
- Added focused facade compatibility coverage in
  `tests/unit/test_evidence_provenance.py`.
- Closed the Milestone 7 alignment gap by proving every moved PROV export
  identity alias and constant resolves to `app/services/evidence_provenance.py`,
  and by proving the `app.services.evidence` settings-aware wrappers produce
  the same receipt, frozen payload, signature, and integrity output as the
  owner module.
- Reduced `app/services/evidence.py` from 8,608 lines to 8,261 lines; the new
  PROV export owner module is 467 lines.
- Reduced the post-commit architecture-probe hotspot score for
  `app/services/evidence.py` from 387,360 to 380,006 while keeping the general
  architecture-probe cycle count at the prior 3 known components. The
  post-commit score includes the Milestone 7 closeout commit itself in the
  architecture-probe churn window.

Focused verification:

```bash
uv run pytest -q tests/unit/test_evidence_provenance.py
uv run pytest -q tests/unit/test_evidence_common.py tests/unit/test_evidence_records.py tests/unit/test_evidence_provenance.py tests/unit/test_evidence_search_packages.py tests/unit/test_technical_reports.py
DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs tests/integration/test_technical_report_harness_roundtrip.py
uv run ruff check app tests
uv run docling-system-architecture-inspect
uv run docling-system-capability-contracts
uv run docling-system-architecture-quality-report --summary
uv run docling-system-hygiene-check
python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 12
DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q
```

Results:

```text
Evidence provenance tests: 13 passed.
Focused evidence/technical-report tests: 40 passed.
DB-backed technical-report harness roundtrip: 1 passed.
Ruff: passed across app and tests.
Architecture inspection: valid, violation_count=0.
Capability contracts: valid, facade_count=6, function_count=110.
Architecture quality summary: agent_legibility_average_score=90.0,
broad_facade_count=2, hotspot_count=10, max_hotspot_risk_score=687.04.
Architecture probe: app/services/evidence.py is 8,261 probe-counted lines and
380,006 post-commit hotspot score; Python cycle components remain at 3.
Full DB-backed suite: 1116 passed in 54.37s.
Hygiene: no ruff, improvement-case, or architecture findings; inherited
file/helper budget debt remains. app/services/evidence.py is now 8,261 lines
with 107 private helpers, still above the strict hygiene budget.
```

## Improvement Intake Ratchet Snapshot

Milestone 8 completed the `Architecture Plan 01` improvement-intake ratchet on
2026-05-10.

Implemented result:

- Refreshed `build/architecture-governance/architecture_quality_report.json`
  from the current checkout.
- Strengthened architecture-quality imports so accepted cases carry structured
  owner surfaces, verification commands, and stop conditions.
- Imported 22 architecture-quality candidates into
  `config/improvement_cases.yaml` as open `architecture_governance` cases.
- Confirmed repeat import dedupe: a follow-up dry-run found the same 22
  candidates and skipped all 22 as `already_imported`.
- Added `docs/hotspot_prevention_gate_milestone_plan.md` as the next follow-on
  weakness plan.
- Added `docs/residual_weakness_resolution_milestone_plan.md` as the broader
  follow-on sequence for the remaining weakness set: hotspot prevention, strict
  hygiene ratchets, remaining hotspot splits, agent-task cycle reduction, and
  evaluation-data readiness.
- Refreshed `docs/evaluation_data_readiness.md` after the command reached local
  Postgres and confirmed the empty-baseline data gates.

Results:

```text
Improvement-case importer tests: 97 passed.
Improvement-case import dry-run before import: candidate_count=22,
imported_count=22, skipped_count=0.
Improvement-case import applied: candidate_count=22, imported_count=22,
skipped_count=0.
Improvement-case import dedupe dry-run: candidate_count=22, imported_count=0,
skipped_count=22.
Improvement-case validation: valid=true, issue_count=0.
Improvement-case summary: case_count=23, measured=1, open=22.
Ruff: passed across app and tests.
Architecture inspection: valid, violation_count=0.
Capability contracts: valid, facade_count=6, function_count=110.
Architecture quality summary: agent_legibility_average_score=90.0,
broad_facade_count=2, hotspot_count=10, max_hotspot_risk_score=693.04.
Full DB-backed suite: 1117 passed in 56.57s.
Hygiene: no ruff, improvement-case, or architecture findings; strict
file/helper budget debt remains.
```

## Architecture Milestone Closeout Policy

The architecture plan was revised on 2026-05-09 so each milestone is complete
only after focused verification, cross-milestone gates, affected docs, handoff
updates, scoped staging, and a local commit. Push remains a separate action and
should happen only when explicitly requested.

The revised closeout rule is:

- run focused tests for the moved or guarded contract
- run `git diff --check`, Ruff, architecture inspection, capability contracts,
  and the architecture-quality summary
- run `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs` for DB, API,
  storage, search, evidence, agent-task, worker, or runtime-facing changes
- run Alembic head/current/upgrade/check plus Postgres metadata create-all
  verification for model or migration changes
- update closeout docs before commit: always refresh this handoff and the active
  milestone/status doc, then refresh any other affected durable docs
- stage only the milestone slice and commit locally before starting the next
  milestone

Milestones 1, 2, 3, 4, 5, 6, 7, and 8 satisfy the revised local commit
closeout rule. The first follow-on residual milestone, the hotspot-prevention
gate in `docs/hotspot_prevention_gate_milestone_plan.md`, is complete.

## Residual Weakness Plan Snapshot

New planning artifact:
`docs/residual_weakness_resolution_milestone_plan.md`.

The plan resolves the five remaining closeout weaknesses in this order:

1. lock the refreshed baseline evidence
2. use the implemented hotspot-prevention gate
3. add the implemented strict hygiene budget ratchet
4. continue facade-preserving top-hotspot splits
5. break the large agent-task import-cycle component
6. lift evaluation-data readiness first to regression readiness, then to
   court-grade readiness
7. run residual closeout with all gates and docs refreshed

Refreshed evidence on 2026-05-10:

```text
architecture quality: hotspot_count=10, max_hotspot_risk_score=692.67
architecture probe: 3 Python cycle components; top hotspot app/db/models.py=411800
Milestone 4 sizes: app/db/models.py=5800, app/cli.py=1231, tests/unit/test_cli.py=2210, app/services/evidence.py=8076
hygiene: inherited file/helper budget debt listed with owners; new hygiene regressions none
evaluation-data readiness: regression_ready=true, court_grade_ready=false, failed_gate_count=7
manual reviewed seed corpus: 1 document, 1 table query, 1 chunk query, 1 cross_document query
live_search_gaps replay: query_count=1, passed_count=1, failed_count=0
cross_document_prose_regressions replay: query_count=1, passed_count=1, failed_count=0
```

Milestone 2 result: `config/hygiene_policy.yaml` now records
`ratchet_max_lines` and `ratchet_max_private_helpers` ceilings for every current
strict budget finding. Existing top-hotspot debts link to open improvement
cases, and remaining inherited debt links to
`residual-weakness-milestone-2`. The hygiene CLI prints `inherited budget debt`
and `new hygiene regressions` separately; inherited debt no longer fails the
command, while ratchet growth fails.

Milestone 2 alignment hardening found and closed one intake gap: the hygiene
improvement-case import path initially treated ratcheted inherited debt as new
open candidates. It now filters non-blocking inherited findings from the import
source while preserving blocking regression import behavior. The hygiene tests
also now cover the CLI output boundary for inherited debt versus new
regressions.

Milestone 2 verification:

```text
git diff --check: passed.
uv run pytest -q tests/unit/test_hygiene.py tests/unit/test_improvement_case_intake.py tests/unit/test_architecture_quality.py: 44 passed.
uv run ruff check app tests: passed.
uv run docling-system-hygiene-check: passed; inherited budget debt listed, new hygiene regressions none.
uv run docling-system-hotspot-prevention-check --strict: passed; changed_hotspots=0, blocked=0.
uv run docling-system-architecture-inspect: valid=true, violation_count=0.
uv run docling-system-capability-contracts: valid=true, facade_count=6, function_count=110.
uv run docling-system-architecture-quality-report --summary: hotspot_count=10, max_hotspot_risk_score=693.04.
uv run docling-system-improvement-case-validate: valid=true, issue_count=0.
uv run docling-system-improvement-case-import --source hygiene --dry-run: candidate_count=0.
DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs: 1134 passed.
```

Milestone 3 result: Top Hotspot Split Pack A moved the ingest ORM model domain
and ingest CLI command family behind stable facades:

- `app/db/model_domains/ingest.py` now owns `IngestBatch`, `IngestBatchItem`,
  `Document`, and `DocumentRun`; `app.db.models` re-exports them for public
  import compatibility.
- `app/cli_commands/ingest.py` now owns ingest file, ingest directory, and
  ingest-batch list/show command implementations; `app.cli` keeps explicit
  console-script forwarding functions.
- `tests/unit/test_cli_ingest.py` now owns the ingest CLI tests and verifies the
  console scripts still target `app.cli`.
- `app/cli_commands/common.py` owns shared lazy service lookup to avoid
  duplicate-helper hygiene debt.
- `app/hotspot_prevention_classifier.py` now allows replacement command bodies
  only when the added hunk is forwarding-only, with controlled tests for the
  Milestone 3 multi-line wrapper shape.
- `config/hygiene_policy.yaml` ratchets `app/db/models.py` to 5,800 lines and
  caps `app/cli.py` at 1,231 lines after the split.

Milestone 3 verification before full-suite closeout:

```text
git diff --check: passed.
uv run ruff check app tests: passed.
uv run pytest -q tests/unit/test_db_model_import_compatibility.py: 242 passed.
uv run pytest -q tests/unit/test_cli.py tests/unit/test_cli_ingest.py: 56 passed.
uv run pytest -q tests/unit/test_hotspot_prevention.py: 14 passed.
uv run pytest -q tests/unit/test_hygiene.py: 10 passed.
DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs tests/integration/test_db_model_metadata.py: 22 passed.
uv run --extra dev alembic heads/current: 0076_claim_feedback_replay_src (head).
uv run --extra dev alembic upgrade head: passed.
uv run --extra dev alembic check: no new upgrade operations detected.
uv run docling-system-hotspot-prevention-check --strict: blocked=0.
uv run docling-system-hygiene-check: new hygiene regressions none.
uv run docling-system-architecture-inspect: valid=true, violation_count=0.
uv run docling-system-capability-contracts: valid=true, facade_count=6, function_count=110.
uv run docling-system-architecture-quality-report --summary: hotspot_count=10, max_hotspot_risk_score=692.67.
architecture probe: app/db/models.py=5800 lines, app/db/models.py score=411800,
app/cli.py=1231 lines, app/cli.py score=67705,
tests/unit/test_cli.py=2210 lines, tests/unit/test_cli.py score=103870,
Python cycle components=3.
DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs: 1168 passed in 63.97s.
```

Milestone 4 result: Top Hotspot Split Pack B moved the knowledge-operator run
recording concern and audit summary payload helpers behind stable facades:

- `app/services/evidence_operator_runs.py` now owns
  `record_knowledge_operator_run` plus the private input/output row recorders.
- `app/services/evidence_task_payloads.py` now owns task, artifact,
  verification, immutability-event, and operator-run summary payload helpers.
- `app.services.evidence.record_knowledge_operator_run` remains a public
  compatibility import.
- Search, retrieval-span, and agent-action executor call sites now import the
  focused owner directly where possible.
- `tests/unit/test_evidence_operator_runs.py` covers facade identity, direct
  owner imports, persisted input/output behavior, and missing-session handling.
- `tests/unit/test_evidence_task_payloads.py` covers the moved payload helper
  shapes and hash behavior.
- `config/hygiene_policy.yaml` ratchets `app/services/evidence.py` to 8,076
  lines and 100 private helpers after the split.
- The architecture probe records `app/services/evidence.py` at 8,076 lines and
  379,572 hotspot score; Python cycle components remain at 3.

Milestone 4 verification before full-suite closeout:

```text
uv run ruff check app tests: passed.
uv run pytest -q tests/unit/test_evidence_task_payloads.py tests/unit/test_evidence_operator_runs.py tests/unit/test_search_service.py tests/unit/test_evidence_records.py: 44 passed.
uv run docling-system-hotspot-prevention-check --strict: changed_hotspots=1, added_lines=7, deleted_lines=78, blocked=0, allowed=6.
uv run docling-system-hygiene-check: new hygiene regressions none; app/services/evidence.py ratchet ceiling=8076 lines and 100 private helpers.
uv run docling-system-architecture-inspect: valid=true, violation_count=0.
uv run docling-system-capability-contracts: valid=True, facade_count=6, function_count=110, issues=0.
uv run docling-system-architecture-quality-report --summary: hotspot_count=10, max_hotspot_risk_score=692.67.
architecture probe: app/services/evidence.py=8076 lines, app/services/evidence.py score=379572, Python cycle components=3.
DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs: 1175 passed in 49.92s.
```

Milestone 5 result: Agent-Task Cycle Break added a narrow action lookup seam
and removed the static back edge from context/task services to the executor
registry facade:

- `app/services/agent_task_action_lookup.py` now owns lazy action lookup and
  input/output validation calls for context and task services.
- `app/services/agent_task_context.py`,
  `app/services/agent_task_context_store.py`, and `app/services/agent_tasks.py`
  use the lookup seam instead of statically importing
  `app.services.agent_task_actions`.
- `app.services.agent_task_actions` remains the public executor registry,
  compatibility facade, and worker execution entrypoint.
- `tests/unit/test_agent_task_action_lookup.py` proves public action identity,
  validation defaults, and the static import guard for the context/task owner
  modules.
- The general architecture probe now reports 2 Python cycle components instead
  of 3; the large agent-task import-cycle component is absent.
- `app/services/agent_task_actions.py` still has fan-out 39, so it is
  documented as the action-orchestration entrypoint rather than claimed as
  reduced.

Milestone 5 implementation closeout commit:

```text
c58e940 architecture: complete residual weakness milestone 5 cycle break
```

Milestone 5 verification before full-suite closeout:

```text
uv run pytest -q tests/unit/test_agent_task_action_lookup.py tests/unit/test_agent_action_contracts.py tests/unit/test_agent_task_actions.py tests/unit/test_agent_tasks.py tests/unit/test_agent_task_context.py tests/unit/test_agent_task_worker.py: 125 passed.
DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs tests/integration/test_agent_task_semantic_orchestration_roundtrip.py tests/integration/test_agent_task_triage_roundtrip.py: 9 passed.
uv run docling-system-agent-task-action-index: emitted schema_name=agent_action_index, schema_version=1.0.
uv run ruff check app tests: passed.
uv run docling-system-hygiene-check: ruff regressions none; inherited budget debt unchanged; new hygiene regressions none.
uv run docling-system-hotspot-prevention-check --strict: changed_hotspots=0, blocked=0.
uv run docling-system-architecture-inspect: valid=true, violation_count=0.
uv run docling-system-capability-contracts: valid=true, facade_count=6, function_count=110.
uv run docling-system-architecture-quality-report --summary: hotspot_count=10, max_hotspot_risk_score=692.67.
architecture probe: Python cycle components=2; no large agent-task cycle component; app/services/agent_task_actions.py fan-out=39.
DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs: 1178 passed in 49.53s.
```

## Active Weak Points

- Evaluation-data readiness now passes the regression tier on the live DB, but
  court-grade readiness is still false because the local DB lacks hand-verified
  gold corpus coverage, operator feedback ledgers, technical-report claim
  feedback, governed claim-support hard cases, full replay and harness-source
  coverage, and retrieval-learning materialization.
- The gold-corpus lane is now seeded, not empty: `docs/evaluation_corpus.yaml`
  contains one reviewed document with one table query, one chunk query, and one
  explicit cross-document query. That seed is enough to harden Milestone 6
  replay coverage but still far below the Milestone 7 thresholds.
- Hygiene remains intentionally strict and currently reports oversized modules,
  especially `app/db/models.py`, `app/services/evidence.py`,
  `app/services/audit_bundles.py`, `app/services/claim_support_policy_impacts.py`,
  `app/services/retrieval_learning.py`, and `app/services/search.py`. These
  overages are now ratcheted inherited debt, not tolerated hidden debt; growth
  beyond the recorded ceilings is blocking.
- The platform, ingest, and document-artifacts model-domain splits reduced
  `app/db/models.py` to 5,537 lines, but it remains the top
  architecture-quality hotspot and should not receive additional unrelated ORM
  concerns. The next model split candidate is `retrieval`, but the next
  hotspot-owner milestone is not model work.
- The first three evidence splits reduced `app/services/evidence.py`, but it
  remains a major architecture-quality hotspot. Future evidence splits should
  move one owner concern at a time behind the same compatibility facade.
- The first agent-action registry split reduced
  `app/services/agent_task_actions.py`, and the Milestone 5 lookup seam removed
  its participation in the large agent-task import-cycle component. It remains a
  hotspot and high fan-out action-orchestration entrypoint. Future action-family
  splits should move one owner concern at a time behind the same compatibility
  facade, starting with an executor family whose dependencies are already
  isolated.
- The first two CLI command-group splits reduced `app/cli.py` to 1,231 lines,
  but it remains a public operator hotspot and is not yet a globally thin
  dispatch surface. Future CLI splits should move one command group at a time
  behind explicit `app.cli` forwarding functions and pair each move with help or
  parser coverage.
- The first search-core split reduced `app/services/search.py`, but search
  remains a retrieval-quality hotspot. Future search splits should move one
  coherent concern at a time behind `app.services.search` compatibility names,
  with replay and ranking behavior covered before changing another search
  concern.
- The improvement-case registry now tracks the current architecture-quality
  hotspot candidates, but this records debt after it exists. The prior
  preventative gap is now closed: `docling-system-hotspot-prevention-check
  --strict` blocks new implementation growth in known hotspot files and points
  future work to the configured owner modules. The gate is Milestone 1 in
  `docs/residual_weakness_resolution_milestone_plan.md` and is detailed in
  `docs/hotspot_prevention_gate_milestone_plan.md`.
- Court-grade readiness now passes on the local DB, so the remaining residual
  work is architecture closeout rather than evaluation-data seeding.

## Next Routed Work

`Architecture Plan 01` is complete through Milestone 8, and the Residual
Weakness Plan is now complete through Milestone 8 as well. The prevention gate,
hygiene ratchet, hotspot splits, agent-task cycle break, regression-readiness
build, court-grade readiness build, and closeout alignment pass are all in
place.

New planning artifacts:

- `docs/hotspot_prevention_gate_milestone_plan.md`
- `docs/residual_weakness_resolution_milestone_plan.md`

Recommended next work shape: owner-scoped follow-up rather than another broad
residual-weakness milestone. Keep both prevention gates active:
`docling-system-hotspot-prevention-check --strict` and
`docling-system-hygiene-check`. The next implementation should choose one
governed owner surface at a time from the improvement-case registry or hotspot
list, verify that the same gates stay green, and avoid reopening this plan as
an umbrella milestone unless a new cross-cutting weakness appears.

Current follow-up plan for the main remaining hotspot-owner debt:

- `docs/hotspot_owner_resolution_plan.md`, which sequences
  `app/db/models.py`, `app/services/evidence.py`,
  `app/services/audit_bundles.py`,
  `app/services/claim_support_policy_impacts.py`,
  `app/services/retrieval_learning.py`, and `app/services/search.py`
  into owner-scoped reduction milestones. It also promotes
  `audit_bundles` and `retrieval_learning` from milestone-owned hygiene debt to
  explicit improvement-case ownership before more split work begins.
- Milestone 0 owner bootstrap closed in `33c7855` and is verified:
  `config/improvement_cases.yaml` adds `IC-2112B1ADC5E8` for
  `app/services/audit_bundles.py` and `IC-0D58F1624037` for
  `app/services/retrieval_learning.py`; `config/hygiene_policy.yaml` now routes
  both surfaces through those case IDs. At the Milestone 0 closeout checkpoint,
  `uv run docling-system-improvement-case-summary` reported `case_count=25`,
  `status_counts.open=24`, `status_counts.measured=1`, and
  `measured_case_count=2`.
- Milestone 1 is now the document-artifacts model-domain split. It reduces
  `app/db/models.py` to 5,537 lines and keeps the moved classes importable from
  `app.db.models` while tightening the metadata contract.
- Milestone 2 is now the evidence and audit bundle split pack. It moved the
  technical-report evidence trace concern into
  `app/services/evidence_manifest_traces.py` and the replay-alert corpus
  lineage concern into `app/services/audit_bundle_replay_alert_corpus.py`
  while preserving both public facades.
- Milestone 3 is now the claim-support replay-alert fixture coverage split. It
  moved the replay-alert fixture coverage workflow into
  `app/services/claim_support_replay_alert_promotions.py` and reduced
  `app/services/claim_support_policy_impacts.py` to 2,011 lines.
- Milestone 4 is now the retrieval-learning replay-alert corpus split. It
  moved replay-alert corpus lineage validation, judgment materialization, and
  hard-negative construction into
  `app/services/retrieval_learning_replay_alert_sources.py` and reduced
  `app/services/retrieval_learning.py` to 2,482 lines.
- Milestone 5 is now the search-ranking split. It moved ranking helpers,
  reranking, hybrid-result merging, result rendering, and ranked-result
  utility types into `app/services/search_ranking.py` and reduced
  `app/services/search.py` to 2,851 lines.
- Hotspot Owner Resolution Milestone 6 is now the closeout-and-routing pass. It
  aligned the owner-case registry, docs, and handoff to the committed
  Milestones 1-5 reduction results and confirmed explicit owner routing for all
  six targeted surfaces.
- Next routed owner case at that checkpoint: `IC-F2A8110185EB` /
  `app/db/models.py` continuation.
