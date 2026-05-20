"""
Ranker node (owner: Vinicius)
"""

import logging

from research_gap_agent.config import load_settings
from research_gap_agent.state import GraphState


logger = logging.getLogger(__name__)


def ranker_node(state: GraphState) -> dict:
    # TODO(vinicius)

    top_k = load_settings().yaml.pipeline.top_papers
    selected = state.raw_papers[:top_k]

    logger.info(
        "ranker_node: keeping the first %d of %d papers (no scoring yet).",
        len(selected),
        len(state.raw_papers),
    )
    return {"ranked_papers": selected}
