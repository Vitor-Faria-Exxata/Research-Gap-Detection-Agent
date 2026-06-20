"""
Aggregator node (owner: Vitor).
"""

import logging

from research_gap_agent.schemas import FinalReport
from research_gap_agent.state import GraphState


logger = logging.getLogger(__name__)


def aggregator_node(state: GraphState) -> dict:
    gap_identification = state.gap_identification
    if gap_identification is None:
        raise ValueError(
            "Aggregator integration error: gap_identification result is "
            "required; use an empty GapIdentificationResult for a valid "
            "empty analysis."
        )

    ranked_papers_by_id = {
        paper.id: paper for paper in state.ranked_papers
    }
    sources_used = sorted(
        {
            ranked_papers_by_id[insight.paper_id].source
            for insight in state.extracted
            if insight.paper_id in ranked_papers_by_id
        }
    )
    insight_count = len(state.extracted)

    graph_summary = (
        state.graph_insight.summary if state.graph_insight else "n/a"
    )
    warning_codes = {
        warning.code for warning in gap_identification.warnings
    }
    if "no_extracted_insights" in warning_codes:
        summary = (
            "Gap identification was not performed because no structured "
            "article insights were available. "
            f"Graph insight: {graph_summary}"
        )
    else:
        gap_count = len(gap_identification.gaps)
        gap_label = "gap" if gap_count == 1 else "gaps"
        summary = (
            f"Found {gap_count} candidate {gap_label}. "
            f"Graph insight: {graph_summary}"
        )
    if gap_identification.cutoff_date is None:
        candidate_scope = "relative to the available corpus"
    else:
        candidate_scope = (
            "relative to the corpus through "
            f"{gap_identification.cutoff_date.isoformat()}"
        )
    source_count = len(sources_used)
    source_label = "source" if source_count == 1 else "sources"
    query_count = len(state.queries)
    query_label = "query" if query_count == 1 else "queries"
    raw_paper_count = len(state.raw_papers)
    paper_label = "paper" if raw_paper_count == 1 else "papers"
    insight_label = "insight" if insight_count == 1 else "insights"
    ranked_paper_count = len(state.ranked_papers)
    ranked_paper_label = (
        "paper" if ranked_paper_count == 1 else "papers"
    )
    methodology_note = (
        f"Candidate gaps are {candidate_scope}. "
        f"Searched {source_count} {source_label} with "
        f"{query_count} rewritten {query_label}; ranked top "
        f"{ranked_paper_count} of {raw_paper_count} {paper_label}; "
        f"analyzed {insight_count} structured {insight_label} from "
        f"{ranked_paper_count} ranked {ranked_paper_label}."
    )

    report = FinalReport(
        topic=state.initial_topic,
        cutoff_date=gap_identification.cutoff_date,
        warnings=[
            warning.model_copy(deep=True)
            for warning in gap_identification.warnings
        ],
        gaps=[
            gap.model_copy(deep=True)
            for gap in gap_identification.gaps
        ],
        summary=summary,
        methodology_note=methodology_note,
        sources_used=sources_used,
        papers_considered=insight_count,
    )

    return {"final_report": report}
