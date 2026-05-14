from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol

from app.services import architecture_governance, runtime_health, telemetry
from app.services.runtime_health import RuntimePublicHealthResponse


class SystemGovernanceCapability(Protocol):
    def get_public_health(self) -> RuntimePublicHealthResponse: ...

    def get_runtime_status(
        self,
        process_identity: str | None = None,
    ) -> dict[str, Any]: ...

    def snapshot_metrics(self) -> dict[str, float]: ...

    def get_architecture_inspection_report(
        self,
        project_root: Path | None = None,
    ) -> dict[str, Any]: ...

    def summarize_architecture_measurements(
        self,
        path: str | Path | None = None,
        *,
        project_root: Path | None = None,
    ) -> dict[str, Any]: ...


class ServicesSystemGovernanceCapability:
    def get_public_health(self) -> RuntimePublicHealthResponse:
        return runtime_health.get_public_health()

    def get_runtime_status(
        self,
        process_identity: str | None = None,
    ) -> dict[str, Any]:
        return runtime_health.get_runtime_diagnostics(process_identity=process_identity)

    def snapshot_metrics(self) -> dict[str, float]:
        return telemetry.snapshot_metrics()

    def get_architecture_inspection_report(
        self,
        project_root: Path | None = None,
    ) -> dict[str, Any]:
        return architecture_governance.get_architecture_inspection_report(project_root)

    def summarize_architecture_measurements(
        self,
        path: str | Path | None = None,
        *,
        project_root: Path | None = None,
    ) -> dict[str, Any]:
        return architecture_governance.summarize_architecture_measurements(
            path,
            project_root=project_root,
        )


system_governance: SystemGovernanceCapability = ServicesSystemGovernanceCapability()
