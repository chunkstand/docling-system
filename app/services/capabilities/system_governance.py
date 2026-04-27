from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol

from app.services import architecture_governance, runtime, telemetry


class SystemGovernanceCapability(Protocol):
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
    def get_runtime_status(
        self,
        process_identity: str | None = None,
    ) -> dict[str, Any]:
        return runtime.get_runtime_status(process_identity=process_identity)

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
