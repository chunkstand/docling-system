# CI Release Gate Parity Milestone Plan

Date: 2026-05-14 local / 2026-05-14 UTC
Status: active through Milestone 1 closeout commit `abecfa1` on 2026-05-14
local / 2026-05-15 UTC after
`docs/runtime_health_orchestration_milestone_plan.md`; the runtime-health
dependency is satisfied locally, the repo-owned
`docling-system-release-gate-parity` runner now exists and passes end to end
locally, and Milestone 2 is the next code-changing slice
Owner context: active follow-on for the checked-in CI parity gap across
`.github/workflows/architecture-governance.yml`,
`.github/workflows/release-gate-parity.yml`,
`pyproject.toml`, a new focused release-gate runner surface, `docker-compose.yml`,
`README.md`, `SYSTEM_PLAN.md`, `docs/SESSION_HANDOFF.md`, and
`docs/agentic_architecture_index.md`. Milestone 0 now binds dedicated owner
case `IC-2D8D5BF5A8C4` in `config/improvement_cases.yaml`, and the dependency
stop condition for code-changing work is now cleared locally.

## Local Progress

Milestone 0 is now refreshed locally against the current system state. The routed
handoff and architecture index both confirm that runtime-health Milestone 4 is
now closed locally, the repo-owned runtime-health contract plus Compose smoke
for `api`, `worker`, and `agent-worker` are both proven locally, and
`IC-2D8D5BF5A8C4` still anchors the active CI parity packet. Milestone 1 is
now resolved locally through closeout commit `abecfa1`:
`app/release_gate_cli.py` owns the canonical local release-parity command,
`pyproject.toml` exposes `docling-system-release-gate-parity`, focused unit
coverage proves the runner step list plus compose lifecycle and teardown
behavior, and `uv run docling-system-release-gate-parity` passed end to end
locally before commit. That local runner proof covers Alembic upgrade/current
smoke, the Postgres `Base.metadata.create_all(...)` verification path, bounded
Compose health convergence for `db`, `api`, `worker`, and `agent-worker`, and
the full DB-backed integration suite at `1980 passed`. The remaining scoped
gap is the missing checked-in `.github/workflows/release-gate-parity.yml`
workflow, so Milestone 2 is now the next code-changing slice.
Milestone 0 alignment verification is now green:
`git diff --check` passed,
`uv run docling-system-improvement-case-validate` returned `valid=true`, and
`uv run docling-system-improvement-case-summary` reported
`case_count=38`, `status_counts.open=26`, `status_counts.deployed=11`, and
`status_counts.measured=1`.

## Purpose

Resolve the current release-readiness gap identified in the system review:

- the only checked-in GitHub workflow is
  `.github/workflows/architecture-governance.yml`
- that workflow validates architecture/governance, Ruff, hygiene, and a narrow
  pytest slice only
- the checked-in CI path does not run the full
  `DOCLING_SYSTEM_RUN_INTEGRATION=1` suite
- the checked-in CI path does not run Alembic upgrade/current smoke
- the checked-in CI path does not run the repo's Postgres
  `Base.metadata.create_all(...)` verification path
- the checked-in CI path does not run Compose config or runtime smoke

The scoped problem is not only that one workflow is too small. The repo's real
release gate currently lives partly in durable docs and operator habit instead
of in checked-in merge-blocking automation. That means "GitHub green" is not
yet equivalent to "release green."

This plan resolves that scoped gap end to end by preserving the fast
architecture-governance lane, introducing one repo-owned release-parity runner,
adding one checked-in release-parity workflow, wiring deterministic Compose
runtime smoke into that workflow, and documenting the canonical gate so future
changes cannot silently narrow CI without failing durable checks.

## Current Evidence

Live repo evidence refreshed from the Milestone 1 local runner-contract
closeout before closeout commit `abecfa1` on 2026-05-14 local / 2026-05-15
UTC:

```text
git status -sb
  ## main...origin/main [ahead 64]

find .github/workflows -maxdepth 1 -type f | sort
  .github/workflows/architecture-governance.yml

rg -n "docling-system-release-gate-parity|docling-system-runtime-health" pyproject.toml
  36:docling-system-runtime-health = "app.runtime_health_cli:run"
  37:docling-system-release-gate-parity = "app.release_gate_cli:run"

uv run docling-system-improvement-case-summary
  case_count=38
  status_counts.measured=1
  status_counts.deployed=11
  status_counts.open=26
  oldest_open_case_id=IC-9812A0B138D9

uv run --extra dev python -m pytest -q tests/unit/test_release_gate_cli.py tests/unit/test_runtime_health_cli.py -rs
  8 passed in 0.54s

uv run docling-system-release-gate-parity
  metadata verification: 335 passed in 2.39s
  full DB-backed suite: 1980 passed in 117.71s
  compose smoke: healthy db/api/worker/agent-worker and automatic teardown

wc -l .github/workflows/architecture-governance.yml README.md SYSTEM_PLAN.md docker-compose.yml pyproject.toml app/release_gate_cli.py tests/unit/test_release_gate_cli.py
      81 .github/workflows/architecture-governance.yml
     818 README.md
     930 SYSTEM_PLAN.md
     124 docker-compose.yml
     151 pyproject.toml
     202 app/release_gate_cli.py
     122 tests/unit/test_release_gate_cli.py
```

Repo-current structural evidence:

- `.github/workflows/architecture-governance.yml` currently installs the repo,
  builds the architecture governance report, validates improvement-case intake,
  runs `uv run ruff check`, `docling-system-architecture-inspect`,
  `docling-system-architecture-decisions`,
  `docling-system-capability-contracts`, `docker compose config --quiet`, the
  focused runtime-health pytest slice, focused architecture tests, and
  `docling-system-hygiene-check`.
- No checked-in workflow currently runs:
  `uv run --extra dev alembic upgrade head`,
  `uv run --extra dev alembic current`,
  a repo-owned Postgres `Base.metadata.create_all(...)` verification path,
  bounded Compose runtime smoke, or the full
  `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run --extra dev python -m pytest -q -rs`
  suite.
- `pyproject.toml` already exposes many repo-owned console scripts, including
  `docling-system-runtime-health`; Milestone 1 now adds
  `docling-system-release-gate-parity` as the canonical local release gate
  runner, and that runner now passes end to end locally.
- `README.md` and older milestone closeouts document the heavier local release
  gate, but that gate is not enforced in GitHub Actions today.
- `docs/agentic_architecture_index.md` and `docs/SESSION_HANDOFF.md` now show
  runtime-health resolved locally through Milestone 4 and route this CI plan
  as the next active follow-on rather than a queued packet blocked on Compose
  smoke.
- The runtime-health dependency is now confirmed at the contract level:
  `app/services/runtime_health.py`, `app/runtime_health_cli.py`, and
  `docker-compose.yml` already provide repo-owned health surfaces for `api`,
  `worker`, and `agent-worker`.
- `config/improvement_cases.yaml` now binds `IC-2D8D5BF5A8C4` as the dedicated
  CI-parity owner case. The scoped gap remains open because the checked-in
  workflow set still lacks a release-parity workflow, but the packet no longer
  depends on chat memory or ad hoc shell snippets to identify its local
  release gate owner.

## Goal

Resolve the scoped CI parity gap so that:

- the checked-in workflow set, taken together, proves the same release gate the
  repo currently relies on locally
- GitHub green meaningfully equals release green for the scoped local-stack
  contract
- the fast architecture-governance lane remains intact, but it is no longer the
  only checked-in merge signal
- Alembic smoke, the Postgres `Base.metadata.create_all(...)` path, Compose
  config/runtime smoke, and the full DB-backed integration suite are all
  executed by checked-in CI rather than left to chat memory or operator habit
- the scoped issue is `resolved` only when the same repo-owned release-parity
  runner is used for local closeout and for GitHub Actions

## Non-Goals

- No hosted deployment pipeline or production infrastructure rollout.
- No Kubernetes, Helm, Terraform, or cloud-environment work.
- No broad runtime-health redesign beyond consuming the health contract from the
  stacked runtime-health packet.
- No test weakening, xfail broadening, skip broadening, or substitution of the
  full DB-backed suite with a narrower subset.
- No branch-protection administration outside the repo beyond documenting the
  required check names if those settings are managed elsewhere.
- No secret-management or auth-hardening project in this packet.
- No rewrite of unrelated search, claim-support, evaluations, evidence, or data
  model surfaces.

## Scope

In scope:

- Milestone 0 stacked-state refresh and CI owner-case bootstrap
- one checked-in release-parity workflow in `.github/workflows/`
- one focused repo-owned release gate runner surface instead of long duplicated
  inline workflow bash
- checked-in execution of:
  `uv run ruff check`,
  `uv run docling-system-improvement-case-validate`,
  `uv run --extra dev alembic upgrade head`,
  `uv run --extra dev alembic current`,
  the repo-owned Postgres `Base.metadata.create_all(...)` verification path,
  `docker compose config --quiet`,
  bounded Compose runtime smoke for `db`, `api`, `worker`, and `agent-worker`,
  and the full
  `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run --extra dev python -m pytest -q -rs`
  suite
- failure-artifact capture for workflow diagnosis:
  `docker compose ps`, health state, and targeted service logs on failure
- README, system-plan, plan, architecture-index, and handoff updates in the
  same closeout commit

Out of scope:

- replacing the existing architecture-governance workflow with one giant mixed
  workflow
- requiring external services beyond the repo's own local stack
- moving architecture-report generation into the release-parity runner
- solving unrelated production-readiness gaps such as secret defaults, TLS,
  backup policy, or multi-node orchestration

## Owner Surfaces

- existing fast governance workflow:
  `.github/workflows/architecture-governance.yml`
- new checked-in release-parity workflow:
  `.github/workflows/release-gate-parity.yml`
- focused release-gate runner:
  `app/release_gate_cli.py` and `pyproject.toml`
- existing CLI/runtime helpers consumed by the runner:
  `app/cli.py`,
  `app/api/main.py`,
  `app/workers/poller.py`,
  `app/workers/agent_poller.py`
- Compose/runtime surface:
  `docker-compose.yml`
- DB metadata verification surface:
  `tests/integration/conftest.py`,
  `tests/integration/test_db_model_metadata.py`
- runtime smoke dependency surfaces from the stacked health packet:
  `app/api/routers/system.py`,
  `app/services/runtime.py`,
  `app/services/runtime_health.py`
- documentation and routing surfaces:
  `README.md`,
  `SYSTEM_PLAN.md`,
  `docs/agentic_architecture_index.md`,
  `docs/SESSION_HANDOFF.md`,
  and this plan

## Placement Rules

- Do not hide the release-parity contract inside large inline GitHub Actions
  shell blocks. The workflow must call one repo-owned runner surface.
- Do not append more orchestration debt to `app/cli.py` if a focused
  `app/release_gate_cli.py` owner can hold the new command cleanly.
- Keep the architecture-governance workflow as a fast signal. The missing
  runtime and DB parity work belongs in a second checked-in workflow unless
  Milestone 0 refresh proves a different layout is materially better.
- Compose smoke must consume repo-owned health behavior and bounded polling;
  do not rely on bare `sleep 30` as the only readiness strategy.
- Do not solve this gap by silently removing slow tests, reducing integration
  coverage, or redefining release green downward.

## Weak-Point Prevention Contract

Freshness check: Milestone 0 must rerun live routing, workflow, and release-gate
commands after the currently stacked packets close. This plan is invalid if the
prior packets remain uncommitted or if they already move the targeted runtime
and CI owner surfaces into different shapes.

| Weak point forecast | Owner surface | Prevention gate | Fail threshold | Controlled violation | Future-Codex misuse scenario |
| --- | --- | --- | --- | --- | --- |
| GitHub goes green only because CI coverage was narrowed rather than made equivalent to the local release gate | `.github/workflows/release-gate-parity.yml`, `app/release_gate_cli.py`, `README.md`, this plan | Local invocation of the repo-owned release-parity runner plus full `DOCLING_SYSTEM_RUN_INTEGRATION=1` closeout verification | Any required local release-gate command is omitted from checked-in CI, or full integration is replaced with a subset/skip/xfail expansion | Temporarily comment out the full integration step or swap in a focused subset and confirm plan review rejects the workflow | A later session speeds up CI by removing the DB-backed suite and claims parity because the workflow still says "release" |
| CI and local release commands drift because they are duplicated across YAML, docs, and chat memory | `app/release_gate_cli.py`, `pyproject.toml`, `.github/workflows/release-gate-parity.yml`, `README.md` | Workflow readback plus runner unit coverage if the runner has argument logic | The workflow runs commands that the local closeout docs do not, or local closeout requires commands the workflow never calls | Rename the runner or move one command back into inline YAML and confirm the workflow/readback no longer matches the docs | A future session updates README verification instructions but forgets the workflow because the command list is duplicated by hand |
| Compose smoke passes configuration but does not prove long-running services become healthy | `docker-compose.yml`, `app/release_gate_cli.py`, runtime-health surfaces | `docker compose config --quiet` plus bounded runtime smoke and health-state assertions for `api`, `worker`, and `agent-worker` | Services start but never reach healthy state, or the smoke step never checks health status at all | Stop one service or force one healthcheck to fail and confirm the smoke runner exits non-zero | A future session adds `docker compose up -d` to CI and treats container startup as equivalent to stack health |
| Alembic appears green while upgrade/current drift or the Postgres metadata path is untested | `pyproject.toml`, `app/release_gate_cli.py`, `tests/integration/test_db_model_metadata.py` | `uv run --extra dev alembic upgrade head`, `uv run --extra dev alembic current`, and the repo-owned `Base.metadata.create_all(...)` verification path | Migration upgrade succeeds but current-head drift or metadata-create path is not exercised in checked-in CI | Skip `alembic current` or the metadata verification path and confirm the parity runner no longer matches the required contract | A later session changes schema code and relies on the full suite alone, even though the metadata path was a separate known risk |
| This stacked plan is implemented against stale repo state after the queued packets land | this plan, `docs/SESSION_HANDOFF.md`, `docs/agentic_architecture_index.md`, `config/improvement_cases.yaml` | Milestone 0 freshness rerun plus manual readback before implementation | Prior stacked packets are still open, or runtime-health semantics changed, or a CI-parity owner case already exists with conflicting scope | Refresh evidence after the earlier packets close; if owner surfaces or dependency assumptions moved, update or stop instead of implementing stale steps | A future session starts coding from this draft without checking whether the runtime-health packet already changed the required smoke contract |

## Milestone Sequence

### Milestone 0 - Refresh the stacked packet and bind the owner case

Outcome label: `reduced`

Current local state: refreshed locally. `IC-2D8D5BF5A8C4` now anchors the
queued CI parity gap, the runtime-health dependency is confirmed against the
repo-owned health contract surfaces, and the scoped CI gap still exists. The
runtime-health dependency is now satisfied at the repo-owned contract and
Compose-smoke level, and Milestone 1 is now implemented locally through the
repo-owned release-parity runner. Milestone 2 is the next active slice.

Purpose: refresh this plan to the current post-stack checkout, confirm that
runtime-health is now the only remaining dependency, and bind the CI parity gap
to a durable owner case before code changes begin.

Implementation:

- Re-run:
  `git status -sb`,
  `sed -n '1,220p' docs/SESSION_HANDOFF.md`,
  `sed -n '1,220p' docs/agentic_architecture_index.md`,
  `find .github/workflows -maxdepth 1 -type f | sort`,
  `sed -n '1,220p' .github/workflows/architecture-governance.yml`,
  `uv run docling-system-improvement-case-summary`,
  and targeted searches for the current runtime-health and release-gate command
  surfaces.
- Confirm the earlier stacked packets remain closed locally and that the CI
  parity gap still exists on the refreshed checkout.
- Confirm whether the runtime-health packet landed with the expected Compose
  health contract for `api`, `worker`, and `agent-worker`.
- If no dedicated CI-parity improvement case exists, create one in
  `config/improvement_cases.yaml` with refreshed owner surfaces, observed
  failure, and this plan as the queued implementation brief. If the case
  already exists, verify that its owner surfaces, failure text, and queued
  verification commands still match the refreshed packet.
- Refresh the evidence block, owner context, dependency assumptions, and queued
  workflow name in this file before touching code.

Acceptance:

- This plan reflects live post-stack repo state rather than the draft-time
  snapshot.
- The runtime-health dependency is either confirmed or explicitly rerouted in
  this plan.
- A dedicated CI-parity owner case exists or an already-existing case is
  explicitly bound to this plan.
- The refreshed plan says whether the scoped issue remains open, has narrowed,
  or has already been resolved by prior packets.

Stop conditions:

- The runtime-health packet remains uncommitted and its blocker cannot be
  isolated cleanly from this queued follow-on.
- The runtime-health packet lands with materially different healthcheck or
  smoke expectations and the plan cannot be reconciled safely.
- Another newly landed plan or owner case already governs the same CI parity
  scope.

### Milestone 1 - Define the canonical repo-owned release-parity runner

Outcome label: `reduced`

Purpose: define the release-gate contract in one repo-owned surface before
workflow wiring so future changes cannot silently reintroduce YAML-only drift.

Current local state: resolved locally through closeout commit `abecfa1`.
`app/release_gate_cli.py` now owns the canonical release-parity runner,
`pyproject.toml` exposes `docling-system-release-gate-parity`, focused runner
coverage exists in `tests/unit/test_release_gate_cli.py`, and
`uv run docling-system-release-gate-parity` now passes end to end locally.
The next remaining scoped gap is the missing checked-in GitHub Actions
workflow.

Implementation:

- Add a focused `app/release_gate_cli.py` owner and expose a new
  `docling-system-release-gate-parity` command in `pyproject.toml`.
- Keep the command narrow and explicit: it should orchestrate the required
  release-parity substeps rather than hiding side effects behind vague modes.
- Include substeps for:
  `uv run ruff check`,
  `uv run docling-system-improvement-case-validate`,
  `uv run --extra dev alembic upgrade head`,
  `uv run --extra dev alembic current`,
  the repo-owned Postgres `Base.metadata.create_all(...)` verification path,
  `docker compose config --quiet`,
  bounded Compose runtime smoke,
  and the full
  `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run --extra dev python -m pytest -q -rs`
  suite.
- Add focused unit coverage for runner argument/step selection in
  `tests/unit/test_release_gate_cli.py` if the runner carries branching logic.
- Record the exact canonical command form in `README.md` and this plan.

Acceptance:

- The release gate lives in one repo-owned runner rather than in duplicated
  ad hoc YAML commands.
- The runner's command list matches the repo's required local release gate.
- Focused tests or readback coverage prove the runner fails if required steps
  are omitted or renamed.

Stop conditions:

- The only workable design would move substantial new orchestration debt into
  the already-large `app/cli.py`.
- The runner depends on external infrastructure beyond the repo's local stack.

### Milestone 2 - Add the checked-in GitHub Actions parity workflow

Outcome label: `reduced`

Purpose: add the missing checked-in merge signal so the repo no longer depends
on local-only release verification for runtime and DB readiness.

Implementation:

- Add `.github/workflows/release-gate-parity.yml`.
- Trigger it on `pull_request` and on `push` to `main`.
- Set up Python and `uv` consistently with the existing workflow.
- Start the local stack needed for release smoke and call the repo-owned
  `docling-system-release-gate-parity` command instead of duplicating the
  release steps inline.
- Upload bounded failure artifacts:
  `docker compose ps`,
  health-state output,
  and targeted service logs on failure.
- Keep the architecture-governance workflow in place. The release-parity
  workflow is additive and closes the missing runtime/DB gate.

Acceptance:

- A checked-in workflow exists for the missing release-parity gate.
- The workflow uses the repo-owned runner rather than an independent command
  list.
- A pull request can become fully green only when both the fast governance lane
  and the release-parity lane pass.

Stop conditions:

- The workflow cannot run deterministically in GitHub-hosted runners with the
  repo's local stack.
- Required failure artifacts cannot be captured without turning the workflow
  into an unreadable monolith.

### Milestone 3 - Prove deterministic Compose and DB smoke inside the parity gate

Outcome label: `reduced`

Purpose: ensure the new workflow proves actual release readiness rather than
only static config validity.

Implementation:

- Wire the release-parity runner so it performs bounded Compose startup and
  health polling for `db`, `api`, `worker`, and `agent-worker`.
- Consume the runtime-health packet's repo-owned health contract for the API,
  worker, and agent-worker checks instead of inventing a second smoke path.
- Reuse the repo's existing Postgres metadata verification surface so the
  `Base.metadata.create_all(...)` path is executed in CI, not just documented.
- Fail fast when health does not converge inside a bounded timeout, then emit
  the targeted failure artifacts captured by the workflow.
- Keep smoke behavior deterministic: no unbounded retries, no silent fallback to
  success, and no "config-only" pass condition.

Acceptance:

- The parity gate proves both DB migration/currentness and long-running service
  health.
- A failed healthcheck or metadata-path regression makes the runner exit
  non-zero.
- The workflow captures enough bounded evidence to diagnose failure without
  rerunning the job locally first.

Stop conditions:

- The runtime-health dependency is not yet landed and no equivalent repo-owned
  health contract exists.
- Compose smoke depends on machine-local assumptions that cannot be reproduced
  in GitHub-hosted CI.

### Milestone 4 - Align docs, handoff, and closeout proof so GitHub green equals release green

Outcome label: `resolved` for the scoped CI release-parity issue

Purpose: prove the new CI surface matches the repo's release gate and close the
milestone with the required durable documentation and local atomic commit.

Implementation:

- Run the full required verification stack locally, using the same
  `docling-system-release-gate-parity` command the workflow uses.
- Update `README.md`, `SYSTEM_PLAN.md`,
  `docs/agentic_architecture_index.md`, `docs/SESSION_HANDOFF.md`, and this
  plan with the final command contract, workflow name, failure-artifact
  behavior, residual risks, and closeout commit hash.
- Record any out-of-repo branch-protection follow-up as a documented manual
  operator action if repo settings are managed elsewhere, but do not treat that
  as a substitute for the checked-in workflow itself.
- Close the improvement case or mark it `reduced` only if refreshed live
  evidence still shows a residual outside this scoped gate.

Acceptance:

- The checked-in workflow set now covers the missing runtime and DB release
  gates.
- The same repo-owned runner is used for local closeout and GitHub Actions.
- GitHub green is no longer merely architecture green; it includes the full
  scoped release parity gate.
- Full verification passes without weakening tests or narrowing coverage.
- The milestone closes in one local atomic commit containing implementation,
  tests, workflow updates, docs, plan closeout, and handoff updates for this
  slice only.

Stop conditions:

- Local closeout cannot run the same command the workflow runs.
- Required docs, plan closeout, or handoff updates cannot be aligned cleanly
  with the implementation slice.

## Required Implementation Artifacts

- `.github/workflows/release-gate-parity.yml`
- updated `.github/workflows/architecture-governance.yml` only if coordination
  or naming alignment is required
- `app/release_gate_cli.py`
- updated `pyproject.toml`
- `tests/unit/test_release_gate_cli.py` if the runner exposes branching logic
- updated `README.md`
- updated `SYSTEM_PLAN.md`
- updated `docs/agentic_architecture_index.md`
- updated `docs/SESSION_HANDOFF.md`
- this plan
- `config/improvement_cases.yaml` if Milestone 0 creates or binds the owner
  case during implementation start

## Required Documentation And Handoff Updates

- `README.md`
- `SYSTEM_PLAN.md`
- `docs/agentic_architecture_index.md`
- `docs/SESSION_HANDOFF.md`
- this plan
- `config/improvement_cases.yaml` if the owner case is created or rebound

## Required Verification Gates

- `git diff --check`
- `uv run ruff check app tests`
- `uv run pytest -q tests/unit/test_release_gate_cli.py`
- `uv run docling-system-improvement-case-validate`
- `uv run --extra dev alembic upgrade head`
- `uv run --extra dev alembic current`
- the repo-owned Postgres `Base.metadata.create_all(...)` verification path
- `docker compose config --quiet`
- `uv run docling-system-release-gate-parity`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run --extra dev python -m pytest -q -rs`
- `uv run docling-system-architecture-inspect`
- `uv run docling-system-capability-contracts`
- `uv run docling-system-hygiene-check`

If the runner already wraps some of the listed commands, still record the exact
wrapped substeps in `docs/SESSION_HANDOFF.md` at closeout so future sessions can
audit what "release green" meant at the time of the commit.

## Acceptance Criteria

- The plan begins with Milestone 0 freshness because the packet is stacked
  behind already drafted follow-on plans and depends on the runtime-health
  contract.
- A new checked-in release-parity workflow exists and runs on pull requests and
  pushes to `main`.
- The repo has one canonical release-parity runner used both locally and in
  GitHub Actions.
- The parity gate includes Alembic upgrade/current smoke, the Postgres
  `Base.metadata.create_all(...)` verification path, Compose config/runtime
  smoke, and the full DB-backed integration suite.
- Failure artifacts are captured for bounded diagnosis when the parity gate
  fails.
- No tests, skips, xfails, or verification gates are weakened to achieve a
  green result; replacement coverage must be equivalent or broader.
- The milestone closes only after docs, handoff, and the local atomic commit
  all exist.

## Stop Conditions

- The prior stacked plans are not yet closed and committed.
- The runtime-health packet does not land in time or lands with incompatible
  health semantics and no clean reroute.
- GitHub-hosted CI cannot run the required local-stack smoke deterministically
  without an additional infrastructure project.
- Unrelated worktree changes cannot be separated from the CI parity milestone
  slice.

## Local Commit Closeout Policy

- Stage only the verified CI release-parity milestone slice.
- Include the workflow file, runner, docs, plan closeout, handoff updates, and
  any owner-case updates in the same atomic commit.
- Do not close the milestone until the local invocation of the same
  `docling-system-release-gate-parity` command used by CI succeeds.
- If an out-of-repo branch-protection step remains, document it explicitly as a
  residual manual action in `docs/SESSION_HANDOFF.md` instead of pretending the
  checked-in repo work is incomplete or fully self-enforcing.
