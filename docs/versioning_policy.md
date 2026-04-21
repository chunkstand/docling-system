# Versioning Policy

This repository currently has one active platform lane and one reserved future lane:

- `v1`: the active stable operator platform
- `v2`: the reserved name for a future experimental agentic platform lane

The repository also has a separate semantics-layer initiative. That initiative is not synonymous with
`v2`. Semantics-layer work may be developed as additive, versioned, feature-flagged work within the
current repository without implying a platform fork.

The purpose of this policy is to keep those lanes explicit in Git, in runtime metadata, and in user-facing contracts.

## Core Rules

- `v1` stays boring, stable, and releasable.
- `v2` is reserved for a future agentic platform project; it is not the default bucket for every
  experimental change.
- Semantics-layer work is not automatically `v2` work.
- If semantics-layer work preserves the current `v1` contracts and remains additive, it can be
  developed and promoted through normal feature branches against `main`.
- If semantics-layer work later requires a breaking platform contract or a new autonomous operating
  model, that subset becomes a candidate for the future `v2` lane.
- Experimental work does not become `v1` merely because it is useful; it becomes `v1` only after promotion.
- Git history is for code and reviewed config contracts. Runtime experiments, attempts, and loop artifacts live in the database and `storage/`, not only in commit history.
- Promotion is additive and explicit. Do not rewrite history or silently mutate named stable contracts in place.

## Git Branch Policy

### Stable branch

- `main` is the protected `v1` branch.
- `main` must remain deployable and compatible with the current stable platform contracts.
- Branches intended for `main` should be named `codex/v1-<topic>` or `codex/<topic>` when the work is clearly stable-platform work.

### Semantics initiative branches

- Semantics-layer feature branches should be named `codex/semantics-<topic>` or
  `codex/v1-semantics-<topic>`.
- Semantics-layer branches should start from `main` unless and until the specific work clearly
  targets a future `v2` platform.
- Keep semantics-layer work additive, feature-flagged, and compatible with the current stable code
  path while it still belongs to the `v1` platform line.

### Future `v2` branch

- `v2` is a reserved protected integration branch for a future agentic platform project.
- Do not create or use `v2` merely as a holding area for general experiments.
- When the future `v2` project starts, branches intended for it should be named `codex/v2-<topic>`.
- Once created, `v2` may move faster than `main`, but it must still build, migrate, and run its
  bounded verification steps.
- Once created, merge `main` into `v2` regularly. Do not let `v2` drift for long periods without
  absorbing stable fixes.

### Direct commit rule

- Do not commit directly to `main` or to `v2` if and when it exists.
- Land work through short-lived feature branches and reviewed merges.
- If a semantics-layer change starts on a feature branch and later becomes stable, promote it with a
  normal merge into a `codex/v1-*` branch or directly through the reviewed `main` path, depending on
  the release workflow in use.
- If a future `v2` change later becomes stable, promote it with a normal merge or a deliberate
  cherry-pick into a `codex/v1-*` branch. Do not force-push or rewrite the original experiment
  history.

## Release Tag Policy

- Stable releases from `main` use semantic version tags: `v1.x.y`.
- Semantics-layer feature branches are not a separate platform release lane. Do not tag them as
  `v2` snapshots just because they are experimental.
- If a semantics-layer branch needs shareable experiment checkpoints, use clearly non-platform
  annotated snapshot tags such as `semantics-<topic>-alpha.N` or `semantics-<topic>-preview.N`.
- Semantics snapshot tags must point to feature-branch commits, not to `main`, and their
  annotation should record the source branch and the base `main` commit or release tag they were
  cut from.
- Experimental snapshots from the future `v2` branch use prerelease tags: `v2.0.0-alpha.N`, then
  `v2.0.0-beta.N` when the surface starts to stabilize.
- Hotfixes for stable production use the next `v1.x.(y+1)` tag from `main`.
- Do not spray tags across arbitrary experiment commits. Tag only deliberate semantics checkpoints,
  stable `main` releases, or future `v2` prereleases once that lane exists.

## What Belongs In `v1`, The Semantics Layer, And Future `v2`

### Land on `v1`

- bug fixes that preserve existing contracts
- additive API fields that do not break clients
- additive database columns and tables that preserve existing semantics
- bounded search-harness tuning and replay/evaluation improvements
- new evaluations, telemetry, and auditability that strengthen existing loops
- operator-facing tooling that does not change the stable platform model

### Build in the semantics-layer initiative first

- governed concept registries, aliases, and relation definitions
- additive semantic-link, fact, and mapping tables that preserve current stable behavior
- feature-flagged semantic extraction, mapping, and retrieval experiments
- semantic artifact families and semantic evaluations that are explicit about schema and version
- semantics-specific validation and telemetry that do not silently redefine existing `v1` contracts

### Land on future `v2` first

- self-directed agent loops that can change behavior without per-step operator review
- new autonomous promotion or auto-apply mechanisms
- breaking API, artifact, schema, or workflow contract changes
- major orchestration model changes
- model-selection policies that materially change runtime behavior
- agent memory systems, experiment planners, or background optimization daemons that are not yet operationally settled

### Decision rule

If a change is semantics-layer work and remains additive and contract-compatible, it does not
require `v2`.

If a change would make an operator ask "is this still the same platform contract?" it belongs on
the future `v2` lane first.

## Contract Versioning

Platform version, API version, schema version, semantic-model version, harness version, and workflow
version are separate axes. Do not collapse them into one label.

### Platform versions

- `v1` means the stable operator platform described by `README.md` and `SYSTEM_PLAN.md`.
- `v2` means the future experimental agentic platform and may contain breaking changes relative to
  `v1`.

### Semantics-layer versions

- Semantic model version, concept-registry version, fact-schema version, and mapping-pipeline
  version are independent of platform version.
- Do not infer semantic-model version from the Git branch name alone.
- When semantics-layer outputs become durable machine-facing artifacts, version them explicitly.

### API contracts

- `v1` endpoints remain stable on `main`.
- Additive response fields are allowed on `main` if old clients continue to work.
- Breaking API changes must ship behind a new route family, explicit experimental endpoint, or on
  the future `v2` lane only until promoted.
- When an experimental API is expected to survive, prefer explicit names such as `/agent-tasks/...` or `/experimental/...` over silently changing existing `v1` routes.

### Database schema

- Schema changes on `main` must be backward-compatible for the current stable code path.
- Additive semantics-layer tables, columns, and artifacts are allowed on `main` if the current
  stable code path remains backward-compatible.
- Destructive migrations, semantic reinterpretations of existing columns, or changes that require
  lockstep deploy behavior belong on the future `v2` lane first.
- Every durable run, task, evaluation, and experiment row should continue to record enough metadata to explain which code and contract versions produced it.

### Artifact schemas

- Canonical machine-readable artifacts must have stable schemas.
- New machine-readable artifact families should carry explicit `schema_name` and `schema_version`
  fields when practical.
- Human-readable YAML remains derived output and does not define version semantics.
- If an artifact format needs a breaking change, mint a new schema version; do not silently overload the old one.

## Harness, Workflow, and Prompt Versioning

These are versioned independently from platform version.

### Search harnesses

- Promoted harness names are immutable once published.
- Stable harness names use `<family>_vN`, for example `default_v1`.
- Experimental harnesses on the future `v2` lane use prerelease suffixes, for example
  `default_v2_alpha1`.
- Promotion creates a new stable name. Do not change the meaning of an existing promoted harness in place.

### Agent workflows

- Workflow definitions carry their own version metadata and should be treated as immutable snapshots once used in production-like runs.
- Breaking workflow changes should increment the workflow version even if they stay on the same Git branch.
- If a workflow is still exploratory, mark it as experimental in its durable metadata rather than pretending it is stable.

### Prompts and verifier thresholds

- Prompts, verifier rules, and threshold bundles that affect behavior must be version-stamped in task or run metadata.
- Do not rely on "latest prompt" as a runtime contract.

## Evaluation Corpus Policy

- `docs/evaluation_corpus.yaml` is a reviewed contract file and belongs in Git.
- Changes to the hand-authored corpus should land with the code or config change they justify.
- Auto-generated corpus artifacts under `storage/` are runtime data, not durable source-of-truth version control.
- A change that improves metrics only by weakening the corpus or verifier does not count as a valid promotion.

## Runtime Experiment Policy

- Search-harness optimization attempts, agent-task attempts, loop artifacts, and replay runs are runtime records, not Git releases.
- Every experiment artifact should be traceable back to:
  - Git commit SHA
  - platform lane (`v1` or `v2` once it exists)
  - semantic-model version when applicable
  - harness version
  - workflow version
  - model/version metadata
  - evaluation corpus context
- Use Git to version the mechanism. Use the database and `storage/` to version the executions.

## Promotion Policy: Semantics Layer To Stable `v1`

A semantics-layer capability is eligible for promotion into the stable `v1` contract only when all
of the following are true:

- the behavior is additive enough to preserve the current stable platform contract
- the semantic model, mapping, and artifact versions are explicit
- the evaluation and rollback story are clear
- migrations and storage impacts are understood
- operator approval points are explicit where needed
- the feature passes the relevant `v1` verification path
- documentation is updated in `README.md` and `SYSTEM_PLAN.md`

Promotion should usually happen in four steps:

1. stabilize the semantics-layer behavior behind explicit names, feature flags, and metrics
2. prove it through evaluations, replay evidence, and operator review
3. merge it through the normal `v1` branch path with any required compatibility cleanup
4. release it from `main` under the next `v1.x.y` tag when it is part of the stable platform

## Promotion Policy: Future `v2` to `v1`

A `v2` capability is eligible for promotion only when all of the following are true:

- the behavior is bounded enough to describe as a stable contract
- the evaluation and rollback story are clear
- migrations and storage impacts are understood
- operator approval points are explicit where needed
- the feature passes the relevant `v1` verification path
- documentation is updated in `README.md` and `SYSTEM_PLAN.md`

Promotion should usually happen in four steps:

1. stabilize the `v2` behavior behind explicit names and metrics
2. prove it through evaluations, replay evidence, and operator review
3. merge or cherry-pick into a `codex/v1-*` branch with any required compatibility cleanup
4. release from `main` under the next `v1.x.y` tag

## Rollback Policy

- Roll back stable behavior by switching active pointers, harness selections, feature flags, or releases.
- Do not roll back by deleting experiment history.
- If an experimental semantics-layer mechanism fails, preserve the evidence and disable promotion
  paths rather than rewriting artifacts to make the failure disappear.
- If a future `v2` mechanism fails, preserve the evidence and disable promotion paths rather than
  rewriting artifacts to make the failure disappear.

## Naming Summary

- Stable platform branch: `main`
- Semantics-layer branch prefix: `codex/semantics-` or `codex/v1-semantics-`
- Semantics snapshot tags: `semantics-<topic>-alpha.N` or `semantics-<topic>-preview.N`
- Experimental platform branch: `v2` when that future project starts
- Stable feature branch: `codex/v1-<topic>`
- Experimental feature branch: `codex/v2-<topic>` for the future `v2` project
- Stable release tags: `v1.x.y`
- Experimental release tags: `v2.0.0-alpha.N`, `v2.0.0-beta.N` for the future `v2` project
- Stable harness names: `<family>_vN`
- Experimental harness names: `<family>_vN_alphaN`

## Practical Examples

- Adding a new replay source and a new evaluation report endpoint without breaking existing routes: `v1`
- Adding governed concept registries and feature-flagged semantic links without breaking current
  retrieval contracts: semantics layer
- Letting an agent auto-apply harness changes without human approval: future `v2`
- Replacing the current task substrate with a planner/executor/memory system that changes
  operational behavior: future `v2`
- Adding durable experiment logs and keeping them read-only unless explicitly promoted: safe to
  land on `main` if the stable contracts do not change, and not automatically a `v2` concern
- Promoting an experimental harness `default_v2_alpha3` after review, once the future `v2` project
  exists: publish a new immutable stable harness such as `default_v2`
