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

## Guardrail

`tests/unit/test_api_architecture.py` rejects direct imports from API routers and
worker launchers into the large implementation modules listed above. Add new
externally reachable behavior to a capability facade first, then call the
facade from the router or worker boundary.

Service modules also avoid importing underscore-prefixed helpers from other
service modules. When shared behavior crosses a module boundary, expose a public
helper or move it to an explicitly shared module.

`uv run docling-system-architecture-inspect` is the top-level architecture
inspection command. It emits a machine-readable architecture map and validates
the API route, agent action, capability facade, service import, improvement
intake, and architecture-documentation contracts as one boundary fitness
function. `uv run docling-system-hygiene-check` runs the same inspection by
default.

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
