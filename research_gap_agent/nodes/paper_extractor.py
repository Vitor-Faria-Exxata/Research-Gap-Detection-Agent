"""
Paper extractor node (owner: Vinicius).
"""

import logging

from research_gap_agent.schemas import ExtractedInsights
from research_gap_agent.state import GraphState


logger = logging.getLogger(__name__)


def paper_extractor_node(state: GraphState) -> dict:
    # TODO(vinicius)
    
    extracted = [ExtractedInsights(paper_id=p.id) for p in state.ranked_papers]

    logger.info(
        "paper_extractor_node: returning %d empty ExtractedInsights.",
        len(extracted),
    )
    return {"extracted": extracted}
