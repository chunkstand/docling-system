from __future__ import annotations

from pathlib import Path

import yaml


def test_evaluation_corpus_config_has_required_documents_and_thresholds() -> None:
    config = yaml.safe_load((Path("docs") / "evaluation_corpus.yaml").read_text())

    assert config["rollout_mode"] == "immediate_breaking_replacement"
    assert config["embedding_contract"]["model"] == "text-embedding-3-small"
    assert config["embedding_contract"]["dimension"] == 1536
    assert len(config["documents"]) == 9

    names = {document["name"] for document in config["documents"]}
    assert "appendix_b_prose_guidance" in names
    assert "upc_ch2_figures" in names
    assert "awkward_headers" in names
    assert "upc_ch4" in names
    assert "upc_ch5" in names
    assert "bitter_lesson_prose" in names

    figure_document = next(
        document for document in config["documents"] if document["name"] == "upc_ch2_figures"
    )
    figure_thresholds = figure_document["thresholds"]
    assert figure_document["kind"] == "figure_heavy_definitions"
    assert figure_thresholds["expected_figure_count"] >= 1
    assert figure_thresholds["figure_count_tolerance"] >= 0
    assert figure_thresholds["minimum_captioned_figure_count"] >= 1
    assert figure_thresholds["minimum_figures_with_provenance"] >= 1
    assert figure_thresholds["minimum_figures_with_artifacts"] >= 1
    assert len(figure_thresholds["expected_figure_captions_present"]) >= 1

    awkward_document = next(
        document for document in config["documents"] if document["name"] == "awkward_headers"
    )
    awkward_thresholds = awkward_document["thresholds"]
    assert awkward_document["path"] == "/Users/chunkstand/Documents/UPC/UPC_CH_3.pdf"
    assert awkward_thresholds["expected_logical_table_count"] >= 1
    assert awkward_thresholds["expected_figure_count"] >= 1
    assert awkward_thresholds["minimum_captioned_figure_count"] >= 1
    assert awkward_thresholds["minimum_figures_with_provenance"] >= 1
    assert awkward_thresholds["minimum_figures_with_artifacts"] >= 1
    assert all(
        isinstance(caption, str)
        for caption in awkward_thresholds["expected_figure_captions_present"]
    )
    assert len(awkward_thresholds["expected_top_n_table_hit_queries"]) >= 1

    simple_document = next(
        document for document in config["documents"] if document["name"] == "born_digital_simple"
    )
    simple_thresholds = simple_document["thresholds"]
    assert simple_document["path"] == "/Users/chunkstand/Documents/UPC/UPC_Appendix_N.pdf"
    assert simple_thresholds["expected_logical_table_count"] == 1
    assert simple_thresholds["expected_figure_count"] == 0
    assert len(simple_thresholds["expected_top_n_table_hit_queries"]) >= 2
    assert len(simple_thresholds["expected_top_n_chunk_hit_queries"]) >= 1

    appendix_b_document = next(
        document
        for document in config["documents"]
        if document["name"] == "appendix_b_prose_guidance"
    )
    appendix_b_thresholds = appendix_b_document["thresholds"]
    assert appendix_b_document["path"] == "/Users/chunkstand/Documents/UPC/UPC_Appendix_B.pdf"
    assert appendix_b_thresholds["expected_logical_table_count"] == 0
    assert appendix_b_thresholds["expected_figure_count"] == 0
    assert len(appendix_b_thresholds["expected_top_n_chunk_hit_queries"]) >= 2

    chapter_four_document = next(
        document for document in config["documents"] if document["name"] == "upc_ch4"
    )
    chapter_four_thresholds = chapter_four_document["thresholds"]
    assert chapter_four_document["path"] == "/Users/chunkstand/Documents/UPC/UPC_CH_4.pdf"
    assert chapter_four_thresholds["expected_logical_table_count"] == 3
    assert chapter_four_thresholds["expected_figure_count"] == 0
    assert len(chapter_four_thresholds["expected_top_n_table_hit_queries"]) >= 1
    assert len(chapter_four_thresholds["expected_top_n_chunk_hit_queries"]) >= 3

    chapter_five_document = next(
        document for document in config["documents"] if document["name"] == "upc_ch5"
    )
    chapter_five_thresholds = chapter_five_document["thresholds"]
    assert chapter_five_document["path"] == "/Users/chunkstand/Documents/UPC/UPC_CH_5.pdf"
    assert chapter_five_thresholds["expected_logical_table_count"] == 41
    assert chapter_five_thresholds["expected_figure_count"] == 41
    assert len(chapter_five_thresholds["expected_merged_tables"]) >= 1
    assert len(chapter_five_thresholds["expected_top_n_table_hit_queries"]) >= 2
    assert len(chapter_five_thresholds["expected_top_n_chunk_hit_queries"]) >= 2

    chapter_seven_document = next(
        document for document in config["documents"] if document["name"] == "upc_ch7"
    )
    chapter_seven_thresholds = chapter_seven_document["thresholds"]
    assert chapter_seven_document["path"] == "/Users/chunkstand/Documents/UPC/UPC_CH_7.pdf"
    assert chapter_seven_thresholds["expected_figure_count"] >= 1
    assert chapter_seven_thresholds["minimum_captioned_figure_count"] >= 1
    assert chapter_seven_thresholds["minimum_figures_with_provenance"] >= 1
    assert chapter_seven_thresholds["minimum_figures_with_artifacts"] >= 1
    assert len(chapter_seven_thresholds["expected_top_n_table_hit_queries"]) >= 2
    assert len(chapter_seven_thresholds["expected_top_n_chunk_hit_queries"]) >= 2

    bitter_lesson_document = next(
        document for document in config["documents"] if document["name"] == "bitter_lesson_prose"
    )
    bitter_lesson_thresholds = bitter_lesson_document["thresholds"]
    assert (
        bitter_lesson_document["path"]
        == "/Users/chunkstand/Documents/docling-ingest-staging/The Bitter Lesson.pdf"
    )
    assert bitter_lesson_document["kind"] == "cross_domain_prose_essay"
    assert bitter_lesson_thresholds["expected_logical_table_count"] == 0
    assert bitter_lesson_thresholds["expected_figure_count"] == 0
    assert len(bitter_lesson_thresholds["expected_top_n_chunk_hit_queries"]) == 3

    for document in config["documents"]:
        thresholds = document["thresholds"]
        assert "expected_logical_table_count" in thresholds
        assert "maximum_unexpected_merges" in thresholds
        assert "maximum_unexpected_splits" in thresholds
        query_count = (
            len(thresholds.get("expected_top_n_table_hit_queries", []))
            + len(thresholds.get("expected_top_n_chunk_hit_queries", []))
            + len(thresholds.get("queries", []))
        )
        assert query_count >= 3
