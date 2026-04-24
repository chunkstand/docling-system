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

## Agent Action Contracts

Agent-task definitions are machine-checked contracts. Each registered action
declares its owning capability, input model, output model/schema metadata,
input example, side-effect level, approval requirement, and context-builder
name. `tests/unit/test_agent_action_contracts.py` validates those contracts and
checks that every named context builder is registered.
