from __future__ import annotations

from pathlib import Path

from app.architecture_quality import (
    build_architecture_quality_report,
    build_architecture_quality_summary,
)
from app.hotspot_prevention_policy import HotspotPolicy, HotspotRouting, HotspotRule


def _inspection_report() -> dict:
    return {
        "valid": True,
        "violation_count": 0,
        "measurement": {},
        "architecture_map": {"contracts": []},
    }


def _empty_policy() -> HotspotPolicy:
    return HotspotPolicy(
        schema_name="hotspot_prevention_policy",
        schema_version="1.0",
        known_hotspots={},
    )


def test_architecture_quality_report_excludes_routing_traps_from_routed_queue(
    monkeypatch,
    tmp_path: Path,
) -> None:
    app_dir = tmp_path / "app"
    (app_dir / "db").mkdir(parents=True)
    (app_dir / "services").mkdir(parents=True)
    (app_dir / "db" / "models.py").write_text("MODEL = object()\n")
    (app_dir / "services" / "agent_tasks.py").write_text(
        "\n".join(
            [
                "def create_agent_task():",
                "    return None",
                "",
                "def update_agent_task():",
                "    return None",
            ]
        )
    )

    monkeypatch.setattr(
        "app.architecture_quality.build_capability_contract_map",
        lambda _root: {"facades": []},
    )
    monkeypatch.setattr(
        "app.architecture_quality.collect_git_churn_metrics",
        lambda _root: {
            "app/db/models.py": {"changes_30d": 50, "changes_90d": 80},
            "app/services/agent_tasks.py": {"changes_30d": 25, "changes_90d": 40},
        },
    )
    monkeypatch.setattr(
        "app.architecture_quality.load_hotspot_policy",
        lambda project_root=None: HotspotPolicy(
            schema_name="hotspot_prevention_policy",
            schema_version="1.0",
            known_hotspots={
                "app/db/models.py": HotspotRule(
                    relative_path="app/db/models.py",
                    target_role="compatibility facade",
                    preferred_owner_modules=("app/db/model_domains/",),
                    block_new=("orm_class",),
                    allow=("import_forwarder",),
                    routing=HotspotRouting(
                        status="compatibility_facade_trap",
                        reason="Compatibility facade is already reduced.",
                        route_to_case_ids=("IC-ROUTE-DB",),
                        route_to_paths=("app/db/model_domains/audit_and_evidence.py",),
                        route_to_plan_paths=("docs/db_models_residual_owner_family_milestone_plan.md",),
                    ),
                )
            },
        ),
    )

    report = build_architecture_quality_report(
        tmp_path,
        inspection_report=_inspection_report(),
        include_hygiene=False,
    )

    assert report["summary"]["top_hotspot_paths"][0] == "app/db/models.py"
    assert report["summary"]["top_routed_hotspot_paths"] == ["app/services/agent_tasks.py"]
    assert report["summary"]["top_broader_rebaseline_paths"] == []
    assert report["summary"]["broader_rebaseline_candidate_count"] == 0
    assert report["summary"]["routing_trap_paths"] == ["app/db/models.py"]
    assert report["summary"]["stale_facade_hotspot_count"] == 1
    assert report["hotspots"][0]["routing_status"] == "compatibility_facade_trap"
    assert report["hotspots"][0]["selected_for_routed_queue"] is False
    assert report["hotspots"][0]["route_to_case_ids"] == ["IC-ROUTE-DB"]
    assert report["raw_improvement_case_candidates"][0]["artifact_target_path"] == (
        "app/db/models.py"
    )
    assert report["improvement_case_candidates"][0]["artifact_target_path"] == (
        "app/services/agent_tasks.py"
    )


def test_architecture_quality_summary_includes_routed_fields(
    monkeypatch,
    tmp_path: Path,
) -> None:
    (tmp_path / "app").mkdir()
    (tmp_path / "app" / "small.py").write_text("def ok():\n    return 1\n")

    monkeypatch.setattr(
        "app.architecture_quality.build_capability_contract_map",
        lambda _root: {"facades": []},
    )
    monkeypatch.setattr("app.architecture_quality.collect_git_churn_metrics", lambda _root: {})
    monkeypatch.setattr(
        "app.architecture_quality.load_hotspot_policy",
        lambda project_root=None: _empty_policy(),
    )

    summary = build_architecture_quality_summary(
        tmp_path,
        inspection_report=_inspection_report(),
    )

    assert summary["top_routed_hotspot_paths"] == ["app/small.py"]
    assert summary["top_broader_rebaseline_paths"] == []
    assert summary["broader_rebaseline_candidate_count"] == 0
    assert summary["routing_trap_paths"] == []
    assert summary["stale_facade_hotspot_count"] == 0


def test_architecture_quality_report_excludes_accepted_residual_from_routed_queue(
    monkeypatch,
    tmp_path: Path,
) -> None:
    app_dir = tmp_path / "app"
    (app_dir / "api" / "routers").mkdir(parents=True)
    (app_dir / "services").mkdir(parents=True)
    (app_dir / "api" / "main.py").write_text(
        "\n".join(f"def route_{index}():\n    return {index}\n" for index in range(30))
    )
    (app_dir / "api" / "routers" / "agent_tasks.py").write_text(
        "\n".join(f"def handler_{index}():\n    return {index}\n" for index in range(20))
    )

    monkeypatch.setattr(
        "app.architecture_quality.build_capability_contract_map",
        lambda _root: {"facades": []},
    )
    monkeypatch.setattr(
        "app.architecture_quality.collect_git_churn_metrics",
        lambda _root: {
            "app/api/main.py": {"changes_30d": 30, "changes_90d": 50},
            "app/api/routers/agent_tasks.py": {"changes_30d": 20, "changes_90d": 30},
        },
    )
    monkeypatch.setattr(
        "app.architecture_quality.load_hotspot_policy",
        lambda project_root=None: HotspotPolicy(
            schema_name="hotspot_prevention_policy",
            schema_version="1.0",
            known_hotspots={
                "app/api/main.py": HotspotRule(
                    relative_path="app/api/main.py",
                    target_role="api bootstrap",
                    preferred_owner_modules=("app/api/routers/",),
                    block_new=("route_family_implementation",),
                    allow=("router_registration",),
                    routing=HotspotRouting(
                        status="accepted_residual",
                        reason="Bootstrap root is already intentional and under budget.",
                        route_to_case_ids=("IC-API-BOOTSTRAP",),
                        route_to_paths=("app/api/routers/agent_tasks.py",),
                        route_to_plan_paths=("docs/open_owner_backlog_resolution_milestone_plan.md",),
                    ),
                )
            },
        ),
    )

    report = build_architecture_quality_report(
        tmp_path,
        inspection_report=_inspection_report(),
        include_hygiene=False,
    )

    assert report["summary"]["top_hotspot_paths"][0] == "app/api/main.py"
    assert report["summary"]["top_routed_hotspot_paths"] == ["app/api/routers/agent_tasks.py"]
    assert report["summary"]["top_broader_rebaseline_paths"] == []
    assert report["summary"]["broader_rebaseline_candidate_count"] == 0
    assert report["summary"]["routing_trap_paths"] == []
    assert report["hotspots"][0]["routing_status"] == "accepted_residual"
    assert report["hotspots"][0]["selected_for_routed_queue"] is False
    assert report["hotspots"][0]["route_to_case_ids"] == ["IC-API-BOOTSTRAP"]


def test_architecture_quality_report_surfaces_broader_rebaseline_candidates_when_queue_empty(
    monkeypatch,
    tmp_path: Path,
) -> None:
    app_dir = tmp_path / "app" / "services"
    app_dir.mkdir(parents=True)
    (app_dir / "search.py").write_text(
        "\n".join(f"def search_{index}():\n    return {index}\n" for index in range(18))
    )
    (app_dir / "search_retrieval_primitives.py").write_text(
        "\n".join(
            f"def retrieval_{index}():\n    return {index}\n"
            for index in range(310)
        )
    )
    (app_dir / "search_harnesses.py").write_text(
        "\n".join(f"def harness_{index}():\n    return {index}\n" for index in range(305))
    )

    monkeypatch.setattr(
        "app.architecture_quality.build_capability_contract_map",
        lambda _root: {"facades": []},
    )
    monkeypatch.setattr(
        "app.architecture_quality.collect_git_churn_metrics",
        lambda _root: {
            "app/services/search.py": {"changes_30d": 1, "changes_90d": 4},
            "app/services/search_retrieval_primitives.py": {
                "changes_30d": 2,
                "changes_90d": 5,
            },
            "app/services/search_harnesses.py": {"changes_30d": 1, "changes_90d": 3},
        },
    )
    monkeypatch.setattr(
        "app.architecture_quality._improvement_case_registry_index",
        lambda _root: (
            {},
            {
                "IC-SEARCH": {"status": "deployed", "deployed_ref": "abc123"},
            },
        ),
    )
    monkeypatch.setattr(
        "app.architecture_quality._build_hotspots",
        lambda **_kwargs: [
            {
                "relative_path": "app/services/search.py",
                "risk_score": 120.0,
                "line_count": 36,
                "public_function_count": 18,
                "private_function_count": 0,
                "class_count": 0,
                "changes_30d": 1,
                "changes_90d": 4,
                "hygiene_finding_count": 0,
                "open_improvement_case_count": 0,
                "hygiene_findings": [],
            }
        ],
    )
    monkeypatch.setattr(
        "app.architecture_quality.load_hotspot_policy",
        lambda project_root=None: HotspotPolicy(
            schema_name="hotspot_prevention_policy",
            schema_version="1.0",
            known_hotspots={
                "app/services/search.py": HotspotRule(
                    relative_path="app/services/search.py",
                    target_role="compatibility facade",
                    preferred_owner_modules=("app/services/search_retrieval_primitives.py",),
                    block_new=("search_family_implementation",),
                    allow=("facade_forwarder",),
                    routing=HotspotRouting(
                        status="compatibility_facade_trap",
                        reason="Search facade is already reduced.",
                        route_to_case_ids=("IC-SEARCH",),
                        route_to_paths=(
                            "app/services/search_retrieval_primitives.py",
                            "app/services/search_harnesses.py",
                        ),
                        route_to_plan_paths=(
                            "docs/search_compatibility_facade_boundary_milestone_plan.md",
                        ),
                    ),
                )
            },
        ),
    )

    report = build_architecture_quality_report(
        tmp_path,
        inspection_report=_inspection_report(),
        include_hygiene=False,
    )

    assert report["summary"]["top_routed_hotspot_paths"] == []
    assert report["summary"]["top_broader_rebaseline_paths"] == [
        "app/services/search_retrieval_primitives.py",
        "app/services/search_harnesses.py",
    ]
    assert report["summary"]["broader_rebaseline_candidate_count"] == 2
    assert report["broader_rebaseline_candidates"][0]["artifact_target_path"] == (
        "app/services/search_retrieval_primitives.py"
    )
    assert report["broader_rebaseline_candidates"][0]["source_hotspot_path"] == (
        "app/services/search.py"
    )
    assert report["broader_rebaseline_candidates"][0]["route_to_case_statuses"] == {
        "IC-SEARCH": "deployed"
    }
