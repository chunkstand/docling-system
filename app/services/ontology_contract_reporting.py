from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from app.core.files import repo_root


def render_ontology_contract_report(report: dict[str, Any]) -> str:
    lines = [
        "# Ontology Contract Report",
        "",
        f"- Contract: `{report['contract_name']}`",
        f"- Version: `{report['contract_version']}`",
        f"- Upper ontology version: `{report['upper_ontology_version']}`",
        f"- Valid: `{report['valid']}`",
        f"- Strict mode: `{report['strict']}`",
        "",
        "## Layers",
        "",
        "| Layer | Kind | Version | Legacy | Entities | Categories | Concepts | Relations |",
        "| --- | --- | --- | --- | ---: | ---: | ---: | ---: |",
    ]
    for layer in report["layers"]:
        lines.append(
            "| {layer_key} | {layer_kind} | {layer_version} | {legacy} | {entity_type_count} | "
            "{category_count} | {concept_count} | {relation_count} |".format(
                legacy="yes" if layer["include_in_legacy_registry"] else "no",
                **layer,
            )
        )
    lines.extend(
        [
            "",
            "## Slices",
            "",
            "| Slice | Status | Layers | Entities | Relations |",
            "| --- | --- | --- | ---: | ---: |",
        ]
    )
    for slice_row in report["slices"]:
        lines.append(
            "| {slice_key} | {status} | {layers} | {entity_type_count} | {relation_count} |".format(
                layers=", ".join(slice_row["layer_keys"]),
                **slice_row,
            )
        )
    lines.extend(
        [
            "",
            "## Competency Families",
            "",
            "| Family | Status | Slices |",
            "| --- | --- | --- |",
        ]
    )
    for family in report["competency_families"]:
        lines.append(
            "| {family_key} | {status} | {slices} |".format(
                slices=", ".join(family["slice_keys"]),
                **family,
            )
        )
    lines.extend(
        [
            "",
            "## Legacy Views",
            "",
            "| View | Path | Exists | In Sync | Entities | Categories | Concepts | Relations |",
            "| --- | --- | --- | --- | ---: | ---: | ---: | ---: |",
        ]
    )
    for view in report["legacy_views"]:
        lines.append(
            "| {view_key} | `{path}` | {exists} | {in_sync} | {entity_type_count} | "
            "{category_count} | {concept_count} | {relation_count} |".format(**view)
        )
    corpus = report["semantic_evaluation_corpus"]
    lines.extend(
        [
            "",
            "## Semantic Evaluation Corpus",
            "",
            f"- Path: `{corpus['path']}`",
            f"- Exists: `{corpus['exists']}`",
            f"- Corpus name: `{corpus['corpus_name']}`",
            f"- Document count: `{corpus['document_count']}`",
            f"- Query count: `{corpus['query_count']}`",
            f"- Ontology slice expectation count: `{corpus['ontology_slice_expectation_count']}`",
            (
                "- Ontology competency family expectation count: "
                f"`{corpus['ontology_competency_family_expectation_count']}`"
            ),
            (
                "- Ontology competency question count: "
                f"`{corpus['ontology_competency_question_count']}`"
            ),
        ]
    )
    if report["warnings"]:
        lines.extend(["", "## Warnings", ""])
        lines.extend(f"- {warning}" for warning in report["warnings"])
    if report["errors"]:
        lines.extend(["", "## Errors", ""])
        lines.extend(f"- {error}" for error in report["errors"])
    return "\n".join(lines) + "\n"


def write_ontology_contract_report(
    path: str | Path,
    *,
    report: dict[str, Any],
    project_root: Path | None = None,
) -> Path:
    root = project_root or repo_root()
    raw_path = Path(path)
    resolved_path = raw_path if raw_path.is_absolute() else root / raw_path
    resolved_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_path.write_text(render_ontology_contract_report(report))
    return resolved_path


def semantic_evaluation_corpus_summary(
    *,
    project_root: Path,
    path: str | Path | None = None,
) -> dict[str, Any]:
    raw_path = Path(path) if path is not None else Path("docs") / "semantic_evaluation_corpus.yaml"
    resolved_path = raw_path if raw_path.is_absolute() else project_root / raw_path
    if not resolved_path.is_file():
        return {
            "path": str(raw_path),
            "exists": False,
            "corpus_name": None,
            "document_count": 0,
            "query_count": 0,
            "ontology_slice_expectation_count": 0,
            "ontology_competency_family_expectation_count": 0,
            "ontology_competency_question_count": 0,
        }
    payload = yaml.safe_load(resolved_path.read_text()) or {}
    documents = payload.get("documents") or []
    ontology_eval = payload.get("ontology_evaluation") or {}
    if not isinstance(ontology_eval, dict):
        ontology_eval = {}
    slice_expectations = ontology_eval.get("slice_expectations") or []
    family_expectations = ontology_eval.get("competency_family_expectations") or []
    query_count = 0
    question_count = 0
    for document in documents:
        if isinstance(document, dict):
            query_count += len(document.get("queries") or [])
    for family in family_expectations:
        if isinstance(family, dict):
            question_count += len(family.get("competency_questions") or [])
    return {
        "path": str(raw_path),
        "exists": True,
        "corpus_name": payload.get("corpus_name"),
        "document_count": len(documents),
        "query_count": query_count,
        "ontology_slice_expectation_count": len(slice_expectations),
        "ontology_competency_family_expectation_count": len(family_expectations),
        "ontology_competency_question_count": question_count,
    }


__all__ = [
    "render_ontology_contract_report",
    "semantic_evaluation_corpus_summary",
    "write_ontology_contract_report",
]
