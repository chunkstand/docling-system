# Hotspot Prevention Gate Milestone Plan

Date: 2026-05-10
Status: planned

Purpose: stop future Codex and human changes from adding new implementation
weight to known hotspot files. Existing hotspot-reduction milestones split
large files after they become painful; this gate prevents the same files from
absorbing new concerns in the first place.

## Problem

Architecture inspection is green, but the architecture quality report still
ranks central files as top hotspots:

- `app/db/models.py`
- `app/cli.py`
- `app/services/evidence.py`
- `app/services/agent_task_actions.py`
- `tests/unit/test_cli.py`

The current architecture controls can tell us that a file is hot, and the
hygiene policy can report file-budget debt, but neither one currently blocks a
new diff from adding implementation logic to these files when a narrower owner
module already exists or should be created.

## Goal

Add an executable hotspot-prevention gate that answers one question for every
architecture milestone and future feature slice:

```text
Did this diff add implementation responsibility to a known hotspot instead of
placing it behind the intended owner module or compatibility facade?
```

The gate should fail on new hotspot growth, but allow behavior-preserving
refactors that shrink hotspots, preserve facade compatibility, or add narrow
forwarding aliases required by a split.

## Non-Goals

- Do not rewrite the architecture quality report scoring model in this
  milestone.
- Do not remove existing file-budget debt as part of gate implementation.
- Do not block deletions, moves, or facade-preserving compatibility shims that
  reduce centralization.
- Do not require DB-backed integration tests unless the implementation touches
  DB, API, storage, search, evidence runtime behavior, agent tasks, or worker
  paths.
- Do not make an LLM-only instruction the source of enforcement. The output
  must be executable and test-backed.

## Proposed Artifacts

- `config/hotspot_prevention.yaml`: tracked hotspot policy with owner modules,
  allowed facade-only edits, thresholds, and exception requirements.
- `app/hotspot_prevention.py`: pure-Python diff analyzer and policy evaluator.
- `docling-system-hotspot-prevention-check`: CLI entrypoint for local and CI
  use.
- `tests/unit/test_hotspot_prevention.py`: classifier, policy, and report tests.
- `tests/unit/test_cli.py` or a focused CLI test file: command wiring and exit
  code coverage.
- `docs/architecture_boundaries.md`: short boundary policy addition once the
  gate exists.
- `docs/SESSION_HANDOFF.md` and `docs/architecture_plan_01.md`: closeout status
  and next-routing updates.

## Policy Shape

The first policy should track current known hotspots and their intended owner
directions:

```yaml
known_hotspots:
  app/db/models.py:
    target_role: compatibility facade for ORM models
    preferred_owner_modules:
      - app/db/model_domains/
    block_new:
      - orm_class
      - enum
      - relationship_logic
      - broad_helper
    allow:
      - import_forwarder
      - table_metadata_alignment
      - deletion

  app/services/evidence.py:
    target_role: compatibility facade for evidence capabilities
    preferred_owner_modules:
      - app/services/evidence_*.py
    block_new:
      - private_helper
      - payload_builder
      - persistence_logic
      - artifact_assembly
    allow:
      - import_forwarder
      - alias_forwarder
      - deletion

  app/cli.py:
    target_role: console script compatibility and dispatch surface
    preferred_owner_modules:
      - app/cli_commands/
    block_new:
      - command_implementation
      - broad_parser_logic
    allow:
      - explicit_forwarding_function
      - parser_registration
      - deletion

  app/services/agent_task_actions.py:
    target_role: action registry compatibility and execution entrypoint
    preferred_owner_modules:
      - app/services/agent_actions/
    block_new:
      - executor_implementation
      - action_family_helper
      - schema_builder
    allow:
      - registry_composition
      - import_forwarder
      - deletion

  app/services/search.py:
    target_role: search service compatibility facade
    preferred_owner_modules:
      - app/services/search_*.py
    block_new:
      - ranking_logic
      - query_feature_helper
      - hydration_logic
      - telemetry_payload_builder
    allow:
      - import_forwarder
      - alias_forwarder
      - deletion

  tests/unit/test_cli.py:
    target_role: legacy CLI compatibility tests
    preferred_owner_modules:
      - tests/unit/test_cli_*.py
    block_new:
      - broad_new_test_group
    allow:
      - compatibility_assertion
      - deletion
```

The exact YAML schema should be validated by tests before the gate becomes
strict.

## Gate Behavior

The CLI should support:

```bash
uv run docling-system-hotspot-prevention-check --base HEAD
uv run docling-system-hotspot-prevention-check --staged
uv run docling-system-hotspot-prevention-check --format json
uv run docling-system-hotspot-prevention-check --strict
```

Minimum behavior:

- Inspect changed lines for known hotspot files.
- Classify additions as blocked implementation growth, allowed facade
  maintenance, deletion-only movement, or policy exception.
- Print the preferred owner module when a blocked addition is found.
- Return non-zero in `--strict` mode when blocked growth is detected.
- Return zero for a clean tree, deletion-only hotspot reductions, import-only
  compatibility forwarding, and explicitly configured exceptions.
- Require every exception to include an improvement case ID or milestone ID,
  an owner module, and an expiration or follow-up condition.

Classification should start conservative and testable. It does not need to be a
perfect semantic parser in the first milestone. It must reliably catch obvious
new functions, classes, enums, private helpers, command bodies, and large
implementation blocks added to known hotspots.

## Milestone Steps

### Step 0: Baseline And Policy Contract

Create the policy schema and current hotspot policy.

Scope:

- Add `config/hotspot_prevention.yaml`.
- Define known hotspot paths, target roles, preferred owner modules, blocked
  addition categories, allowed facade-maintenance categories, and exception
  fields.
- Add policy loading and validation tests.

Acceptance:

- Every current top hotspot from the architecture quality summary is listed or
  explicitly deferred with rationale.
- Every tracked hotspot has at least one preferred owner module.
- Policy validation fails for missing owner modules, empty block lists, or
  exceptions without case or milestone IDs.
- `uv run pytest -q tests/unit/test_hotspot_prevention.py` passes for policy
  validation.

### Step 1: Advisory Diff Analyzer

Build the analyzer and JSON/console report without strict failure by default.

Scope:

- Parse `git diff --numstat` and unified diffs for the working tree, staged
  diff, and a caller-provided base ref.
- Classify additions in tracked hotspot files.
- Emit a report with path, line counts, classification, preferred owner module,
  and remediation text.

Acceptance:

- A fixture diff that adds a new helper to `app/services/evidence.py` reports a
  blocked `private_helper` finding.
- A fixture diff that adds an import alias or forwarding wrapper reports an
  allowed facade-maintenance finding.
- A fixture diff that only deletes from a hotspot reports allowed reduction.
- JSON output has a stable `schema_name`, `schema_version`, `findings`, and
  `summary`.
- Advisory mode returns exit code 0 even when findings exist.

### Step 2: Strict Gate And CLI Wiring

Make the gate enforceable through a repo command.

Scope:

- Add the `docling-system-hotspot-prevention-check` entrypoint.
- Add `--strict`, `--staged`, `--base`, and `--format json`.
- Wire stable CLI tests for exit codes and report shape.

Acceptance:

- `--strict` returns non-zero for blocked hotspot implementation growth.
- `--strict` returns zero for the current clean checkout.
- CLI tests cover blocked, allowed, clean, and exception cases.
- The command output includes the preferred owner module and the exact policy
  rule that failed.

### Step 3: Architecture And Hygiene Integration

Make the gate part of the architecture closeout path.

Scope:

- Add the new command to `docs/architecture_plan_01.md` cross-milestone gates.
- Add the policy to `docs/architecture_boundaries.md`.
- Decide whether `uv run docling-system-hygiene-check` should invoke the gate
  immediately or whether the gate should remain a separate command for one
  milestone before integration.
- Add an improvement-case intake source only if the report shape is stable.

Acceptance:

- Architecture milestone closeout docs require the hotspot-prevention gate.
- The gate can run independently in local development.
- If integrated with hygiene, inherited file-budget debt does not cause false
  failures; only new hotspot growth fails.
- Architecture inspection and capability contracts remain green.

### Step 4: Ratchet And Exception Discipline

Prevent the gate from becoming another stale report.

Scope:

- Add a ratchet baseline or policy field that records the current known hotspot
  role and allowed edit categories.
- Require exceptions to reference an improvement case or milestone.
- Document how to retire exceptions after a split.

Acceptance:

- Exceptions without a case ID or milestone ID fail validation.
- Expired exceptions fail validation.
- A test proves that reducing a hotspot updates no exception and requires no
  policy bypass.
- A test proves that adding implementation to a known hotspot fails even when
  overall architecture inspection remains green.

## Required Verification

Minimum closeout commands:

```bash
git diff --check
uv run ruff check app tests
uv run pytest -q tests/unit/test_hotspot_prevention.py
uv run pytest -q tests/unit/test_architecture_quality.py tests/unit/test_hygiene.py
uv run docling-system-hotspot-prevention-check --strict
uv run docling-system-architecture-inspect
uv run docling-system-capability-contracts
uv run docling-system-architecture-quality-report --summary
```

If the command is integrated into CLI surfaces, also run the focused CLI tests
that cover the new entrypoint. If the implementation touches runtime service
behavior, DB models, API routes, storage artifacts, search behavior, evidence
runtime behavior, agent tasks, or workers, add the repo-standard DB-backed
suite:

```bash
DOCLING_SYSTEM_RUN_INTEGRATION=1 uv run pytest -q -rs
```

## Completion Criteria

The milestone is complete only when:

- A current clean checkout passes the strict gate.
- A fixture diff that adds implementation to each known hotspot fails the gate.
- A fixture diff that moves logic out of a hotspot and leaves a compatibility
  facade passes the gate.
- The gate tells Codex where the implementation should have gone.
- The architecture closeout docs require the gate before future hotspot split
  milestones.
- The change is locally committed as its own milestone slice.

## Stop Conditions

- The gate cannot distinguish deletion/move reductions from new implementation
  growth.
- Strict mode fails on the current clean checkout without a specific,
  documented policy exception.
- The first implementation depends on brittle LLM-authored prose instead of
  deterministic diff and policy checks.
- The exception mechanism allows permanent bypasses without ownership or
  follow-up.
- The gate creates broad churn in unrelated architecture-quality or hygiene
  internals before the policy contract is proven.

## Recommended Next Action

Implement this gate before starting more hotspot split work. The improvement
intake ratchet remains useful, but intake records debt after it exists; the
hotspot-prevention gate should block new centralization at diff time.
