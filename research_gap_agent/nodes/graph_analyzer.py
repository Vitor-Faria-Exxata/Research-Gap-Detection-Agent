"""
Graph analyzer node (owner: Caio).
"""

import logging

from research_gap_agent.schemas import GraphInsight
from research_gap_agent.state import GraphState


logger = logging.getLogger(__name__)


def graph_analyzer_node(state: GraphState) -> dict:
    # TODO(caio)

    placeholder = GraphInsight(
        summary=(
            "Graph analysis is not implemented yet."
        ),
        disconnected_pairs=[],
        raw={"stub": True},
    )

    logger.info("graph_analyzer_node: returning placeholder GraphInsight.")
    return {"graph_insight": placeholder}
