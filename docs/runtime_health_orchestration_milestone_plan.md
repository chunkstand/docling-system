# Runtime Health Orchestration Milestone Plan

Date: 2026-05-13 local / 2026-05-13 UTC
Status: active stacked follow-on after
`docs/claim_support_policy_impacts_boundary_milestone_plan.md`,
`docs/evaluations_service_boundary_milestone_plan.md`,
`docs/evidence_provenance_exports_boundary_milestone_plan.md`,
`docs/semantics_service_boundary_milestone_plan.md`,
`docs/cli_command_dispatch_boundary_milestone_plan.md`,
`docs/agent_task_schema_aggregation_boundary_milestone_plan.md`,
`docs/oversized_test_hotspots_boundary_milestone_plan.md`,
`docs/hygiene_owner_case_routing_boundary_milestone_plan.md`, and
`docs/architecture_governance_cycle_boundary_milestone_plan.md`; those prior
packets are now closed locally, including architecture-governance closeout
commit `7a4c5b0`, and Milestone 0 refresh / owner-case bootstrap is now
committed locally as checkpoint `289f15a` through `IC-0F89DBB1CF9F`.
Milestone 1 gate-first health contract is now resolved locally in the current
worktree. Milestone 2 hardened API and authenticated runtime-health behavior
is now the next active slice
Owner context: active follow-on for the production-orchestration health gap
across `app/api/routers/system.py`, `app/services/runtime.py`,
`app/workers/poller.py`, `app/workers/agent_poller.py`, and
`docker-compose.yml`. `IC-0F89DBB1CF9F` now anchors the runtime-health
contract gap across those surfaces. `app/services/runtime_health.py` now owns
the shared gate-first health contract, but authenticated detailed diagnostics,
process-heartbeat publication, and Compose healthchecks remain unimplemented.

## Local Progress

Milestone 0 is committed locally as checkpoint `289f15a`. Milestone 1 is now
resolved locally in the current worktree: `app/services/runtime_health.py`
owns the shared health contract at `256` lines, the
`system_governance` capability now exposes the bounded public health seam at
`64` lines, `GET /health` now delegates to that seam and returns only bounded
`{"status":"ok"}` / `{"status":"error"}` payloads, and the checked-in
architecture workflow now runs `docker compose config --quiet` plus a focused
runtime-health pytest slice. The current health-contract surfaces now measure
`88 / 198 / 256 / 64 / 329 / 64 / 113 / 81` lines for
`app/api/routers/system.py`, `app/services/runtime.py`,
`app/services/runtime_health.py`,
`app/services/capabilities/system_governance.py`,
`tests/unit/test_health.py`, `tests/unit/test_runtime_service.py`,
`tests/unit/test_runtime_health.py`, and
`.github/workflows/architecture-governance.yml`. Milestone 2 hardened API and
authenticated runtime-health behavior is now the next active code-changing
slice.

## Purpose

Resolve the current production-orchestration health gap identified in the
system review:

- `GET /health` is a static success response and cannot fail when critical
  runtime dependencies are broken
- Compose uses only the API `/health` probe for API liveness/readiness
- `worker` and `agent-worker` have no healthchecks at all
- the runtime registry tracks startup fingerprint registration but not ongoing
  per-process heartbeat freshness

The scoped problem is not only that one endpoint is too simple. The system
lacks a single repo-owned health contract that can be reused by:

- the public API liveness surface
- authenticated runtime diagnostics
- worker and agent-worker process checks
- Docker Compose healthchecks
- future CI and operator runbooks

This plan resolves that scoped gap end to end by adding one shared runtime
health owner, one repo-owned process health CLI, process-heartbeat freshness
for API and workers, and Compose healthchecks for all long-running services,
while explicitly forbidding a broad auth redesign, deployment-platform rewrite,
or public leak of detailed runtime internals.

## Current Evidence

Milestone 0 baseline evidence refreshed from the current local checkout on
2026-05-14 local / 2026-05-14 UTC before the owner-case bootstrap:

```text
git status -sb
  ## main...origin/main [ahead 58]

uv run docling-system-improvement-case-summary
  case_count=36
  status_counts.open=25
  status_counts.deployed=10
  status_counts.measured=1

uv run docling-system-architecture-quality-report --summary
  agent_legibility_average_score=90.0
  broad_facade_count=2
  hotspot_count=10
  max_hotspot_risk_score=501.06
  top_hotspot_paths=[app/db/models.py, app/services/agent_task_actions.py, app/cli.py, app/schemas/agent_tasks.py, app/services/evidence.py]

wc -l app/api/routers/system.py app/services/runtime.py app/workers/poller.py app/workers/agent_poller.py tests/unit/test_health.py docker-compose.yml
    85 app/api/routers/system.py
   194 app/services/runtime.py
    15 app/workers/poller.py
    15 app/workers/agent_poller.py
   307 tests/unit/test_health.py
   110 docker-compose.yml
   726 total

rg -n "runtime-health|runtime health|app/services/runtime.py|app/api/routers/system.py|poller.py|agent_poller.py" config/improvement_cases.yaml config/hygiene_policy.yaml
  no hits
```

Repo-current structural evidence:

- `docs/agentic_architecture_index.md` and `docs/SESSION_HANDOFF.md` now both
  route runtime-health as the next active packet after architecture-governance
  closeout commit `7a4c5b0`. Milestone 0 is closed, Milestone 1 is now
  resolved locally in the current worktree, and Milestone 2 is the next active
  slice.
- `app/api/routers/system.py` currently serves a public `GET /health` route
  backed by `system_governance.get_public_health()` and a gated
  `GET /runtime/status` route. The public route is now bounded and can fail on
  critical runtime-currentness, DB, storage, or registry failures without
  leaking internal diagnostics, but `/runtime/status` does not yet expose the
  shared health report.
- `tests/unit/test_health.py` now proves the public health route stays bounded
  on both success and failure while preserving `/runtime/status`
  auth/metadata behavior, and `tests/unit/test_runtime_health.py` now covers
  stale code fingerprints, DB/storage probe failures, and process-heartbeat
  expiry against the shared owner module.
- `app/services/runtime.py` currently owns startup fingerprint registration and
  registry reads, and now exposes `get_runtime_registry()` so the shared health
  owner can evaluate the registry contract. It still does not record ongoing
  heartbeat timestamps.
- `app/workers/poller.py` and `app/workers/agent_poller.py` are thin launchers.
  Health ownership currently lives deeper in run and agent-task worker loops,
  but those loops only reason about task/run lease heartbeats, not whole-process
  runtime health.
- `docker-compose.yml` currently gives `db` and `api` healthchecks but no
  healthchecks for `worker` or `agent-worker`. The `api` healthcheck probes
  only `http://127.0.0.1:8000/health`.
- `README.md` documents that Compose publishes the API, keeps `GET /health`
  public, and now documents the bounded `ok` / `error` public health contract.
  It does not yet document a worker health contract or a repo-owned health CLI.
- `docs/architecture_boundaries.md` says the only public remote exemptions are
  `/` and `/health`, and now also states that `/health` must remain a bounded
  contract while detailed runtime diagnostics stay behind `system:read`.
- The only checked-in GitHub workflow is
  `.github/workflows/architecture-governance.yml`. It now validates
  `docker compose config --quiet` plus a focused runtime-health pytest slice in
  addition to the prior architecture/governance checks.
- Milestone 0 created `IC-0F89DBB1CF9F` in `config/improvement_cases.yaml` as
  the durable owner-case anchor for this packet. No hygiene-policy changes were
  needed because the scoped surfaces are not currently budget-ratcheted
  inherited debt.

## Goal

Resolve the scoped runtime-health orchestration gap so that:

- `/health` is no longer a static unconditional success route; it becomes a
  bounded public health contract that can fail on critical runtime-health
  failures without leaking internal details.
- detailed runtime-health diagnostics are available only through existing
  authenticated system-governance surfaces rather than through a new public
  exemption.
- the API, worker, and agent-worker each publish fresh process-heartbeat state
  through the runtime registry.
- Compose has real healthchecks for `api`, `worker`, and `agent-worker`, all
  driven by repo-owned health logic instead of ad hoc inline probing.
- the scoped issue is `resolved` only when a broken DB/storage/runtime-current
  condition can make the relevant service health fail, and when all three
  long-running Compose services have healthchecks wired to that contract.

## Non-Goals

- No broad deployment-platform rewrite beyond the checked-in Compose stack.
- No auth-model redesign beyond the minimum needed to preserve existing
  `system:read` gating or public `/health` semantics.
- No new public remote route exemption besides the already-allowed `/health`.
- No DB schema or Alembic migration change for process health.
- No observability-platform or metrics overhaul.
- No rewrite of document-run or agent-task lease logic beyond the minimal
  process-heartbeat hooks needed for runtime health.
- No attempt to solve unrelated production-readiness gaps such as secret
  defaults, external TLS, backups, or multi-node orchestration in this packet.

## Scope

In scope:

- Milestone 0 stacked-state refresh and runtime-health owner-case bootstrap
- one shared runtime-health owner module:
  `app/services/runtime_health.py`
- one repo-owned process-health CLI entrypoint for Compose healthchecks
- process-heartbeat freshness in the runtime registry for API, worker, and
  agent-worker
- public `/health` contract hardening
- authenticated runtime-diagnostic enrichment through existing system-governance
  surfaces
- Compose healthchecks for `api`, `worker`, and `agent-worker`
- focused unit coverage for runtime-health and worker/API heartbeat freshness
- Compose config verification and targeted CI/runtime gate updates
- README, system-plan, architecture-boundary, plan, and handoff updates in the
  same closeout commit

Out of scope:

- introducing Kubernetes-specific probes or platform-specific deployment files
- adding another public `/ready` or `/livez` route family
- storing process health in Postgres
- redesigning API capability taxonomy
- changing search, claim-support, evaluations, or evidence behavior outside the
  shared runtime-health contract

## Owner Surfaces

- API/system route surface:
  `app/api/routers/system.py`
- system-governance capability surface:
  `app/services/capabilities/system_governance.py`,
  `app/services/capabilities/__init__.py`
- runtime registry primitives:
  `app/services/runtime.py`
- new shared health owner:
  `app/services/runtime_health.py`
- worker loop/process surfaces:
  `app/workers/poller.py`,
  `app/workers/agent_poller.py`,
  `app/services/runs.py`,
  `app/services/agent_task_worker.py`
- CLI and packaging surfaces:
  `pyproject.toml`,
  the new runtime-health CLI module
- Compose/runtime config:
  `docker-compose.yml`
- architecture/route contracts:
  `docs/architecture_boundaries.md`,
  `tests/unit/test_api_route_contracts.py`,
  `tests/unit/test_api_architecture.py`
- health/runtime tests:
  `tests/unit/test_health.py`,
  `tests/unit/test_runtime_service.py`,
  `tests/unit/test_runtime_health.py`,
  `tests/unit/test_run_logic.py`,
  `tests/unit/test_agent_task_worker.py`
- verification/doc surfaces:
  `.github/workflows/architecture-governance.yml`,
  `README.md`,
  `SYSTEM_PLAN.md`,
  `docs/SESSION_HANDOFF.md`,
  `docs/agentic_architecture_index.md`,
  and this plan

## Placement Rules

- Shared runtime-health evaluation logic belongs in
  `app/services/runtime_health.py` and nowhere else.
- `app/services/runtime.py` remains the low-level runtime-registry and
  fingerprint owner; do not turn it into a second mixed-responsibility health
  module.
- If a new CLI is required for Compose healthchecks, it must be a single
  repo-owned command exposed through `pyproject.toml`; do not hide health logic
  inside long inline `python -c` or shell fragments in `docker-compose.yml`.
- Keep `/health` as the only public remote health exemption. If detailed health
  diagnostics are added, they must flow through the existing gated
  system-governance surface, preferably by enriching `/runtime/status` instead
  of minting a new public route.
- Process-heartbeat freshness should live in the runtime registry under
  `storage/runtime/`, not in new database tables or migrations.
- Compose healthchecks must consume the shared runtime-health contract for all
  long-running services; do not let API, worker, and agent-worker drift into
  three separate probe implementations.
- Do not solve this gap by weakening tests, lowering route-contract strictness,
  or broadening the public route exemption list.

## Weak-Point Prevention Contract

Freshness check: Milestone 0 must rerun live routing, worktree, and architecture
commands after the currently stacked packets close. This plan is invalid if the
prior packets remain uncommitted or if they already move the targeted health
surfaces into different owners.

| Weak point forecast | Owner surface | Prevention gate | Fail threshold | Controlled violation | Future-Codex misuse scenario |
| --- | --- | --- | --- | --- | --- |
| Public health leaks internal topology, credentials, or detailed runtime state | `app/api/routers/system.py`, `app/services/runtime_health.py`, `tests/unit/test_health.py`, `tests/unit/test_api_route_contracts.py`, `docs/architecture_boundaries.md` | `uv run pytest -q tests/unit/test_health.py tests/unit/test_api_route_contracts.py` | `/health` exposes file paths, fingerprints, principal metadata, capability lists, or detailed process entries, or a new public route exemption is introduced | Temporarily return the full runtime-status payload from `/health` and confirm the health/route tests fail | A later session dumps `runtime/status` internals into the public health endpoint because it is convenient |
| Worker or agent-worker still appears healthy while its process loop is wedged or stale | `app/services/runtime.py`, `app/services/runtime_health.py`, `app/services/runs.py`, `app/services/agent_task_worker.py`, `tests/unit/test_runtime_health.py`, `tests/unit/test_run_logic.py`, `tests/unit/test_agent_task_worker.py` | `uv run pytest -q tests/unit/test_runtime_health.py tests/unit/test_run_logic.py tests/unit/test_agent_task_worker.py` | A stale process heartbeat, stale code fingerprint, or missing registration still returns healthy for that process kind | Inject an expired heartbeat timestamp or stale fingerprint into the runtime registry and confirm the health evaluator fails | A later session assumes run/task lease heartbeats are enough and never checks whole-process freshness |
| Public health becomes slow, flaky, or overly broad because it performs expensive diagnostics on every request | `app/services/runtime_health.py`, `app/api/routers/system.py`, focused health tests | `uv run pytest -q tests/unit/test_health.py tests/unit/test_runtime_health.py` | `/health` depends on unbounded scans, broad query loops, or non-critical checks that turn transient noise into hard failure | Simulate a non-critical detail-source failure and confirm the public contract stays bounded while detailed diagnostics carry the richer state | A later session adds evaluation, search, or trace inspection into `/health` because “it’s just one more check” |
| Compose healthchecks drift away from the repo-owned health contract or disappear for worker services | `docker-compose.yml`, the new runtime-health CLI, `.github/workflows/architecture-governance.yml` | `docker compose config --quiet` plus focused health tests and workflow readback | Any long-running service lacks a healthcheck, or Compose references a missing/renamed CLI command | Temporarily remove the worker healthcheck or break the CLI command name and confirm compose config / focused checks fail | A future session updates API health logic but forgets worker probes because they live in separate ad hoc commands |
| This stacked plan executes against stale repo state after earlier queued packets land | this plan, `docs/SESSION_HANDOFF.md`, `docs/agentic_architecture_index.md`, `config/improvement_cases.yaml` | Milestone 0 freshness rerun plus manual readback before implementation | Prior stacked packets are still open, or the targeted health surfaces already moved, or a runtime-health owner case already exists with conflicting scope | Refresh evidence after the prior packets close; if owner surfaces or counts moved, update or stop instead of implementing stale steps | A future session starts implementing from this draft without checking whether search/claim-support/evaluations already changed the starting point |

## Milestone Sequence

### Milestone 0 - Refresh the stacked packet and bind the owner case

Outcome label: `reduced`

Current local state: committed locally as checkpoint `289f15a`. The prior
stacked packets are committed, the runtime-health gap remains open on the
refreshed checkout, and `IC-0F89DBB1CF9F` now binds this packet before code
moves. Milestone 1 gate-first health contract is the next active slice.

Purpose: refresh this plan to current system state after the stacked
prerequisite packets close locally, and bind the runtime-health gap to a
durable owner case before code changes begin.

Implementation:

- Re-run:
  `git status -sb`,
  `sed -n '1,220p' docs/SESSION_HANDOFF.md`,
  `sed -n '1,220p' docs/agentic_architecture_index.md`,
  `uv run docling-system-improvement-case-summary`,
  `uv run docling-system-architecture-quality-report --summary`,
  `wc -l app/api/routers/system.py app/services/runtime.py app/workers/poller.py app/workers/agent_poller.py tests/unit/test_health.py docker-compose.yml`
- Confirm the prior stacked packets are committed and the runtime-health gap is
  still open on the refreshed checkout.
- If no dedicated runtime-health improvement case exists, create one in
  `config/improvement_cases.yaml` with the refreshed owner surfaces, observed
  failure, and this plan as the queued implementation brief.
- Refresh the evidence block, owner context, and stacked-plan assumptions in
  this file before touching code.

Acceptance:

- This plan reflects live post-stack repo state instead of the draft-time
  snapshot.
- A dedicated runtime-health owner case exists or an already-existing case is
  explicitly bound to this plan.
- The refreshed plan says whether the scoped issue remains open, has narrowed,
  or has already been resolved by prior packets.

Stop conditions:

- Any prior stacked packet remains uncommitted.
- Prior packets move the targeted health surfaces into different owners.
- Another newly landed plan or owner case already governs the same runtime
  health scope.

### Milestone 1 - Create the gate-first health contract and controlled violations

Outcome label: `reduced`

Current local state: resolved locally in the current worktree. The shared
runtime-health owner module, bounded public route contract, focused unit
coverage, and checked-in workflow gate are now in place. Authenticated
detailed diagnostics, process-heartbeat publication, and Compose healthchecks
remain for Milestone 2 and Milestone 3.

Purpose: define and enforce the runtime-health contract before broad
implementation so future growth cannot silently reintroduce static or
service-specific ad hoc probes.

Implementation:

- Add `app/services/runtime_health.py` as the shared health owner with
  dependency-injected checks for:
  API currentness, runtime-registry freshness, DB connectivity, storage-root
  availability, and per-process heartbeat freshness.
- Add focused unit coverage in `tests/unit/test_runtime_health.py`.
- Expand `tests/unit/test_health.py` so `/health` proves bounded public output
  and failure-path behavior instead of only asserting a static success.
- If implementation uses a new CLI entrypoint, add packaging/tests for that
  command before Compose wiring.
- Add `docker compose config --quiet` and the focused health test slice to the
  checked-in workflow or another checked-in CI gate so health-regression drift
  is visible before merge.

Acceptance:

- The runtime-health contract exists in one shared owner module.
- Focused tests fail on the controlled violations described in the prevention
  contract.
- Compose config and health-focused CI checks are part of the repo-owned gate,
  not a chat-only instruction.

Stop conditions:

- The health contract requires broad deployment abstractions beyond Compose.
- The only workable gate depends on another public route exemption besides
  `/health`.

### Milestone 2 - Harden API and authenticated runtime-health behavior

Outcome label: `reduced`

Purpose: replace the static API health model with a bounded public contract and
authenticated detailed diagnostics without leaking internal state.

Implementation:

- Wire `app/api/routers/system.py` to the shared runtime-health service.
- Keep `/health` public but make it meaningfully fail on critical health
  failures with a bounded payload and appropriate status code.
- Enrich the existing gated system-governance surface, preferably
  `/runtime/status`, with detailed runtime-health diagnostics instead of
  creating another public health route.
- Preserve route-capability and public-exemption contracts in
  `docs/architecture_boundaries.md` and the route-contract tests.
- Update or add compatibility coverage in `tests/unit/test_api_route_contracts.py`
  and `tests/unit/test_api_architecture.py` if the route contract surface
  changes.

Acceptance:

- `/health` is no longer an unconditional `200 {"status":"ok"}`.
- `/health` stays public and bounded.
- Detailed health diagnostics remain behind existing `system:read` gating.
- Route-capability and public-exemption checks remain green.

Stop conditions:

- Detailed diagnostics can only be exposed by broadening the public exemption
  list.
- The API health contract cannot distinguish critical failure from non-critical
  diagnostic detail.

### Milestone 3 - Add process-heartbeat freshness and Compose healthchecks for all long-running services

Outcome label: `reduced`

Purpose: make API, worker, and agent-worker runtime health observable through
the same repo-owned health contract and turn Compose service state into a real
signal instead of a best-effort process-start proxy.

Implementation:

- Extend `app/services/runtime.py` so runtime registrations can record ongoing
  process heartbeat timestamps and process-kind/state metadata needed by the
  shared health evaluator.
- Update the API lifespan and the worker loops in `app/services/runs.py` and
  `app/services/agent_task_worker.py` so the API, worker, and agent-worker keep
  their runtime heartbeat fresh while the process loop is healthy.
- Add a repo-owned runtime-health CLI command and expose it through
  `pyproject.toml`.
- Wire `docker-compose.yml` so `api`, `worker`, and `agent-worker` all use
  healthchecks driven by the shared runtime-health contract.
- Keep the worker launchers thin; do not push health logic into
  `app/workers/poller.py` or `app/workers/agent_poller.py`.

Acceptance:

- API, worker, and agent-worker each publish fresh runtime-heartbeat state.
- Stale process heartbeat or stale desired fingerprint can fail the relevant
  service health.
- `docker-compose.yml` has healthchecks for all three long-running services.
- Compose healthchecks call repo-owned health logic rather than service-specific
  ad hoc commands.

Stop conditions:

- Process-heartbeat freshness requires a DB migration or a second persistence
  system.
- Compose health depends on fragile container-name assumptions or secret-bearing
  inline commands that cannot be verified cleanly in the repo.

### Milestone 4 - Prove the orchestration gap is closed and align docs/handoff

Outcome label: `resolved` for the scoped runtime-health orchestration issue

Purpose: prove that runtime-health behavior is now end-to-end real rather than
just better-factored code, and close the milestone with the required docs,
handoff, and atomic commit.

Implementation:

- Run the full required verification stack, including focused health tests, the
  full DB-backed suite, architecture/capability/hygiene gates, Compose config,
  and Compose runtime smoke.
- Update `README.md`, `SYSTEM_PLAN.md`, `docs/architecture_boundaries.md`,
  `docs/SESSION_HANDOFF.md`, and this plan with final commands, health
  semantics, closeout commit hash, residual risks, and next routing.
- Update `docs/agentic_architecture_index.md` so the new plan is discoverable
  and its closeout state is durable.

Acceptance:

- All three long-running Compose services have healthchecks and those
  healthchecks are backed by the shared runtime-health contract.
- `/health` can fail on critical runtime-health failures while remaining a
  bounded public route.
- The authenticated runtime-diagnostic surface exposes detailed health state
  without broadening public exemptions.
- Full verification passes without weakening tests or narrowing coverage.
- The milestone closes in one local atomic commit containing implementation,
  tests, docs, workflow/config updates, and handoff updates for this health
  slice only.

Stop conditions:

- Runtime smoke fails for unrelated stack breakage that cannot be separated from
  this milestone.
- Required docs/handoff/index updates cannot be aligned cleanly with the
  implementation slice.

## Required Implementation Artifacts

- `app/services/runtime_health.py`
- runtime-health CLI module and `pyproject.toml` script entry
- updated `app/services/runtime.py`
- updated `app/api/routers/system.py`
- updated `app/services/capabilities/system_governance.py`
- updated `app/services/runs.py` and `app/services/agent_task_worker.py`
- updated `docker-compose.yml`
- updated `.github/workflows/architecture-governance.yml` or another checked-in
  workflow gate
- `tests/unit/test_runtime_health.py`
- updated `tests/unit/test_health.py`
- updated `tests/unit/test_runtime_service.py`
- updated worker-loop focused tests in `tests/unit/test_run_logic.py` and
  `tests/unit/test_agent_task_worker.py`

## Required Documentation And Handoff Updates

- `README.md`
- `SYSTEM_PLAN.md`
- `docs/architecture_boundaries.md`
- `docs/agentic_architecture_index.md`
- `docs/SESSION_HANDOFF.md`
- this plan
- `config/improvement_cases.yaml` if Milestone 0 creates or binds the owner
  case during implementation start

## Required Verification Gates

- `git diff --check`
- `uv run ruff check app/api/routers/system.py app/services/runtime.py app/services/runtime_health.py app/services/capabilities/system_governance.py app/services/runs.py app/services/agent_task_worker.py app/workers/poller.py app/workers/agent_poller.py tests/unit/test_health.py tests/unit/test_runtime_service.py tests/unit/test_runtime_health.py tests/unit/test_run_logic.py tests/unit/test_agent_task_worker.py tests/unit/test_api_route_contracts.py tests/unit/test_api_architecture.py`
- `uv run pytest -q tests/unit/test_health.py tests/unit/test_runtime_service.py tests/unit/test_runtime_health.py tests/unit/test_run_logic.py tests/unit/test_agent_task_worker.py tests/unit/test_api_route_contracts.py tests/unit/test_api_architecture.py`
- `docker compose config --quiet`
- `docker compose up -d db api worker agent-worker`
- `docker inspect "$(docker compose ps -q api)" --format '{{.State.Health.Status}}'`
- `docker inspect "$(docker compose ps -q worker)" --format '{{.State.Health.Status}}'`
- `docker inspect "$(docker compose ps -q agent-worker)" --format '{{.State.Health.Status}}'`
- `uv run docling-system-architecture-inspect`
- `uv run docling-system-architecture-decisions`
- `uv run docling-system-capability-contracts`
- `uv run docling-system-hygiene-check`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run --extra dev python -m pytest -q -rs`

If runtime smoke needs a short wait for health transition, add a bounded polling
step to the closeout commands and record the exact command in
`docs/SESSION_HANDOFF.md`.

## Acceptance Criteria

- The plan begins with Milestone 0 freshness and owner-case binding because the
  packet is stacked behind already drafted implementation plans.
- `/health` is a bounded public contract that can fail on critical runtime
  health issues and does not leak internal diagnostics.
- Detailed runtime-health diagnostics are available only through authenticated
  system-governance surfaces.
- Runtime registry data includes enough freshness state to distinguish stale API
  and worker processes from current ones.
- `api`, `worker`, and `agent-worker` each have Compose healthchecks backed by
  the shared runtime-health contract.
- The repo includes a focused regression gate for this health contract.
- No new public health exemption is introduced beyond `/health`.
- No tests, route contracts, or verification gates are weakened to achieve a
  green result; replacement coverage must be equivalent or broader.
- The milestone closes only after docs, handoff, and the local atomic commit
  all exist.

## Stop Conditions

- The prior stacked plans are not yet closed and committed.
- A runtime-health owner case already exists with materially different scope and
  the routing cannot be reconciled safely.
- The only viable implementation path requires a DB migration, a new deployment
  platform, or a second public health route exemption.
- Compose health behavior cannot be verified with repo-owned commands in a
  deterministic way.
- Unrelated worktree changes cannot be separated from the health milestone
  slice.

## Local Commit Closeout Policy

- Stage only the verified runtime-health milestone slice.
- Leave unrelated dirty or untracked search/orchestration and other stacked-plan
  files alone.
- Include implementation, tests, workflow/config updates, docs, and handoff
  updates that describe the completed health milestone in the same commit.
- Record the closeout commit hash in `docs/SESSION_HANDOFF.md` and this plan.
- Treat the milestone as incomplete until that local atomic commit exists.
- Stop before committing if any required verification gate fails or if the
  runtime-health slice cannot be isolated safely from unrelated worktree state.

## Residual Risks And Next Milestone Routing

- Even after this scoped issue is resolved, broader production hardening still
  remains outside this packet: secret/default tightening, external TLS,
  multi-host orchestration, richer metrics/alerting, and release-CI parity for
  full runtime smoke.
- If this milestone resolves the scoped health gap but leaves wider deployment
  risk open, route the next packet to a dedicated deployment-hardening or
  release-readiness plan rather than broadening this milestone in place.
- If the shared runtime-health owner itself becomes oversized or starts pulling
  unrelated diagnostics into one place, route that as a new owner-scoped follow
  on instead of hiding the debt inside this resolved packet.
