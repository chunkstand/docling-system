# Architecture Boundaries

This repository stays a modular monolith. Core runtime boundaries are enforced
inside the process before any service decomposition is justified.

## Public Capability Interfaces

API routers and worker launchers depend on `app.services.capabilities`.
Those facades are the public entrypoints for the large implementation domains:

- `run_lifecycle`: document ingest, inspection, active-run artifact resolution,
  and ingest worker launch
- `retrieval`: search, search history, replay, harness evaluation, and chat
- `evaluation`: document evaluations and eval-workbench inspection
- `semantics`: semantic pass inspection, review, and backfill
- `agent_orchestration`: agent-task CRUD, context, artifacts, approvals,
  analytics, and agent-worker launch

The existing service modules behind those facades remain implementation
modules. They may collaborate internally, but externally reachable boundaries
should not import them directly.

The facade surface is a machine-readable contract. The committed contract map
is `docs/capability_contract_map.json`; regenerate it with
`uv run docling-system-capability-contracts --write-map` after intentional
facade changes. The map records each facade's Protocol methods, implementation
owner modules, operation kind, parameter annotations, and return annotations.
Protocol methods are the public surface. The concrete `Services*Capability`
classes must not expose extra public methods outside the Protocol.

## Guardrail

`tests/unit/test_api_architecture.py` rejects direct imports from API routers and
worker launchers into the large implementation modules listed above. Add new
externally reachable behavior to a capability facade first, then call the
facade from the router or worker boundary.

Boundary modules also avoid importing `app.db.models` directly. They may accept
database sessions from FastAPI dependencies, but ORM row lookup and active-run
scoping belong behind the service capability facades.

Service modules also avoid importing underscore-prefixed helpers from other
service modules. When shared behavior crosses a module boundary, expose a public
helper or move it to an explicitly shared module.

`uv run docling-system-architecture-inspect` is the top-level architecture
inspection command. It emits a machine-readable architecture map and validates
the API route, agent action, capability facade surface, service import, data
model import, improvement intake, and architecture-documentation contracts as
one boundary fitness function. `uv run docling-system-hygiene-check` runs the same
inspection by default.

Architecture inspection rules are first-class registry entries with stable
rule IDs, linked contracts, descriptions, default severities, source paths, and
callable checkers. The architecture contract map exposes that rule inventory so
agents can inspect both the boundary model and the checks that enforce it.
Architecture measurement snapshots count violations by those stable rule IDs and
by linked contract, so trend summaries can identify which boundary checks are
improving or regressing. The architecture contract map also exposes the
measurement, summary, and delta field lists so agents can read the trend
contract without reverse-engineering the JSONL history.

The committed map lives at `docs/architecture_contract_map.json`; regenerate it
with `uv run docling-system-architecture-inspect --write-map` after intentional
boundary changes. Inspection severity is governed by
`config/architecture_inspection.yaml`, whose default policy treats every
non-ignored violation as an error. Severity overrides can target a stable rule
with `rule.<rule_id>`, a contract, or a contract field.

## Architecture Decisions

Architecture decisions are source-controlled contracts, not only prose in
review threads. The canonical registry is `docs/architecture_decisions.yaml`;
regenerate the machine-readable map with
`uv run docling-system-architecture-decisions --write-map` after intentional
decision changes.

`app.architecture_decisions` validates decision shape, map drift, linked source
paths, and whether every major architecture contract-map entry has a linked
decision. `uv run docling-system-architecture-inspect` runs that validation as
part of the architecture fitness function.
Current architecture contracts must be linked to accepted decisions, and the
architecture contract map repeats each contract's `decision_ids` so agents can
move from structure to rationale without joining separate files by hand.

## API Route Capability Contracts

Remote API permissions are a closed route contract, not free-form router
strings. Capability names live in `app.api.capabilities`; routers reference
those constants when calling `require_api_capability(...)`.

`app.api.route_contracts` builds an inspectable manifest from the actual
FastAPI app: method, path, route name, endpoint, capability, public exemption,
mutation-key gate, and response model. `tests/unit/test_api_route_contracts.py`
validates that every non-exempt public route has exactly one known capability
and that every mutating route also carries `require_api_key_for_mutations`.
The only public remote exemptions are `/` and `/health`.

## Agent Action Contracts

Agent-task definitions are machine-checked contracts. Each registered action
declares its owning capability, input model, output model/schema metadata,
input example, side-effect level, approval requirement, and context-builder
name. `tests/unit/test_agent_action_contracts.py` validates those contracts and
checks that every named context builder is registered.
`GET /agent-tasks/actions` exposes the same capability and context-builder
metadata so agents can inspect the public task surface without reading private
registry internals.

The contract vocabulary is intentionally closed: capabilities, definition
kinds, and side-effect levels are enumerated in `app.services.agent_actions`.
Changing those categories should be a deliberate contract change, not an
accidental string addition in one registry entry.

## Improvement Intake Boundary

Improvement-case intake is owned by `app.services.improvement_case_intake`.
CLI, API, worker, or UI callers should delegate source selection, observation
collection, and deduped import to that service facade instead of branching over
hygiene, eval-workbench, and agent-task tables at the boundary.

The facade exposes `ImprovementCaseImportRequest` and
`ImprovementCaseImportResult` as the reusable machine contract. Boundary callers
should pass that typed request, or the equivalent keyword arguments, and render
the typed result without reconstructing import payloads themselves.

Improvement-case lifecycle transitions are owned by
`app.services.improvement_case_lifecycle`. CLI, API, worker, or UI callers
should use that service when deploying or measuring a case so late-stage status
changes always pass the registry contract before being written.

Architecture measurement history is owned by `app.architecture_measurements`.
The history is local JSONL runtime data under
`storage/architecture_inspections/history.jsonl`; source control versions the
recording and summary mechanism, while `storage/` tracks local executions. The
read-only API surface is owned by the `system_governance` service capability
facade and exposed through `GET /architecture/inspection` and
`GET /architecture/measurements/summary` under the `system:read` capability.
The summary response includes commit freshness fields so agents can distinguish
current inspection status from stale local measurement history.
