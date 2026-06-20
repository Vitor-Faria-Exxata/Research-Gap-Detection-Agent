import logging

from research_gap_agent.config import load_settings
from research_gap_agent.rerankers import get_reranker, safe_rerank
from research_gap_agent.state import GraphState

logger = logging.getLogger(__name__)


def ranker_node(state: GraphState) -> dict:
    settings = load_settings()

    top_k = settings.yaml.pipeline.top_papers
    cfg = settings.yaml.reranker

    primary = get_reranker(cfg.provider_name)
    fallback = get_reranker(cfg.fallback) if cfg.fallback else None

    logger.info(
        "ranker_node: Initiating reranking for %d papers down to top %d.",
        len(state.raw_papers),
        top_k
    )

    selected_papers = safe_rerank(
        state.queries[0].text,
        state.raw_papers,
        top_k,
        primary,
        fallback,
    )

    return {"ranked_papers": selected_papers}
