# Session Handoff

Date: 2026-05-11 local / 2026-05-11 UTC
Project: `/Users/chunkstand/Documents/docling-system`
Branch: `main`
Remote: `origin -> https://github.com/chunkstand/docling-system.git`
Latest closeout checkpoint: Evaluation Feedback Model-Domain Milestone 1 owner
split is now verified locally in the current checkout; High Value Technical
Paydown Milestone 10 final closeout remains complete locally.
Active local follow-up owner case: `IC-F2A8110185EB` /
`app/db/models.py` agent-task continuation.
Active bounded implementation brief:
`docs/data_model_boundary_plan.md`.

## Current Position

The checkout is on `main`. Local `main` remains ahead of `origin/main` after
the High Value Technical Paydown Milestone 10 closeout, the Evaluation
Feedback Model-Domain Milestone 0 preflight closeout, and the Milestone 1
owner split staged in the current checkout.
`origin/main` is `33acc23` (`docs: plan residual weakness resolution
milestones`).

The Residual Weakness Plan is already closed through Milestone 8, and the
Hotspot Owner Resolution sequence is closed locally through Milestone 6. The
High Value Technical Paydown plan is now complete locally through Milestone 10:
it moved the retrieval-interaction, replay/release governance, and
retrieval-learning ORM families into focused owner modules, reduced
`app/db/models.py` to 3,570 lines while keeping `app.db.models` as the public
compatibility facade, and left the registry summary at `case_count=26`,
`status_counts.open=25`, `status_counts.measured=1`, and
`measured_case_count=14`. The completed evaluation-feedback milestone record
now lives in `docs/evaluation_feedback_model_domain_milestone_plan.md`, while
the routed follow-up returns to `docs/data_model_boundary_plan.md` until the
next dedicated `app/db/models.py` owner-split brief is written.

Post-closeout architecture alignment recheck on 2026-05-11 kept that routing
intact after the Milestone 1 owner split:
`uv run docling-system-architecture-quality-report --summary` now reports
`max_hotspot_risk_score=653.8` with `app/db/models.py` still first in
`top_hotspot_paths`, and
`python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 12`
reports `app/services/evidence.py` as the top churn hotspot while
`app/db/models.py` remains a governed model hotspot at score `267750`.

The completed implementation brief for the evaluation-feedback route lives in
`docs/evaluation_feedback_model_domain_milestone_plan.md`. It scoped
`resolved` to the evaluation-feedback concern itself
(`EvalObservation`, `EvalFailureCase`) and treats the broader
`IC-F2A8110185EB` owner case as only `reduced` unless the live
architecture-quality report stops flagging `app/db/models.py`. Milestone 0 in
that plan is now verified locally: routing agreement, DB-backed verification
availability, and the pre-move Alembic posture are confirmed, while the
evaluation-feedback metadata contract coverage is now in place and the ORM move
is verified locally. The broader owner case remains `reduced`, and the next
remaining model-domain candidate is the agent-task family if model work
continues in `app/db/models.py`.

## Evaluation Feedback Model-Domain Milestone 1 Progress

Milestone 1 is the evaluation-feedback contract and owner split for
`IC-F2A8110185EB` / `app/db/models.py`. It is a behavior-preserving ORM owner
split behind the existing `app.db.models` compatibility facade.

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
current Milestone 1 closeout are:

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

These commits close the High Value Technical Paydown current-state alignment
pass, add the dedicated evaluation-feedback follow-up brief, and close the
Milestone 0 preflight slice that must pass before the ORM move begins.

## Current Architecture And Governance State

Current read-only gates from this checkout:

```text
uv run docling-system-architecture-inspect
  valid=true, violation_count=0, api_route_count=130,
  agent_action_count=51, contract_count=10, inspection_rule_count=13

uv run docling-system-capability-contracts
  valid=true, facade_count=6, function_count=110, issues=[]

uv run docling-system-architecture-decisions
  valid=true, decision_count=9, issues=[]

uv run docling-system-architecture-quality-report --summary
  agent_legibility_average_score=90.0
  broad_facade_count=2
  hotspot_count=10
  max_hotspot_risk_score=658.21
  top_hotspot_paths=[
    app/db/models.py,
    app/cli.py,
    app/services/agent_task_actions.py,
    app/services/evidence.py,
    app/schemas/agent_tasks.py
  ]

python /Users/chunkstand/.codex/skills/code-architecture-governance/scripts/architecture_probe.py --format markdown --top 12
  Python cycle components=3
  app/services/agent_task_actions.py fan-out=39 local modules

uv run docling-system-improvement-case-summary
  case_count=26, measured=1, open=25,
  source_type_counts={hygiene_finding: 1, architecture_governance: 25}

uv run docling-system-hotspot-prevention-check --strict
  known_hotspots=6, changed_hotspots=0, added_lines=0, deleted_lines=0,
  blocked=0, allowed=0, exceptions=0

uv run docling-system-hygiene-check
  ruff regressions=none
  inherited budget debt listed with owner_case_id or owner_milestone
  new hygiene regressions=none
  improvement-case findings=none
  architecture findings=none

uv run docling-system-improvement-case-import --source hygiene --dry-run
  candidate_count=0, imported_count=0, skipped_count=0
```

The architecture boundary model is clean, but hotspot debt remains real. The
current top governed split targets are `app/db/models.py`, `app/cli.py`,
`app/services/agent_task_actions.py`, `app/services/evidence.py`, and
`app/schemas/agent_tasks.py`. The latest architecture probe records
`app/services/evidence.py` at 6,307 lines and 309,043 hotspot score,
`app/db/models.py` at 3,782 lines and 283,650 score,
`app/services/agent_task_actions.py` at 2,746 lines and 164,760 score, and
`app/cli.py` at 1,231 lines and 67,705 score.

Strict hygiene debt also remains real, but it is now ratcheted: the current
file/helper overages are non-blocking inherited entries while unchanged, and any
growth beyond their `ratchet_max_*` ceilings is a blocking hygiene regression.

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
