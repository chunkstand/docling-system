# Agentic Architecture Milestone Plan

Date: 2026-05-04
Status refreshed: 2026-05-10

Purpose: translate code-review, software-architecture, and agentic-system
guidance into an implementation plan for making this repository easier for
humans and coding agents to review, modify, verify, and maintain.

## Grounding Snapshot

Current architecture status:

- The system is already a modular monolith with public capability facades,
  architecture decisions, route/action contracts, architecture inspection, and
  measurement history.
- `uv run docling-system-architecture-inspect` currently reports
  `valid: true`, `violation_count: 0`, `api_route_count: 130`,
  `agent_action_count: 51`, `contract_count: 10`, and
  `inspection_rule_count: 13`.
- `uv run docling-system-capability-contracts` currently reports
  `valid: true`, `facade_count: 6`, `function_count: 110`, and no issues.
- `uv run docling-system-architecture-quality-report --summary` currently
  reports `agent_legibility_average_score: 90.0`, `broad_facade_count: 2`,
  `hotspot_count: 10`, and `max_hotspot_risk_score: 687.04`.
- The general architecture probe still reports 3 Python cycle components.
  `app.services.agent_task_actions` remains part of the large agent-task cycle
  component and has fan-out 39, so the first registry/helper split did not close
  executor-level coupling.
- The main architecture control points are:
  - `docs/architecture_boundaries.md`
  - `docs/agentic_architecture_index.md`
  - `docs/agentic_architecture_milestone_audit.md`
  - `docs/architecture_contract_map.json`
  - `docs/capability_contract_map.json`
  - `docs/architecture_decisions.yaml`
  - `config/architecture_inspection.yaml`
- The largest service modules are still governed hotspot work. They are ranked
  by the architecture quality report and should be split one behavior-preserving
  milestone at a time:
  - `app/services/evidence.py`: 8,608 lines after the first search-evidence
    split
  - `app/services/audit_bundles.py`: 3,862 lines
  - `app/services/agent_task_context.py`: 3,858 lines
  - `app/services/claim_support_policy_impacts.py`: 3,477 lines
  - `app/services/search.py`: 3,429 lines
  - `app/services/agent_task_actions.py`: 2,884 lines after the first
    search-harness registry/helper split
  - `app/services/retrieval_learning.py`: 3,028 lines
  - `app/db/models.py`: 6,006 lines and the highest current hotspot score
    after the first model-domain split
  - `app/cli.py`: 1,283 lines after the first improvement-case command-group
    split
- Recent 90-day churn hotspots include `app/db/models.py`,
  `app/schemas/agent_tasks.py`, `app/services/agent_task_actions.py`,
  `app/cli.py`, `app/api/main.py`, `app/services/evidence.py`,
  `app/services/agent_tasks.py`, and `app/services/search.py`.

Interpretation: the system does not need a rewrite or premature service
extraction. It needs narrower review surfaces, stronger agent-legibility
contracts, hotspot-aware prioritization, and more of the existing human
judgment encoded into mechanically checked repository artifacts.

## Research Panel

### Martin Fowler and Kent Beck: evolutionary refactoring

Relevant guidance:

- Fowler describes refactoring as small behavior-preserving transformations
  that cumulatively improve the design while reducing breakage risk.
- Fowler's modernization guidance favors gradual replacement through stable
  seams instead of big-bang rewrites.

Panel evaluation:

- The modular monolith decision is correct for v1. The capability facades are
  the right seams.
- The next architecture work should preserve public facades while splitting
  oversized implementation modules behind them.
- Do not extract services yet. The current value is in stable in-process seams,
  validation gates, and DB-backed state, not network boundaries.

Sources:

- https://martinfowler.com/books/refactoring.html
- https://martinfowler.com/bliki/StranglerFigApplication.html

### John Ousterhout: complexity and deep modules

Relevant guidance:

- Ousterhout emphasizes designing around important complexity and using
  general-purpose deeper modules with simpler interfaces.

Panel evaluation:

- The current facades are deep in the good sense: they hide DB, artifact, and
  service implementation details from API and worker boundaries.
- Some surfaces are now broad enough to become shallow for agents. The
  `retrieval` and `agent_orchestration` capability protocols expose many
  concerns through one tool-like surface.
- The next improvement is not more layers. It is clearer subcontracts:
  search, replay, release, learning, task catalog, task lifecycle, task audit,
  task analytics, and worker execution.

Source:

- https://web.stanford.edu/~ouster/cgi-bin/aposd.php

### Adam Tornhill: hotspots and behavioral code analysis

Relevant guidance:

- Tornhill's CodeScene work prioritizes files that combine high change activity
  with low code health; stable low-health code is lower priority than unhealthy
  code under active change.

Panel evaluation:

- The architecture gate currently knows whether boundary rules are broken, but
  it does not yet rank architecture debt by cost of change.
- The highest-priority refactors should be selected by combined evidence:
  churn, file size, coupling, contract growth, bug/eval failures, and review
  friction.
- `app/db/models.py`, `app/services/agent_task_actions.py`,
  `app/services/evidence.py`, and `app/services/search.py` are the first
  candidates because they combine size, centrality, and churn.
  `Architecture Plan 01` has already moved the first low-risk
  `app/db/models.py` domain, `ApiIdempotencyKey`, behind the
  `app.db.models` compatibility facade, and has split search evidence package
  assembly/export/trace helpers out of `app/services/evidence.py`.

Source:

- https://docs.enterprise.codescene.io/versions/6.2.8/guides/technical/hotspots.html

### Hamel Husain plus current agent guidance: evals, traces, and harnesses

Relevant guidance:

- Hamel's eval guidance emphasizes error analysis, trace review, custom
  application-specific metrics, calibrated judges, and coding-agent eval skills.
- Anthropic's agent guidance favors simple workflows first, explicit planning,
  transparent tool use, and carefully tested agent-computer interfaces.
- OpenAI's harness-engineering guidance treats repository-local knowledge,
  strict boundaries, mechanical checks, observability, and recurring cleanup as
  core infrastructure for agent-first software work.

Panel evaluation:

- This repository is already unusually aligned with agentic architecture:
  typed agent actions, persisted context, trace/audit artifacts, approval
  gates, eval corpora, architecture fitness functions, and improvement intake
  are the right foundation.
- The next gap is agent legibility at scale. Agents need smaller maps, better
  task-local contracts, high-signal trace/replay entry points, and quality
  metrics that tell them what to inspect next.
- Generic "AI quality" scores should not be added. Use real failed traces,
  replay regressions, verification failures, stale docs, and hotspot trends as
  the architecture signal.

Sources:

- https://hamel.dev/blog/posts/evals-skills/index.html
- https://hamel.dev/blog/posts/evals-faq/evals-faq.pdf
- https://www.anthropic.com/engineering/building-effective-agents
- https://www.anthropic.com/engineering/writing-tools-for-agents
- https://openai.com/index/harness-engineering/
- https://openai.com/business/guides-and-resources/a-practical-guide-to-building-ai-agents/

## Panel Verdict

The architecture is directionally strong and already has the right core
doctrine: modular monolith, canonical structured data, typed agent actions,
validation-gated promotion, persisted evaluation, and architecture fitness
functions.

The architecture is not yet optimized for sustained agentic development. The
risk is that agents will keep copying patterns from the largest, most central
modules, causing local consistency but global entropy. The remedy is to turn
human review taste into smaller contracts, generated maps, and recurring
architecture garbage collection.

## Milestone Plan

### Milestone 0: Agentic Architecture Baseline

Goal: establish a baseline that ranks architecture risk by both boundary
violations and cost of change.

Deliverables:

- Add a generated architecture quality report that combines:
  - architecture inspection result
  - capability facade size and growth
  - module line count
  - 30/90-day churn
  - public function count
  - known hygiene findings
  - linked improvement cases
- Extend architecture measurement history with hotspot fields instead of
  relying only on violation counts.
- Document an "agent-legibility score" for major surfaces: clear owner,
  public entrypoint, contract map, examples, tests, trace/replay command, and
  decision rationale.

Acceptance signal:

- `uv run docling-system-architecture-inspect`
- `uv run docling-system-capability-contracts`
- new quality report command emits JSON with stable schema and no write unless
  explicitly requested
- tests cover the quality-report schema and drift behavior

### Milestone 1: Split Broad Capability Surfaces Into Subcontracts

Goal: keep stable facade imports while making each facade easier for agents to
inspect and use.

Deliverables:

- Split `retrieval` into contract companions such as:
  - search execution and history
  - replay and comparison
  - harness evaluation and release
  - audit bundle and receipt operations
  - retrieval learning and reranker artifacts
  - chat and feedback
- Split `agent_orchestration` into contract companions such as:
  - action catalog
  - task lifecycle
  - context and artifacts
  - approvals and verifications
  - audit/provenance/evidence
  - analytics and worker control
- Preserve `app.services.capabilities.retrieval` and
  `app.services.capabilities.agent_orchestration` as compatibility facades.
- Regenerate and validate `docs/capability_contract_map.json`.

Acceptance signal:

- existing API/router tests unchanged or minimally adjusted
- `uv run docling-system-capability-contracts --write-map`
- `uv run docling-system-architecture-inspect`
- focused tests for capability contracts and route architecture

### Milestone 2: Hotspot-Driven Implementation Splits

Goal: reduce the largest and highest-churn implementation surfaces without
changing external behavior.

Deliverables:

- Split `app/services/evidence.py` behind compatibility functions into focused
  modules for:
  - search evidence packages (complete in `Architecture Plan 01` Milestone 3)
  - technical-report evidence closure
  - claim derivation and feedback ledgers
  - agent-task audit bundles
  - provenance/export traces
- Split `app/services/agent_task_actions.py` into a registry composition module
  plus per-domain action registration modules. Keep the public registry
  functions stable. `Architecture Plan 01` Milestone 4 completed the first
  search-harness action registry/helper split in
  `app/services/agent_actions/search_harness.py`; the next action-family split
  should target an executor dependency seam before moving executor
  implementations out of the facade.
- Split `app/cli.py` into command-group modules behind compatibility exports.
  `Architecture Plan 01` Milestone 5 completed the first improvement-case
  command-group split in `app/cli_commands/improvement_cases.py`, with
  explicit `app.cli` forwarding functions preserving console entrypoints.
- Continue the prior `search.py` split by isolating query planning, feature
  extraction, ranking, and result hydration where tests already give coverage.
- Continue model-domain splits only when they can be paired with exact
  migration/create-all verification. `Architecture Plan 01` Milestone 2 proved
  the pattern with `ApiIdempotencyKey` in `app/db/model_domains/platform.py`.

Acceptance signal:

- no public import breakage
- focused unit tests for each split module
- `uv run docling-system-hygiene-check` shows no new regressions
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs` before landing any
  split touching DB, API, storage-backed routes, or migrations

### Milestone 3: Agent Action and Tool Interface Hardening

Goal: make every agent action a high-quality tool contract, not just a typed
executor.

Deliverables:

- Extend the agent action manifest with agent-facing fields:
  - concise tool description
  - when to use
  - when not to use
  - required context refs
  - expected artifacts
  - verification command
  - common failure modes
  - escalation condition
- Add manifest validation for missing examples, ambiguous task descriptions,
  unsafe side-effect metadata, and stale context-builder names.
- Generate a compact agent action index from the manifest for future agents.
- Add error-response shape checks for action validation failures.

Acceptance signal:

- `tests/unit/test_agent_action_contracts.py`
- generated action manifest is stable
- at least one HTTP-boundary test for action catalog or task creation failure
  paths

### Milestone 4: Trace-First Evaluation And Review Harness

Goal: make architecture decisions and agent behavior reviewable from traces,
not from chat summaries.

Deliverables:

- Add a trace review command that samples:
  - failed agent tasks
  - failed verifications
  - replay regressions
  - stale approval gates
  - architecture/hygiene failures
- Route trace review findings into the existing improvement-case intake.
- Add scoped binary evals for recurring agent failures, such as missing
  artifact links, stale context refs, wrong side-effect level, or unsupported
  promotion.
- Keep retrieval and generation evals separate. Do not collapse them into a
  generic "agent quality" score.

Acceptance signal:

- trace review command has deterministic sample output
- improvement-case import dry run accepts the report
- at least one eval fixture proves a previously observed agent failure mode

### Milestone 5: Repository Knowledge As A Map, Not A Manual

Goal: reduce token burn and stale instruction drift by making repo knowledge
progressively discoverable.

Deliverables:

- Keep `AGENTS.md` as a short operating map.
- Add or update docs indexes that point to:
  - architecture contracts
  - active milestones
  - completed milestones
  - current handoff
  - verification commands
  - generated contract maps
  - known debt and improvement cases
- Add doc freshness checks for architecture docs that reference generated maps.
- Prefer small milestone briefs over long chat-derived summaries.

Acceptance signal:

- architecture inspection checks doc required tokens and map freshness
- future architecture work can start from one index plus the relevant contract
  map

### Milestone 6: Architecture Garbage Collection

Goal: make cleanup continuous, targeted, and measurable.

Deliverables:

- Add a recurring local/CI report that creates improvement-case candidates for:
  - modules above file budget
  - capability surfaces growing beyond threshold
  - duplicated helper patterns
  - stale docs versus generated maps
  - newly hot modules with low agent-legibility score
- Give each generated case an owner surface, verification command, and stop
  condition.
- Prefer many small behavior-preserving refactors over large cleanup branches.

Acceptance signal:

- generated cases are deduped through improvement intake
- architecture measurement summary shows trend deltas
- cleanup PRs remain reviewable in under one focused pass

### Milestone 7: Data Model Boundary Plan

Goal: reduce `app/db/models.py` centrality without destabilizing migrations.

Deliverables:

- Write a model-domain split design before touching model imports.
- Identify domain groupings: ingest, retrieval, semantic memory, agent tasks,
  audit/evidence, claim support, document artifacts.
- Add compatibility import tests before any split.
- Execute exact Alembic DDL and `Base.metadata.create_all(...)` verification
  against local Postgres after any model or migration change.

Acceptance signal:

- no migration drift
- local Postgres DDL verification passes
- `DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs`

## Non-Goals

- No microservice extraction in this milestone sequence.
- No generic LLM-app scorecards detached from real failures.
- No YAML-as-source-of-truth drift.
- No broad rewrite of the agent-task system.
- No large refactor that cannot be validated with focused tests and the
  architecture gates before continuing.

## Operating Rule

When a human review comment, failed agent run, or repeated cleanup issue reveals
a durable preference, encode it in this order:

1. focused test or architecture rule
2. generated contract map or manifest field
3. concise repo documentation that points to the executable check
4. improvement-case entry with owner, verification, and stop condition

The target state is not "prettier code." The target state is a codebase where
agents can reliably locate the right surface, understand the contract, make a
small change, run the right checks, and leave durable evidence for human review.
