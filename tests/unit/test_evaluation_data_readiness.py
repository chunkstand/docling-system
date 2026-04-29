from __future__ import annotations

import yaml

from app.services.evaluation_data_readiness import (
    CLAIM_FEEDBACK_LABELS,
    CLAIM_FEEDBACK_STATUSES,
    FEEDBACK_TYPES,
    REPLAY_SOURCE_TYPES,
    build_readiness_gates,
    summarize_evaluation_corpora,
    summarize_readiness,
)


def test_summarize_evaluation_corpora_counts_query_families_and_db_matches(tmp_path) -> None:
    manual = tmp_path / "manual.yaml"
    auto = tmp_path / "auto.yaml"
    manual.write_text(
        yaml.safe_dump(
            {
                "documents": [
                    {
                        "source_filename": "gold.pdf",
                        "thresholds": {
                            "expected_logical_table_count": 1,
                            "expected_figure_count": 0,
                            "expected_merged_tables": [{"logical_table_key": "table:a"}],
                            "expected_top_n_table_hit_queries": [{"query": "table"}],
                            "expected_top_n_chunk_hit_queries": [{"query": "chunk"}],
                            "queries": [{"query": "cross doc"}],
                            "expected_answer_queries": [{"query": "answer"}],
                        },
                    }
                ]
            }
        )
    )
    auto.write_text(
        yaml.safe_dump(
            {
                "documents": [
                    {
                        "source_filename": "auto.pdf",
                        "thresholds": {
                            "expected_top_n_table_hit_queries": [{"query": "table"}],
                            "expected_top_n_chunk_hit_queries": [{"query": "chunk"}],
                        },
                    }
                ]
            }
        )
    )

    summary = summarize_evaluation_corpora(
        manual_corpus_path=manual,
        auto_corpus_path=auto,
        db_source_filenames={"gold.pdf"},
    )

    assert summary["manual"]["documents"] == 1
    assert summary["manual"]["table_queries"] == 1
    assert summary["manual"]["chunk_queries"] == 1
    assert summary["manual"]["cross_document_queries"] == 1
    assert summary["manual"]["answer_queries"] == 1
    assert summary["manual"]["expected_merged_table_docs"] == 1
    assert summary["manual"]["document_filename_match_count"] == 1
    assert summary["auto"]["document_filename_missing_count"] == 1


def test_build_readiness_gates_surfaces_court_grade_data_gaps() -> None:
    db = {
        "documents": {"active": 5},
        "runs": {"completed": 5},
        "evaluations": {"completed": 5, "queries": 50, "passed_queries": 45},
        "search": {
            "requests": 100,
            "feedback_total": 2,
            "feedback_by_type": {"relevant": 1, "irrelevant": 1},
        },
        "claim_feedback": {
            "total": 0,
            "by_learning_label": {},
            "by_status": {},
            "traceability_issue_counts": {},
        },
        "claim_support_replay_alert_corpus": {"rows": 0, "active_snapshots": 0},
        "replays": {
            "completed_runs_by_source": {
                "evaluation_queries": 1,
                "feedback": 1,
                "live_search_gaps": 1,
                "cross_document_prose_regressions": 1,
            },
            "completed_query_counts_by_source": {},
        },
        "harness_evaluations": {
            "source_rows_by_source": {
                "evaluation_queries": 1,
                "feedback": 1,
            }
        },
        "retrieval_learning": {
            "judgment_sets": 0,
            "completed_training_runs": 0,
            "training_examples": 0,
        },
    }
    corpora = {
        "auto": {"documents": 50, "table_queries": 60, "chunk_queries": 60},
        "manual": {
            "documents": 10,
            "table_queries": 20,
            "chunk_queries": 30,
            "answer_queries": 8,
        },
    }

    gates = build_readiness_gates(db=db, corpora=corpora)
    by_key = {gate["key"]: gate for gate in gates}
    summary = summarize_readiness(gates)

    assert summary["regression_ready"] is True
    assert summary["court_grade_ready"] is False
    assert by_key["operator_feedback_coverage"]["passed"] is False
    assert by_key["operator_feedback_coverage"]["metric"]["missing_types"] == [
        "missing_table",
        "missing_chunk",
        "no_answer",
    ]
    assert by_key["technical_report_claim_feedback_ledger"]["passed"] is False
    assert by_key["basic_replay_source_coverage"]["passed"] is True
    assert by_key["all_replay_source_coverage"]["metric"]["missing_sources"] == [
        "technical_report_claim_feedback"
    ]
    assert "retrieval_learning_materialized" in summary["court_grade_blockers"]


def test_build_readiness_gates_passes_when_all_required_data_exists() -> None:
    db = {
        "documents": {"active": 20},
        "runs": {"completed": 20},
        "evaluations": {"completed": 20, "queries": 120, "passed_queries": 120},
        "search": {
            "requests": 500,
            "feedback_total": 30,
            "feedback_by_type": {key: 2 for key in FEEDBACK_TYPES},
        },
        "claim_feedback": {
            "total": 30,
            "by_learning_label": {key: 2 for key in CLAIM_FEEDBACK_LABELS},
            "by_status": {key: 2 for key in CLAIM_FEEDBACK_STATUSES},
            "traceability_issue_counts": {},
        },
        "claim_support_replay_alert_corpus": {"rows": 5, "active_snapshots": 1},
        "replays": {
            "completed_runs_by_source": {key: 1 for key in REPLAY_SOURCE_TYPES},
            "completed_query_counts_by_source": {key: 10 for key in REPLAY_SOURCE_TYPES},
        },
        "harness_evaluations": {
            "source_rows_by_source": {key: 1 for key in REPLAY_SOURCE_TYPES}
        },
        "retrieval_learning": {
            "judgment_sets": 1,
            "completed_training_runs": 1,
            "training_examples": 30,
        },
    }
    corpora = {
        "auto": {"documents": 50, "table_queries": 60, "chunk_queries": 60},
        "manual": {
            "documents": 10,
            "table_queries": 20,
            "chunk_queries": 30,
            "answer_queries": 8,
        },
    }

    summary = summarize_readiness(build_readiness_gates(db=db, corpora=corpora))

    assert summary["regression_ready"] is True
    assert summary["court_grade_ready"] is True
    assert summary["failed_gate_count"] == 0
