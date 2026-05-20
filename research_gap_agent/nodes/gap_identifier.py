"""
Gap identifier node (owner: Vitor)
"""

import logging

from research_gap_agent.state import GraphState


logger = logging.getLogger(__name__)


def gap_identifier_node(state: GraphState) -> dict:
    # TODO(vitor)

    logger.info(
        "gap_identifier_node: ignored %d ExtractedInsights, returning [].",
        len(state.extracted),
    )
    return {"content_gaps": []}
