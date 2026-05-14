# CLI Command Dispatch Boundary Milestone Plan

Date: 2026-05-13 local / 2026-05-14 UTC
Status: Milestone 3 is implemented and verified locally in the working tree
after the Milestone 2 closeout `f5a4260`, the Milestone 1 closeout `c674871`,
and the Milestone 0 rebaseline closeout `381ca15`; the closeout commit is
still pending, so Milestone 4 is now the next active CLI closeout slice
Owner context: active bounded follow-on under `IC-9812A0B138D9` /
`app/cli.py`. Milestone 0 refreshed the live post-stack state, Milestone 1
tightened the facade-prevention ratchet, Milestone 2 extracted the runtime and
maintenance command owner, Milestone 3 extracted the retrieval-learning and
search-harness command owner in the working tree, and Milestone 4 is now the
next active closeout step.

## Local Progress

Milestone 3 is implemented and verified locally in the working tree. Milestone
2 remains closed as commit `f5a4260`, Milestone 1 remains closed as commit
`c674871`, Milestone 0 remains closed as commit `381ca15`, the runtime and
maintenance command owner remains in `app/cli_commands/runtime.py`, and
Milestone 4 is now the next active CLI closeout slice.

Local Milestone 3 working-tree snapshot:

- added `app/cli_commands/search_harness.py` as the focused retrieval-learning
  and search-harness owner at `604` lines, covering
  `run_materialize_retrieval_learning_dataset(...)`,
  `run_evaluate_retrieval_learning_candidate(...)`,
  `run_create_retrieval_reranker_artifact(...)`,
  `run_eval_reranker(...)`,
  `run_search_harness_evaluation_list(...)`,
  `run_search_harness_evaluation_show(...)`,
  `run_gate_search_harness_release(...)`,
  `run_search_harness_release_audit_bundle(...)`,
  `run_retrieval_training_run_audit_bundle(...)`,
  `run_audit_bundle_validation_receipt(...)`, and
  `run_optimize_search_harness(...)`
- reduced `app/cli.py` from `926` lines to `375` lines by replacing the
  remaining direct retrieval-learning and search-harness command bodies with
  explicit forwarding wrappers while preserving the stable `app.cli:run_*`
  entrypoint names and the stable service-wrapper monkeypatch seam names
- moved direct owner coverage into `tests/unit/test_cli_search_harness.py` at
  `714` lines, expanded `tests/unit/test_cli_entrypoints.py` to `102` lines
  for the forwarding-dependency contract, and reduced
  `tests/unit/test_cli.py` to an empty compatibility placeholder so the legacy
  hotspot no longer absorbs direct owner assertions
- kept `app/cli_commands/runtime.py` at `463` lines and
  `app/cli_commands/common.py` at `6` lines, so the split stayed within the
  two-owner plan boundary and did not create a generic CLI framework sink
- the live architecture-quality report now measures `app/cli.py` at `375`
  lines, `56` changes over 90 days, and `risk_score 425.5`; the architecture
  probe no longer lists `app/cli.py` in the top 12 churn hotspots, but the
  architecture-quality summary still routes the facade among the top hotspot
  paths so the broader owner case remains reduced/open
- refreshed `config/hygiene_policy.yaml` and `config/improvement_cases.yaml` so
  the CLI facade and both owner modules now carry exact verified local
  ceilings, and `IC-9812A0B138D9` now reflects the Milestone 3 working-tree
  measurements rather than the older `926`-line runtime-only state
- local closeout commit: pending

Local Milestone 3 working-tree verification:

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

Local Milestone 2 snapshot:

- added `app/cli_commands/runtime.py` as the focused runtime and maintenance
  owner at `463` lines, covering `run_eval_run(...)`,
  `run_eval_corpus(...)`, `run_audit(...)`,
  `run_backfill_legacy_audit(...)`, `run_knowledge_base_reset(...)`,
  `run_semantic_backfill_status(...)`, `run_semantic_backfill(...)`,
  `run_replay_search(...)`, `run_eval_candidates(...)`,
  `run_evaluation_data_readiness(...)`, `run_replay_suite(...)`, and
  `run_export_ranking_dataset(...)`
- reduced `app/cli.py` from `1231` lines to `926` lines by replacing the
  extracted runtime command bodies with narrow zero-argument forwarding
  wrappers and preserving the stable `app.cli:run_*` entrypoint names
- moved direct runtime owner coverage into `tests/unit/test_cli_runtime.py`
  at `444` lines, left `tests/unit/test_cli.py` at `106` lines as the legacy
  compatibility surface, and added `tests/unit/test_cli_entrypoints.py` at
  `33` lines for the focused app-cli forwarding contract
- kept `app/cli_commands/common.py` at `6` lines, so the split did not create
  a generic CLI framework sink
- reduced the routed CLI hotspot enough that the architecture probe no longer
  lists `app/cli.py` as the top hotspot; it now measures `55` revisions /
  `926` lines / `score 50930` while the broader owner case remains open
  because `app/cli.py` still appears in the architecture-quality top-hotspot
  routing and still exceeds the default `600`-line budget
- post-closeout alignment ratcheted `app/cli.py` in
  `config/hygiene_policy.yaml` from the stale `1231`-line ceiling down to the
  verified `926`-line seam against the default `600`-line budget, and
  refreshed `IC-9812A0B138D9` so its verification contract now matches the
  implemented Milestone 2 surfaces instead of the queued
  `app/cli_commands/search_harness.py` follow-on. The current architecture
  probe now measures `app/cli.py` at `56` revisions / `926` lines /
  `score 51856`, while strict hotspot-prevention reports `changed_hotspots=0`
- Milestone 3 is now the next routed CLI slice for retrieval-learning and
  search-harness command-owner extraction
- local closeout commit:
  `f5a4260`

Local Milestone 2 verification:

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
- `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 12`: top hotspot is now `tests/unit/test_agent_tasks_api.py`; `app/cli.py` measures `55` revisions / `926` lines / `score 50930`; Python cycle components=`5`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs`: `1932 passed`

Local Milestone 1 snapshot:

- tightened the `app/cli.py` hotspot-prevention rule so the facade now blocks
  new direct session or storage wiring plus direct parser-body or JSON-render
  scaffolding, in addition to the existing command-body and
  `ArgumentParser(...)` guards
- preserved the existing allowed seam for explicit forwarding wrappers and
  parser registration so `app.cli` can keep its compatibility dispatch role
  while command bodies move into `app/cli_commands/*`
- added focused controlled-violation tests proving direct
  `get_session_factory()`, `with session_factory()`, `StorageService()`,
  `parser.add_argument(...)`, `parser.parse_args()`, and `json.dumps(...)`
  growth in `app/cli.py` is now blocked while the forwarding-wrapper pattern
  remains allowed
- refreshed `config/hygiene_policy.yaml` and `config/improvement_cases.yaml`
  for the classifier follow-on case `IC-6C1B516A3F92` after the stricter CLI
  facade gate expanded `app/hotspot_prevention_classifier.py` to `879` lines
- Milestone 2 remains the next routed CLI slice for runtime and maintenance
  command owner extraction
- local closeout commit:
  `c674871`

Local Milestone 1 verification:

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

Local Milestone 0 snapshot:

- confirmed the prior stacked packets are closed locally as commits
  `3d7d090`, `1159297`, `1aa8378`, and `a2eb27e`
- promoted this plan from a queued stacked draft to the current active bounded
  implementation brief, with Milestone 1 as the next code-changing slice
- updated the handoff and architecture index so the active local follow-up now
  routes through `IC-9812A0B138D9` / `app/cli.py`
- refreshed `config/improvement_cases.yaml` and `config/hygiene_policy.yaml`
  so the active CLI owner case, live hotspot evidence, and hygiene routing all
  agree before Milestone 1 begins
- refreshed the live CLI baseline: `app/cli.py` measures `1231` lines by
  `wc -l`, remains the top architecture-probe hotspot at `55` revisions /
  `score 67705`, and the oldest open improvement case remains
  `IC-9812A0B138D9`
- confirmed the existing focused CLI owners remain small:
  `app/cli_commands/ingest.py` at `135` lines,
  `app/cli_commands/improvement_cases.py` at `149` lines, and
  `app/cli_commands/common.py` at `6` lines, so the remaining hotspot is
  still the older direct command-body cluster in `app/cli.py`
- refreshed the Python cycle baseline for the downstream CLI packet to `5`
  components after the stacked closeouts
- local closeout commit:
  `381ca15`

Local Milestone 0 verification:

- `git diff --check`: pass
- `wc -l app/cli.py app/cli_commands/ingest.py app/cli_commands/improvement_cases.py app/cli_commands/common.py tests/unit/test_cli.py tests/unit/test_cli_search_harness.py tests/unit/test_cli_ingest.py app/agent_task_cli.py app/claim_support_replay_cli.py app/improvement_case_intake_cli.py`: refreshed live size baseline
- `uv run docling-system-architecture-quality-report --summary`: `hotspot_count=10`, `max_hotspot_risk_score=501.06`, `top_hotspot_paths` still includes `app/cli.py`
- `uv run docling-system-improvement-case-summary`: `case_count=29`, `status_counts.open=21`, `status_counts.deployed=7`, `status_counts.measured=1`, `oldest_open_case_id=IC-9812A0B138D9`
- `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 12`: `app/cli.py` remains the top hotspot at `55` revisions / `1231` lines / `score 67705`; Python cycle components=`5`

## Purpose

Resolve the oldest open architecture hotspot that remains in `app/cli.py`.

The scoped problem is not only line count. The current CLI facade still repeats
the same command-body scaffolding across many entrypoints:

- `argparse` parser setup
- session-factory and `StorageService` wiring
- typed request construction
- `json.dumps(...)` or `model_dump(...)` rendering
- commit and exit-code flow for release-gate style commands

This plan resolves that scoped knot by turning `app/cli.py` into a narrow
console-script compatibility and dispatch surface, moving the remaining command
bodies into bounded `app/cli_commands/` owner modules, while explicitly
forbidding the work from spilling into a new top-level `app/*_cli.py` sprawl,
into service modules, or into a broad generic CLI framework in
`app/cli_commands/common.py`.

## Current Evidence

Live repo evidence refreshed from the current local checkout on 2026-05-13
local / 2026-05-14 UTC:

```text
git status -sb
  ## main...origin/main [ahead 30]

wc -l app/cli.py app/cli_commands/ingest.py app/cli_commands/improvement_cases.py app/cli_commands/common.py tests/unit/test_cli.py tests/unit/test_cli_search_harness.py tests/unit/test_cli_ingest.py app/agent_task_cli.py app/claim_support_replay_cli.py app/improvement_case_intake_cli.py
  1231 app/cli.py
   135 app/cli_commands/ingest.py
   149 app/cli_commands/improvement_cases.py
     6 app/cli_commands/common.py
   423 tests/unit/test_cli.py
   322 tests/unit/test_cli_search_harness.py
   176 tests/unit/test_cli_ingest.py
   508 app/agent_task_cli.py
   198 app/claim_support_replay_cli.py
    63 app/improvement_case_intake_cli.py

find app/cli_commands -maxdepth 1 -type f | sort
  app/cli_commands/__init__.py
  app/cli_commands/common.py
  app/cli_commands/improvement_cases.py
  app/cli_commands/ingest.py

uv run docling-system-architecture-quality-report --summary
  hotspot_count=10
  max_hotspot_risk_score=501.06
  top_hotspot_paths=[
    app/db/models.py,
    app/services/agent_task_actions.py,
    app/cli.py,
    app/schemas/agent_tasks.py,
    app/services/evidence.py
  ]

uv run docling-system-improvement-case-summary
  case_count=29
  status_counts.measured=1
  status_counts.deployed=7
  status_counts.open=21
  actionable_buckets.oldest_open_case_id=IC-9812A0B138D9

python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 12
  app/cli.py: 55 revisions, 1231 lines, score 67705
  app/cli.py remains the top hotspot in the live probe
  Python cycle components=5
```

Repo-current structural evidence:

- `docs/claim_support_policy_impacts_boundary_milestone_plan.md`,
  `docs/evaluations_service_boundary_milestone_plan.md`,
  `docs/evidence_provenance_exports_boundary_milestone_plan.md`, and
  `docs/semantics_service_boundary_milestone_plan.md` are now all resolved
  locally through closeout commits `3d7d090`, `1159297`, `1aa8378`, and
  `a2eb27e`. Milestone 0 is therefore complete, and this CLI packet is now
  the active bounded implementation brief.
- `app/cli.py` already delegates two bounded command families into
  `app/cli_commands/ingest.py` at `135` lines and
  `app/cli_commands/improvement_cases.py` at `149` lines, while
  `app/cli_commands/common.py` remains a `6` line helper surface. The repo
  also already uses separate CLI owner modules for
  `app/agent_task_cli.py`, `app/claim_support_replay_cli.py`, and
  `app/improvement_case_intake_cli.py`. The residual hotspot is still the
  older direct command-body cluster that lives in `app/cli.py`.
- The repeated direct command-body families still in `app/cli.py` include:
  `run_eval_run(...)`,
  `run_eval_corpus(...)`,
  `run_audit(...)`,
  `run_backfill_legacy_audit(...)`,
  `run_knowledge_base_reset(...)`,
  `run_semantic_backfill_status(...)`,
  `run_semantic_backfill(...)`,
  `run_replay_search(...)`,
  `run_eval_candidates(...)`,
  `run_evaluation_data_readiness(...)`,
  `run_replay_suite(...)`,
  `run_export_ranking_dataset(...)`,
  `run_materialize_retrieval_learning_dataset(...)`,
  `run_evaluate_retrieval_learning_candidate(...)`,
  `run_create_retrieval_reranker_artifact(...)`,
  `run_eval_reranker(...)`,
  `run_search_harness_evaluation_list(...)`,
  `run_search_harness_evaluation_show(...)`,
  `run_gate_search_harness_release(...)`,
  `run_search_harness_release_audit_bundle(...)`,
  `run_retrieval_training_run_audit_bundle(...)`,
  `run_audit_bundle_validation_receipt(...)`, and
  `run_optimize_search_harness(...)`.
- The existing hotspot-prevention classifier already blocks new `def` bodies
  and new `ArgumentParser(...)` additions in `app/cli.py`, and
  `tests/unit/test_hotspot_prevention.py` already proves that explicit keyword
  forwarders are allowed while direct replacement command bodies can be blocked.
  The remaining gap is that the current rule does not explicitly guard against
  new direct session-wiring or JSON-render scaffolding inside the facade.
- `tests/unit/test_cli.py` is already governed as a legacy CLI compatibility
  surface in `config/hotspot_prevention.yaml`, which only allows
  compatibility assertions and deletions there. Direct owner-module coverage
  therefore needs to move into focused test files rather than broadening
  `tests/unit/test_cli.py`.
- The current test and import contracts depend on the `app.cli` names staying
  stable. `tests/unit/test_cli.py`, `tests/unit/test_cli_search_harness.py`,
  and `pyproject.toml` console-script entrypoints still import
  `app.cli:run_*` functions directly, and monkeypatched tests currently patch
  lazy service wrappers such as `list_search_harness_evaluations` and
  `get_search_harness_evaluation_detail`.

## Goal

Resolve the scoped CLI-boundary knot by the end of this stacked plan so that:

- `app/cli.py` becomes a narrow compatibility and dispatch surface rather than
  the owner of parser, session, request-building, and JSON-render logic.
- At most two new owner modules are introduced under `app/cli_commands/`:
  `app/cli_commands/runtime.py` and
  `app/cli_commands/search_harness.py`.
- `app/cli_commands/common.py` may gain only minimal shared helpers; it must
  not become a generic CLI framework or a new hotspot sink.
- Public console-script entrypoints in `pyproject.toml` and stable `app.cli`
  import names remain behavior-stable.
- The scoped issue is `resolved` when the selected repeated
  parser/session/JSON-print scaffolding no longer lives in `app/cli.py`.
- The broader owner case `IC-9812A0B138D9` is `reduced` unless refreshed live
  architecture evidence proves the hotspot is fully retired.

## Non-Goals

- No search, evaluations, evidence, semantics, claim-support, or agent-task
  service refactor in this packet.
- No CLI UX redesign, new command naming, or console-script rename.
- No movement of business logic into CLI modules; services remain the owners of
  runtime behavior.
- No migration of these command families into new top-level `app/*_cli.py`
  modules.
- No attempt to solve the separate agent-task or claim-support CLI families.
- No broad split into more than two new `app/cli_commands/*.py` owner modules.

## Scope

In scope:

- Milestone 0 stacked-state refresh after the claim-support, evaluations,
  evidence provenance-export, and semantics packets close
- hotspot-prevention tightening for `app/cli.py`
- one runtime and maintenance command owner:
  `app/cli_commands/runtime.py`
- one retrieval-learning and search-harness command owner:
  `app/cli_commands/search_harness.py`
- minimal shared helper additions in `app/cli_commands/common.py`
- direct owner-module unit coverage
- compatibility coverage for `app/cli.py` and `pyproject.toml` entrypoints
- hygiene, improvement-case, index, and handoff updates for the narrowed CLI
  facade

Out of scope:

- adding a third new owner module under `app/cli_commands/`
- adding new top-level `app/*_cli.py` wrappers for these command families
- moving request parsing into service modules
- changing console-script names in `pyproject.toml`
- solving the `tests/unit/test_cli.py` hotspot beyond keeping it bounded as a
  compatibility surface

## Owner Surfaces

- compatibility facade:
  `app/cli.py`
- new runtime owner:
  `app/cli_commands/runtime.py`
- new retrieval-learning and search-harness owner:
  `app/cli_commands/search_harness.py`
- shared helper surface:
  `app/cli_commands/common.py`
- importer and compatibility surfaces:
  `pyproject.toml`,
  `tests/unit/test_cli.py`,
  `tests/unit/test_cli_search_harness.py`,
  `tests/unit/test_cli_improvement_cases.py`
- adjacent CLI owners that may be called but must not absorb this debt:
  `app/agent_task_cli.py`,
  `app/claim_support_replay_cli.py`,
  `app/improvement_case_intake_cli.py`,
  `app/improvement_case_lifecycle_cli.py`,
  `app/cli_commands/ingest.py`,
  `app/cli_commands/improvement_cases.py`
- service owners that stay responsible for runtime behavior:
  `app/services/evaluations.py`,
  `app/services/search_replays.py`,
  `app/services/retrieval_learning.py`,
  `app/services/search_harness_evaluations.py`,
  `app/services/search_release_gate.py`,
  `app/services/search_harness_optimization.py`,
  `app/services/semantic_backfill.py`,
  `app/services/evaluation_data_readiness.py`,
  `app/services/knowledge_base_reset.py`,
  `app/services/audit.py`,
  `app/services/cleanup.py`,
  `app/services/audit_bundles.py`
- focused tests:
  `tests/unit/test_cli.py`,
  `tests/unit/test_cli_runtime.py`,
  `tests/unit/test_cli_search_harness.py`,
  `tests/unit/test_hotspot_prevention.py`,
  `tests/unit/test_run_logic.py`
- governance and routing surfaces:
  `config/hotspot_prevention.yaml`,
  `app/hotspot_prevention_classifier.py`,
  `config/hygiene_policy.yaml`,
  `config/improvement_cases.yaml`,
  `docs/agentic_architecture_index.md`,
  `docs/SESSION_HANDOFF.md`,
  and this plan

## Placement Rules

- `app/cli.py` remains the stable console-script compatibility surface. It may
  contain only:
  import forwarders,
  lazy service wrapper names needed for compatibility and monkeypatching,
  explicit forwarding functions into `app/cli_commands/`,
  and deletion-only cleanup.
- Direct `argparse` setup, session-factory wiring, `StorageService` creation,
  request-object construction, commit behavior, and `json.dumps(...)` rendering
  belong in `app/cli_commands/runtime.py` or
  `app/cli_commands/search_harness.py`.
- Minimal shared helpers may be added to `app/cli_commands/common.py` only for
  very small cross-module needs such as JSON rendering or lazy import access.
  Do not put command bodies, parser factories, or generic session abstractions
  there.
- Do not move the residual `app/cli.py` families into
  `app/agent_task_cli.py`, `app/claim_support_replay_cli.py`,
  `app/improvement_case_intake_cli.py`, or another new top-level CLI file.
- Preserve stable wrapper names in `app/cli.py` for service-level monkeypatch
  points unless a compatibility test is updated in the same milestone commit to
  prove the replacement contract is equivalent or stronger.
- New direct runtime command tests belong in focused files such as
  `tests/unit/test_cli_runtime.py` and `tests/unit/test_cli_search_harness.py`,
  not in `tests/unit/test_cli.py`.

## Weak Point Prevention Contract

| Weak point forecast | Owner surface | Prevention gate | Fail threshold | Controlled violation | Future-Codex misuse scenario |
| --- | --- | --- | --- | --- | --- |
| The facade keeps accumulating direct command scaffolding because the current rule only blocks new `def` bodies and `ArgumentParser(...)` lines | `config/hotspot_prevention.yaml`, `app/hotspot_prevention_classifier.py`, `app/cli.py` | `uv run docling-system-hotspot-prevention-check --strict` plus `tests/unit/test_hotspot_prevention.py` | New direct parser, session, storage, or JSON-render scaffolding can be added to `app/cli.py` without the gate failing | Add a temporary direct `ArgumentParser(...)`, `get_session_factory()`, or `json.dumps(...)` body to `app/cli.py` and confirm the tightened rule blocks it | A future session adds a “small CLI tweak” directly in `app/cli.py` instead of routing it into `app/cli_commands/` |
| The split just recreates a new monolith in `app/cli_commands/common.py` or one oversized catch-all command file | `app/cli_commands/common.py`, `app/cli_commands/runtime.py`, `app/cli_commands/search_harness.py`, staged diff | `uv run docling-system-hygiene-check` plus line-budget review | `common.py` becomes a generic framework, or either owner module exceeds the stated budget | Temporarily move a full command body into `common.py` or add a third owner module and confirm the milestone acceptance review fails | A future session sees repeated helper code and pushes full command orchestration into `common.py` because it looks convenient |
| Direct owner tests get shoved into the already-governed legacy `tests/unit/test_cli.py` hotspot | `tests/unit/test_cli.py`, `tests/unit/test_cli_runtime.py`, `tests/unit/test_cli_search_harness.py` | `uv run docling-system-hotspot-prevention-check --strict` and focused unit suites | New broad test groups are added to `tests/unit/test_cli.py` instead of focused files | Add a temporary `def test_new_command_group...` case to `tests/unit/test_cli.py` and confirm the gate blocks it | A future session keeps all CLI tests in the old file because the existing imports already work there |
| Entry point or monkeypatch compatibility drifts while command bodies move | `app/cli.py`, `pyproject.toml`, focused CLI tests | `uv run pytest -q` on the named CLI suites plus `pyproject.toml` entrypoint assertions | Any console-script entrypoint or stable monkeypatch target changes without equivalent replacement coverage | Temporarily remove an `app.cli:run_*` forwarder or a stable wrapper name and confirm compatibility tests fail | A future session “cleans up wrappers” and silently breaks console scripts or test patch points |

Accepted residual risk after closeout: `app/cli.py` may still remain a routed
hotspot because of stable console-script fan-in even after command bodies are
removed. If that happens, route the remaining CLI residual from fresh
post-closeout evidence rather than stretching this plan into a generic CLI
framework cleanup.

## Milestone Sequence

This plan is intentionally stacked behind the current claim-support,
evaluations, evidence provenance-export, and semantics packets. Milestone 0 is
mandatory and must run before any CLI code changes start.

### Milestone 0 - Post-Claim-Support-Evaluations-Evidence-Semantics System-State Refresh

Status: resolved locally
Outcome label: `resolved`

Purpose:

- convert the current repo state from “four prior packets drafted or in flight”
  into the fresh baseline used by this plan
- promote this CLI plan to the active bounded follow-on only after the prior
  four milestones are actually complete

Implementation:

- confirm
  `docs/claim_support_policy_impacts_boundary_milestone_plan.md`,
  `docs/evaluations_service_boundary_milestone_plan.md`,
  `docs/evidence_provenance_exports_boundary_milestone_plan.md`, and
  `docs/semantics_service_boundary_milestone_plan.md`
  each have a real closeout commit recorded and are no longer merely drafted
- rerun live routing and hotspot evidence after those closeouts:
  `git status -sb`,
  `uv run docling-system-architecture-quality-report --summary`,
  `uv run docling-system-improvement-case-summary`,
  `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 12`,
  and `wc -l` for the active CLI owner files
- update `docs/SESSION_HANDOFF.md` and `docs/agentic_architecture_index.md` so
  this CLI plan becomes the active bounded implementation brief
- refresh this plan's evidence section if the prior closeouts changed the live
  counts materially

Acceptance:

- all four prior packets are complete, verified, and committed locally before
  CLI implementation begins
- the targeted repeated command-body scaffolding still lives in `app/cli.py`
- this plan, `docs/SESSION_HANDOFF.md`, and
  `docs/agentic_architecture_index.md` reflect the refreshed post-stack state
- if the targeted concern families have already moved or the prior packets are
  incomplete, stop and rewrite this plan instead of continuing

### Milestone 1 - CLI Facade Prevention Ratchet

Status: resolved locally
Outcome label: `resolved`

Implementation:

- tighten the existing `app/cli.py` hotspot-prevention rule so it also blocks
  new direct session or storage wiring and direct JSON-render or parser-body
  scaffolding on the facade
- preserve the existing allowance for explicit forwarding functions that route
  from `app/cli.py` into `app/cli_commands/*`
- add a controlled-violation test proving the tightened rule blocks direct
  command scaffolding while still allowing the ingest-style forwarding pattern
- prepare the post-split hygiene and owner-case linkage so the narrowed facade
  is governed under `IC-9812A0B138D9`

Acceptance:

- `uv run docling-system-hotspot-prevention-check --strict` passes on the real
  milestone diff
- the new controlled violation fails when introduced
- the rule still allows explicit forwarding wrappers in `app/cli.py`
- the CLI facade can no longer gain new parser or session or JSON scaffolding
  without a gate failure

### Milestone 2 - Runtime Command Owner Extraction

Status: resolved locally through closeout commit `f5a4260`
Outcome label: `reduced`

Implementation:

- add `app/cli_commands/runtime.py`
- move the runtime and maintenance command bodies into that owner module:
  `run_eval_run(...)`,
  `run_eval_corpus(...)`,
  `run_audit(...)`,
  `run_backfill_legacy_audit(...)`,
  `run_knowledge_base_reset(...)`,
  `run_semantic_backfill_status(...)`,
  `run_semantic_backfill(...)`,
  `run_replay_search(...)`,
  `run_eval_candidates(...)`,
  `run_evaluation_data_readiness(...)`,
  `run_replay_suite(...)`, and
  `run_export_ranking_dataset(...)`
- preserve stable `app.cli:run_*` entrypoint names as explicit forwarding
  wrappers
- keep service wrapper names such as `evaluate_run`,
  `resolve_baseline_run_id`,
  `run_integrity_audit`,
  `backfill_legacy_run_audit_fields`,
  `get_semantic_backfill_status`,
  `execute_semantic_backfill`,
  `replay_search_request`,
  `list_quality_eval_candidates`,
  `build_evaluation_data_readiness_report`,
  `run_search_replay_suite`, and `export_ranking_dataset` stable unless the
  compatibility tests are updated in the same commit
- add direct owner coverage in `tests/unit/test_cli_runtime.py`

Acceptance:

- the selected runtime and maintenance command bodies no longer live in
  `app/cli.py` except for narrow forwarding seams
- `app/cli_commands/runtime.py` closes within `<= 550` lines and
  `<= 10` private helpers
- `tests/unit/test_cli.py` does not become the new owner test surface for these
  commands
- `app.cli` console-script entrypoints remain stable

### Milestone 3 - Retrieval-Learning And Search-Harness Command Owner Extraction

Status: implemented locally in working tree; closeout commit pending
Outcome label: `resolved` for the scoped CLI scaffolding issue and `reduced`
for the broader owner case unless the live hotspot fully retires

Implementation:

- add `app/cli_commands/search_harness.py`
- move the retrieval-learning and search-harness command bodies into that owner
  module:
  `run_materialize_retrieval_learning_dataset(...)`,
  `run_evaluate_retrieval_learning_candidate(...)`,
  `run_create_retrieval_reranker_artifact(...)`,
  `run_eval_reranker(...)`,
  `run_search_harness_evaluation_list(...)`,
  `run_search_harness_evaluation_show(...)`,
  `run_gate_search_harness_release(...)`,
  `run_search_harness_release_audit_bundle(...)`,
  `run_retrieval_training_run_audit_bundle(...)`,
  `run_audit_bundle_validation_receipt(...)`, and
  `run_optimize_search_harness(...)`
- preserve stable `app.cli:run_*` entrypoint names as explicit forwarding
  wrappers
- keep wrapper names such as `materialize_retrieval_learning_dataset`,
  `evaluate_retrieval_learning_candidate`,
  `create_retrieval_reranker_artifact`,
  `evaluate_search_harness`,
  `list_search_harness_evaluations`,
  `get_search_harness_evaluation_detail`,
  `record_search_harness_release_gate`,
  `create_search_harness_release_audit_bundle`,
  `create_retrieval_training_run_audit_bundle`,
  `create_audit_bundle_validation_receipt`, and
  `run_search_harness_optimization_loop` stable unless the compatibility tests
  are updated in the same commit
- use `tests/unit/test_cli_search_harness.py` as the focused direct owner suite
  for the new module and keep any remaining `tests/unit/test_cli.py` additions
  limited to compatibility assertions only

Acceptance:

- the selected retrieval-learning and search-harness command bodies no longer
  live in `app/cli.py` except for narrow forwarding seams
- `app/cli_commands/search_harness.py` closes within `<= 700` lines and
  `<= 14` private helpers
- `app/cli_commands/common.py` stays within `<= 80` lines and
  `<= 3` helpers
- `app/cli.py` closes within `<= 450` lines and `<= 1` private helper
- no third new `app/cli_commands/*.py` owner file is introduced
- the scoped repeated parser or session or JSON-print issue is resolved because
  those command bodies no longer cohabit the facade

### Milestone 4 - Closeout, Ratchets, And Residual Routing

Status: next active closeout slice
Outcome label: `reduced`

Implementation:

- update `config/hygiene_policy.yaml` with exact verified ceilings for the
  narrowed CLI facade and both new owner modules
- update `config/improvement_cases.yaml` so `IC-9812A0B138D9` records the
  refreshed measurements and broader owner-case state after the split
- refresh `docs/SESSION_HANDOFF.md`, `docs/agentic_architecture_index.md`, and
  this plan with the closeout hash, verification commands, and post-closeout
  routing
- stage only the verified CLI milestone slice and close with one local atomic
  commit

Acceptance:

- all required verification gates below pass in the same closeout window
- the scoped CLI scaffolding issue is recorded as resolved in this plan
- the broader owner case is marked `reduced` unless live architecture evidence
  proves full retirement
- the same closeout commit contains code, tests, governance config, and docs

## Required Implementation Artifacts

- `app/cli_commands/runtime.py`
- `app/cli_commands/search_harness.py`
- updated `app/cli.py`
- updated `app/cli_commands/common.py` if a minimal shared helper is needed
- updated hotspot-prevention policy and classifier
- updated focused CLI unit tests
- updated improvement-case and hygiene routing
- updated architecture index and handoff

## Required Documentation And Handoff Updates

- this plan:
  `docs/cli_command_dispatch_boundary_milestone_plan.md`
- architecture index:
  `docs/agentic_architecture_index.md`
- canonical handoff:
  `docs/SESSION_HANDOFF.md`
- improvement-case registry:
  `config/improvement_cases.yaml`
- hygiene ratchets:
  `config/hygiene_policy.yaml`

Milestone 0 must also update the active-follow-up references in the handoff and
index after the semantics milestone completes.

## Required Verification Gates

- `git diff --check`
- `uv run ruff check app/cli.py app/cli_commands/common.py app/cli_commands/ingest.py app/cli_commands/improvement_cases.py app/cli_commands/runtime.py app/cli_commands/search_harness.py app/hotspot_prevention_classifier.py tests/unit/test_cli.py tests/unit/test_cli_entrypoints.py tests/unit/test_cli_runtime.py tests/unit/test_cli_search_harness.py tests/unit/test_hotspot_prevention.py tests/unit/test_cli_improvement_cases.py tests/unit/test_cli_ingest.py`
- `uv run pytest -q tests/unit/test_cli.py tests/unit/test_cli_entrypoints.py tests/unit/test_cli_runtime.py tests/unit/test_cli_search_harness.py tests/unit/test_hotspot_prevention.py tests/unit/test_cli_improvement_cases.py tests/unit/test_cli_ingest.py`
- `uv run docling-system-hotspot-prevention-check --strict`
- `uv run docling-system-hygiene-check`
- `uv run docling-system-architecture-inspect`
- `uv run docling-system-capability-contracts`
- `uv run docling-system-architecture-quality-report --summary`
- `uv run docling-system-improvement-case-validate`
- `uv run docling-system-improvement-case-summary`
- `python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 12`
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs`

If any verification command fails, the milestone does not close and must not be
committed as complete.

## Acceptance Criteria

- Milestone 0 refreshes the repo's live system state after the claim-support,
  evaluations, evidence provenance-export, and semantics packets close and
  promotes this plan to the active bounded follow-on.
- `app/cli.py` gains a tightened prevention rule that blocks new direct parser,
  session, storage, or JSON-render scaffolding before broad extraction begins.
- No more than two new owner modules are introduced under `app/cli_commands/`.
- The selected repeated parser or session or JSON-print command bodies no
  longer live in `app/cli.py` by closeout except for narrow forwarding seams.
- `app/cli_commands/runtime.py` and `app/cli_commands/search_harness.py`
  remain under the stated line and helper ceilings.
- `app/cli_commands/common.py` remains a small helper surface rather than a
  generic framework.
- `app/cli.py` closes at `<= 450` lines and `<= 1` private helper with only
  allowed forwarding or compatibility seams.
- Console-script entrypoints in `pyproject.toml` and stable `app.cli` wrapper
  names remain behavior-stable.
- `tests/unit/test_cli.py` stays a compatibility surface; new owner-module
  coverage lives in focused files instead of broadening the legacy test file.
- The architecture probe does not increase Python cycle components above the
  current baseline of `5`.
- Test coverage is equivalent or stronger than before the split; no test,
  fixture, or gate is weakened to get green.
- The scoped CLI scaffolding issue is `resolved` in this plan, while the
  broader owner case is only `reduced` unless refreshed live evidence proves
  the hotspot is retired.

## Stop Conditions

- Stop if Milestone 0 shows any of the four prior packets are not yet complete
  and committed.
- Stop if the selected repeated command-body scaffolding has already moved or
  the file no longer matches this plan's baseline shape after the prior
  closeouts.
- Stop if preserving entrypoint and monkeypatch compatibility requires more
  than two new owner modules.
- Stop if either new owner module cannot be kept within the stated line and
  helper ceilings.
- Stop if the split requires moving business logic into service modules or
  growing a broad generic framework in `app/cli_commands/common.py`.
- Stop if targeted verification fails in a way that implies console-script
  renames, service-boundary changes, or a broad CLI architecture rewrite
  outside this packet.

## Local Commit Closeout Policy

- Stage only the verified CLI milestone slice.
- Leave unrelated dirty and untracked files alone.
- Include implementation, tests, config, docs, and handoff updates in the same
  local atomic commit.
- Record the closeout commit hash in this plan and in `docs/SESSION_HANDOFF.md`.
- Treat the milestone as incomplete until that commit exists.
- Do not commit if any required verification gate fails.

## Residual Risks And Next Milestone Routing

- Most likely residual risk: `app/cli.py` may still remain a routed hotspot
  because its stable console-script fan-in keeps churn concentrated even after
  direct command bodies move out. If so, route the remaining issue from fresh
  post-closeout evidence rather than stretching this plan.
- Another residual risk is that one focused CLI command module could still be
  large enough to deserve its own future boundary split. Route that as explicit
  new residual debt if it happens.
- After closeout, choose the next follow-on from fresh post-closeout evidence
  in `uv run docling-system-architecture-quality-report --summary`,
  `uv run docling-system-improvement-case-summary`, and the architecture probe.
- Do not predeclare the post-CLI target before that evidence exists.
