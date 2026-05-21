from __future__ import annotations

import copy
import json
import tomllib
from pathlib import Path

from app.core.files import repo_root
from app.ontology_contract_cli import run_eval, run_report, run_validate
from app.services.ontology_contract_evaluations import evaluate_ontology_contract
from app.services.ontology_contract_runtime import load_ontology_contract_runtime_metadata
from app.services.ontology_contracts import (
    compile_legacy_view_payload,
    inspect_ontology_contract,
    load_ontology_contract_payload,
    write_ontology_contract_report,
)
from app.services.semantic_registry import load_semantic_registry_payload


def test_current_contract_compiles_legacy_views_in_sync_with_seed_registries() -> None:
    payload = load_ontology_contract_payload()
    summary = inspect_ontology_contract(payload, strict=True, project_root=repo_root())
    legacy_views = {row["view_key"]: row for row in summary["legacy_views"]}

    assert summary["valid"] is True
    assert summary["semantic_evaluation_corpus"]["document_count"] == 0
    assert summary["semantic_evaluation_corpus"]["ontology_slice_expectation_count"] == 5
    assert (
        summary["semantic_evaluation_corpus"]["ontology_competency_family_expectation_count"]
        == 4
    )
    assert summary["semantic_evaluation_corpus"]["ontology_competency_question_count"] == 8
    assert legacy_views["upper_ontology_yaml"]["in_sync"] is True
    assert legacy_views["semantic_registry_yaml"]["in_sync"] is True
    assert compile_legacy_view_payload(
        payload,
        "upper_ontology_yaml",
    ) == load_semantic_registry_payload(repo_root() / "config" / "upper_ontology.yaml")
    assert compile_legacy_view_payload(
        payload,
        "semantic_registry_yaml",
    ) == load_semantic_registry_payload(repo_root() / "config" / "semantic_registry.yaml")


def test_inspect_ontology_contract_reports_missing_required_layer_kind_in_strict_mode() -> None:
    payload = copy.deepcopy(load_ontology_contract_payload())
    payload["layers"] = [
        layer for layer in payload["layers"] if layer.get("layer_kind") != "report_semantics"
    ]

    summary = inspect_ontology_contract(payload, strict=True, project_root=repo_root())

    assert summary["valid"] is False
    assert "Missing required ontology layer_kind: report_semantics" in summary["errors"]


def test_write_ontology_contract_report_roundtrips(tmp_path: Path) -> None:
    payload = load_ontology_contract_payload()
    report = inspect_ontology_contract(payload, strict=True, project_root=repo_root())
    report_path = tmp_path / "ontology_contract_report.md"

    written_path = write_ontology_contract_report(report_path, report=report)

    assert written_path == report_path
    text = written_path.read_text()
    assert "# Ontology Contract Report" in text
    assert "upper_ontology_yaml" in text
    assert "Ontology slice expectation count: `5`" in text


def test_ontology_evaluation_passes_current_contract() -> None:
    payload = load_ontology_contract_payload()

    report = evaluate_ontology_contract(payload, project_root=repo_root())

    assert report["overall_passed"] is True
    assert report["slice_fail_count"] == 0
    assert report["competency_family_fail_count"] == 0
    assert report["global_entity_type_count"] >= 19
    assert report["global_relation_count"] >= 20


def test_ontology_evaluation_fails_when_required_report_semantics_relation_is_removed() -> None:
    payload = copy.deepcopy(load_ontology_contract_payload())
    report_slice = next(
        slice_row for slice_row in payload["slices"] if slice_row["slice_key"] == "report_semantics"
    )
    report_slice["relation_keys"] = [
        key for key in report_slice["relation_keys"] if key != "claim_supported_by_evidence"
    ]

    report = evaluate_ontology_contract(payload, project_root=repo_root())

    assert report["overall_passed"] is False
    report_slice_result = next(
        row for row in report["slice_results"] if row["slice_key"] == "report_semantics"
    )
    claim_support_result = next(
        row for row in report["competency_family_results"] if row["family_key"] == "claim_support"
    )
    assert "claim_supported_by_evidence" in report_slice_result["missing_declared_relation_keys"]
    assert "claim_supported_by_evidence" in claim_support_result["missing_declared_relation_keys"]


def test_ontology_contract_runtime_metadata_exposes_slices_and_competency_families() -> None:
    metadata = load_ontology_contract_runtime_metadata()

    assert metadata["contract_path"] == "config/ontology/docling_ontology_contract.json"
    assert metadata["ontology_slice_count"] == 5
    assert metadata["competency_family_count"] == 4
    assert metadata["ontology_slices"][0]["slice_key"] == "core"
    assert metadata["ontology_slices"][0]["slice_sha256"]
    assert metadata["competency_families"][0]["family_key"] == "claim_support"


def test_ontology_contract_cli_validate_and_report(capsys, tmp_path: Path) -> None:
    report_path = tmp_path / "ontology_contract_report.md"
    eval_report_path = tmp_path / "ontology_evaluation_report.json"

    validate_exit_code = run_validate(["--strict"])
    validate_output = json.loads(capsys.readouterr().out)

    report_exit_code = run_report(["--strict", "--output", str(report_path)])
    report_output = json.loads(capsys.readouterr().out)

    eval_exit_code = run_eval(["--output", str(eval_report_path)])
    eval_output = json.loads(capsys.readouterr().out)

    assert validate_exit_code == 0
    assert validate_output["valid"] is True
    assert report_exit_code == 0
    assert report_output["valid"] is True
    assert eval_exit_code == 0
    assert eval_output["overall_passed"] is True
    assert report_path.is_file()
    assert eval_report_path.is_file()


def test_ontology_contract_cli_entrypoints_include_eval() -> None:
    scripts = tomllib.loads(Path("pyproject.toml").read_text())["project"]["scripts"]

    assert (
        scripts["docling-system-ontology-contract-validate"]
        == "app.ontology_contract_cli:run_validate"
    )
    assert (
        scripts["docling-system-ontology-contract-report"]
        == "app.ontology_contract_cli:run_report"
    )
    assert scripts["docling-system-ontology-eval"] == "app.ontology_contract_cli:run_eval"
