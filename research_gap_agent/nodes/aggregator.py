"""
Aggregator node (owner: Vitor).
"""

import logging

from research_gap_agent.schemas import FinalReport
from research_gap_agent.state import GraphState


logger = logging.getLogger(__name__)


def aggregator_node(state: GraphState) -> dict:
    # TODO(vitor)

    sources_used = sorted({paper.source for paper in state.ranked_papers})

    graph_summary = (
        state.graph_insight.summary if state.graph_insight else "n/a"
    )
    summary = (
        f"Found {len(state.content_gaps)} content gaps. "
        f"Graph insight: {graph_summary}"
    )
    methodology_note = (
        f"Searched {len(sources_used)} source(s) with "
        f"{len(state.queries)} rewritten queries; ranked top "
        f"{len(state.ranked_papers)} of {len(state.raw_papers)} papers."
    )

    report = FinalReport(
        topic=state.initial_topic,
        gaps=state.content_gaps,
        summary=summary,
        methodology_note=methodology_note,
        sources_used=sources_used,
        papers_considered=len(state.ranked_papers),
    )

    return {"final_report": report}
