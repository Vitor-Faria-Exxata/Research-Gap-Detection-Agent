from datetime import date

import pytest

from research_gap_agent.nodes.aggregator import aggregator_node
from research_gap_agent.schemas import (
    ExtractedInsights,
    GapEvidence,
    GapIdentificationResult,
    GapWarning,
    GraphInsight,
    IdentifiedGap,
    Paper,
    SearchQuery,
)
from research_gap_agent.state import GraphState


def _paper(paper_id: str, source: str) -> Paper:
    return Paper(
        id=paper_id,
        source=source,
        title=f"Paper {paper_id}",
        abstract="Abstract",
        published_date=date(2025, 1, 1),
        url=f"https://example.com/{paper_id}",
        pdf_url=f"https://example.com/{paper_id}.pdf",
    )


def _insight(paper_id: str) -> ExtractedInsights:
    return ExtractedInsights(
        paper_id=paper_id,
        title=f"Paper {paper_id}",
        published_date=date(2025, 1, 1),
    )


def _gap() -> IdentifiedGap:
    return IdentifiedGap(
        research_question="How do candidate effects change over time?",
        description="Longitudinal effects remain insufficiently studied.",
        evidence_strength=84,
        evidence=[
            GapEvidence(
                paper_id="paper-1",
                evidence_type="stated_limitations",
                description="The study calls for longitudinal follow-up.",
            )
        ],
        rationale="The available corpus repeatedly identifies this scope.",
    )


def _state(gap_result: GapIdentificationResult | None) -> GraphState:
    return GraphState(
        initial_topic="Longitudinal effects of AI agents",
        queries=[
            SearchQuery(
                text="AI agents longitudinal effects",
                rationale="Find longitudinal studies.",
            )
        ],
        raw_papers=[
            _paper("paper-1", "arxiv"),
            _paper("paper-2", "openalex"),
            _paper("paper-3", "semantic_scholar"),
        ],
        ranked_papers=[
            _paper("paper-1", "arxiv"),
            _paper("paper-2", "openalex"),
            _paper("paper-3", "semantic_scholar"),
        ],
        extracted=[_insight("paper-1")],
        graph_insight=GraphInsight(summary="Two themes are disconnected."),
        gap_identification=gap_result,
    )


def test_aggregator_propagates_gap_identification_contract():
    gap_result = GapIdentificationResult(
        cutoff_date=date(2025, 4, 3),
        warnings=[
            GapWarning(
                code="invalid_counter_evidence_reference",
                message="One invalid counterevidence item was removed.",
            )
        ],
        gaps=[_gap()],
    )

    report = aggregator_node(_state(gap_result))["final_report"]

    assert report.gaps == gap_result.gaps
    assert report.cutoff_date == gap_result.cutoff_date
    assert report.warnings == gap_result.warnings
    assert "Found 1 candidate gap." in report.summary
    assert "Graph insight: Two themes are disconnected." in report.summary
    assert "relative to the corpus through 2025-04-03" in (
        report.methodology_note
    )
    assert "1 source with 1 rewritten query" in report.methodology_note
    assert "ranked top 3 of 3 papers" in report.methodology_note
    assert (
        "analyzed 1 structured insight from 3 ranked papers"
        in report.methodology_note
    )
    assert report.sources_used == ["arxiv"]
    assert report.papers_considered == 1


def test_aggregator_accepts_valid_empty_gap_identification_result():
    gap_result = GapIdentificationResult(
        cutoff_date=None,
        warnings=[
            GapWarning(
                code="no_extracted_insights",
                message="No structured article insights were available.",
            )
        ],
        gaps=[],
    )

    state = _state(gap_result).model_copy(
        deep=True,
        update={"extracted": []},
    )

    report = aggregator_node(state)["final_report"]

    assert report.gaps == []
    assert report.cutoff_date is None
    assert report.warnings == gap_result.warnings
    assert report.summary == (
        "Gap identification was not performed because no structured article "
        "insights were available. Graph insight: Two themes are disconnected."
    )
    assert "Found 0 candidate gaps" not in report.summary
    assert "relative to the available corpus" in report.methodology_note
    assert (
        "analyzed 0 structured insights from 3 ranked papers"
        in report.methodology_note
    )
    assert report.sources_used == []
    assert report.papers_considered == 0


def test_aggregator_counts_unmatched_insight_without_inventing_source():
    gap_result = GapIdentificationResult(
        cutoff_date=date(2025, 1, 1),
        gaps=[],
    )
    state = _state(gap_result).model_copy(
        deep=True,
        update={"extracted": [_insight("missing-paper")]},
    )

    report = aggregator_node(state)["final_report"]

    assert report.sources_used == []
    assert report.papers_considered == 1
    assert (
        "analyzed 1 structured insight from 3 ranked papers"
        in report.methodology_note
    )


def test_aggregator_uses_plural_candidate_gaps_for_multiple_results():
    first_gap = _gap()
    second_gap = first_gap.model_copy(
        deep=True,
        update={
            "research_question": (
                "Which populations remain underrepresented?"
            )
        },
    )
    gap_result = GapIdentificationResult(
        cutoff_date=date(2025, 4, 3),
        gaps=[first_gap, second_gap],
    )

    report = aggregator_node(_state(gap_result))["final_report"]

    assert "Found 2 candidate gaps." in report.summary


def test_aggregator_uses_singular_source_and_plural_queries():
    gap_result = GapIdentificationResult(
        cutoff_date=None,
        gaps=[],
    )
    state = _state(gap_result).model_copy(
        deep=True,
        update={
            "ranked_papers": [_paper("paper-1", "arxiv")],
            "queries": [
                SearchQuery(text="query one", rationale="First query."),
                SearchQuery(text="query two", rationale="Second query."),
            ],
        },
    )

    report = aggregator_node(state)["final_report"]

    assert "1 source with 2 rewritten queries" in report.methodology_note


def test_aggregator_uses_singular_paper_for_ranked_and_raw_counts():
    gap_result = GapIdentificationResult(
        cutoff_date=None,
        gaps=[],
    )
    paper = _paper("paper-1", "arxiv")
    state = _state(gap_result).model_copy(
        deep=True,
        update={
            "raw_papers": [paper],
            "ranked_papers": [paper],
        },
    )

    report = aggregator_node(state)["final_report"]

    assert "ranked top 1 of 1 paper;" in report.methodology_note
    assert (
        "analyzed 1 structured insight from 1 ranked paper."
        in report.methodology_note
    )


def test_aggregator_deep_copies_warnings_and_gaps_into_report():
    gap_result = GapIdentificationResult(
        cutoff_date=date(2025, 4, 3),
        warnings=[
            GapWarning(
                code="missing_evidence",
                message="A candidate was discarded.",
            )
        ],
        gaps=[_gap()],
    )

    report = aggregator_node(_state(gap_result))["final_report"]

    assert report.warnings is not gap_result.warnings
    assert report.warnings[0] is not gap_result.warnings[0]
    assert report.gaps is not gap_result.gaps
    assert report.gaps[0] is not gap_result.gaps[0]
    assert report.gaps[0].evidence[0] is not gap_result.gaps[0].evidence[0]

    report.warnings[0].message = "Changed report warning."
    report.gaps[0].description = "Changed report gap."
    report.gaps[0].evidence[0].description = "Changed report evidence."

    assert gap_result.warnings[0].message == "A candidate was discarded."
    assert gap_result.gaps[0].description == (
        "Longitudinal effects remain insufficiently studied."
    )
    assert gap_result.gaps[0].evidence[0].description == (
        "The study calls for longitudinal follow-up."
    )


def test_aggregator_rejects_missing_gap_identification_result():
    with pytest.raises(
        ValueError,
        match="gap_identification result is required",
    ):
        aggregator_node(_state(None))
