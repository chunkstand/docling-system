from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

import app.services.evaluation_fixtures as fixture_owners
import app.services.evaluation_scoring as scoring_owners
from app.core.files import path_exists
from app.db.models import DocumentFigure, DocumentRun, DocumentTable
from app.services.evaluation_fixtures import EvaluationThresholds


def _summarize_structural_checks(
    tables: list[object], figures: list[object], thresholds: EvaluationThresholds
) -> dict:
    checks: list[dict] = []

    actual_table_count = len(tables)
    if thresholds.expected_logical_table_count is not None:
        passed = (
            abs(actual_table_count - thresholds.expected_logical_table_count)
            <= thresholds.logical_table_tolerance
        )
        checks.append(
            {
                "name": "logical_table_count",
                "passed": passed,
                "expected": thresholds.expected_logical_table_count,
                "actual": actual_table_count,
                "tolerance": thresholds.logical_table_tolerance,
            }
        )

    actual_figure_count = len(figures)
    if thresholds.expected_figure_count is not None:
        passed = (
            abs(actual_figure_count - thresholds.expected_figure_count)
            <= thresholds.figure_count_tolerance
        )
        checks.append(
            {
                "name": "figure_count",
                "passed": passed,
                "expected": thresholds.expected_figure_count,
                "actual": actual_figure_count,
                "tolerance": thresholds.figure_count_tolerance,
            }
        )

    captioned_figure_count = sum(1 for figure in figures if getattr(figure, "caption", None))
    if thresholds.minimum_captioned_figure_count is not None:
        checks.append(
            {
                "name": "minimum_captioned_figure_count",
                "passed": captioned_figure_count >= thresholds.minimum_captioned_figure_count,
                "expected_minimum": thresholds.minimum_captioned_figure_count,
                "actual": captioned_figure_count,
            }
        )

    figures_with_provenance = sum(
        1
        for figure in figures
        if (fixture_owners._metadata_for_row(figure).get("provenance") or [])
    )
    if thresholds.minimum_figures_with_provenance is not None:
        checks.append(
            {
                "name": "minimum_figures_with_provenance",
                "passed": figures_with_provenance >= thresholds.minimum_figures_with_provenance,
                "expected_minimum": thresholds.minimum_figures_with_provenance,
                "actual": figures_with_provenance,
            }
        )

    figures_with_artifacts = sum(
        1
        for figure in figures
        if path_exists(getattr(figure, "json_path", None))
        and path_exists(getattr(figure, "yaml_path", None))
    )
    if thresholds.minimum_figures_with_artifacts is not None:
        checks.append(
            {
                "name": "minimum_figures_with_artifacts",
                "passed": figures_with_artifacts >= thresholds.minimum_figures_with_artifacts,
                "expected_minimum": thresholds.minimum_figures_with_artifacts,
                "actual": figures_with_artifacts,
            }
        )

    if thresholds.expected_figure_captions_present:
        expected_captions = [
            fixture_owners._normalized_caption_text(expected)
            for expected in thresholds.expected_figure_captions_present
        ]
        available_captions = [
            fixture_owners._normalized_caption_text(getattr(figure, "caption", None))
            for figure in figures
        ]
        missing_captions = [
            expected
            for expected in expected_captions
            if not any(expected.lower() in caption.lower() for caption in available_captions)
        ]
        checks.append(
            {
                "name": "expected_figure_captions_present",
                "passed": not missing_captions,
                "expected": expected_captions,
                "missing": missing_captions,
            }
        )

    merged_tables = [
        table for table in tables if fixture_owners._metadata_for_row(table).get("is_merged")
    ]
    matched_merged_ids: set[object] = set()
    expectation_results: list[dict] = []
    for expectation in thresholds.expected_merged_tables:
        matches = [
            table
            for table in merged_tables
            if scoring_owners._table_matches_merge_expectation(table, expectation)
        ]
        matched_merged_ids.update(id(table) for table in matches)
        expectation_results.append(
            {
                "description": expectation.description,
                "passed": bool(matches),
                "match_count": len(matches),
                "matches": [
                    {
                        "label": scoring_owners._table_label(table),
                        "page_from": getattr(table, "page_from", None),
                        "page_to": getattr(table, "page_to", None),
                        "source_segment_count": scoring_owners._source_segment_count(table),
                        "overlay_family_key": fixture_owners._metadata_for_row(table).get(
                            "overlay_family_key"
                        ),
                    }
                    for table in matches
                ],
            }
        )

    missing_expected_merges = [
        item["description"] for item in expectation_results if not item["passed"]
    ]
    checks.append(
        {
            "name": "expected_merged_tables",
            "passed": len(missing_expected_merges) <= thresholds.maximum_unexpected_splits,
            "expected_count": len(thresholds.expected_merged_tables),
            "actual_matched_count": len(expectation_results) - len(missing_expected_merges),
            "missing": missing_expected_merges,
            "tolerance": thresholds.maximum_unexpected_splits,
            "details": expectation_results,
        }
    )

    unexpected_merged_tables: list[dict] = []
    if thresholds.enforce_unexpected_merged_tables:
        unexpected_merged_tables = [
            {
                "label": scoring_owners._table_label(table),
                "page_from": getattr(table, "page_from", None),
                "page_to": getattr(table, "page_to", None),
                "merge_reason": fixture_owners._metadata_for_row(table).get("merge_reason"),
            }
            for table in merged_tables
            if id(table) not in matched_merged_ids
        ]
    checks.append(
        {
            "name": "unexpected_merged_tables",
            "passed": len(unexpected_merged_tables) <= thresholds.maximum_unexpected_merges,
            "enforced": thresholds.enforce_unexpected_merged_tables,
            "limit": thresholds.maximum_unexpected_merges,
            "actual": len(unexpected_merged_tables),
            "details": unexpected_merged_tables,
            "observed_merged_table_count": len(merged_tables),
        }
    )

    passed_checks = sum(1 for check in checks if check["passed"])
    failed_checks = len(checks) - passed_checks
    return {
        "passed": failed_checks == 0,
        "check_count": len(checks),
        "passed_checks": passed_checks,
        "failed_checks": failed_checks,
        "checks": checks,
    }


def _evaluate_structural_checks(
    session: Session, run: DocumentRun, thresholds: EvaluationThresholds
) -> dict:
    tables = (
        session.execute(
            select(DocumentTable)
            .where(DocumentTable.run_id == run.id)
            .order_by(DocumentTable.table_index)
        )
        .scalars()
        .all()
    )
    figures = (
        session.execute(
            select(DocumentFigure)
            .where(DocumentFigure.run_id == run.id)
            .order_by(DocumentFigure.figure_index)
        )
        .scalars()
        .all()
    )
    return _summarize_structural_checks(tables, figures, thresholds)
