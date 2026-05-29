"""
Ranker node (owner: Vinicius)
"""

import logging
import os
import requests

from research_gap_agent.config import load_settings
from research_gap_agent.schemas import Paper
from research_gap_agent.state import GraphState


logger = logging.getLogger(__name__)

JINA_API_KEY = os.getenv("JINA_API_KEY")
LANGSEARCH_API_KEY = os.getenv("LANGSEARCH_API_KEY")

def jina_rerank(query: str, documents: list[Paper], top_k: int) -> list[tuple[Paper, float]]:
    """Hits the Jina API and returns papers with relevancy results."""
    url = "https://api.jina.ai/v1/rerank"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {JINA_API_KEY}"
    }
    data = {
        "model": "jina-reranker-v3",
        "query": query,
        "documents": documents,
        "top_n": top_k
    }
    
    response = requests.post(url, headers=headers, json=data)
    
    if response.status_code == 402:
        raise PermissionError("Jina out of tokens")
    
    response.raise_for_status()
    results = response.json().get("results", [])

    return [(documents[r['index']], r['relevance_score']) for r in results]

def langsearch_rerank(query: str, documents: list[Paper]) -> list[tuple[Paper, float]]:
    """Hits the LangSearch API and returns papers with relevancy results. Limited to 50"""
    url = "https://api.langsearch.com/v1/rerank"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LANGSEARCH_API_KEY}"
    }
    data = {
        "model": 'langsearch-reranker-v1',
        "query": query,
        "documents": documents
    }
    
    response = requests.post(url, headers=headers, json=data)
    response.raise_for_status()
    results = response.json().get("data", [])
    
    return [(documents[r['index']], r['relevance_score']) for r in results]

def safe_rerank(query: str, documents: list[Paper], top_k: int) -> list[Paper]:
    """
    Tries Jina first, falls back to LangSearch gracefully.
    If both APIs fail, defaults to returning the top_k raw documents.
    """
    try:
        logger.info("ranker_node: attempting Jina Reranker...")
        return jina_rerank(query, documents, top_k)
        
    except Exception as e:
        if isinstance(e, PermissionError):
            logger.warning("ranker_node: jina tokens depleted. Falling back to LangSearch...")
        else:
            logger.warning(f"ranker_node: jina failed with error: {e}. Falling back to LangSearch...")
            
        try:
            docs_to_rerank = documents[:50]
            ranked_docs = langsearch_rerank(query, docs_to_rerank)
            
            return ranked_docs[:top_k]
            
        except Exception as ls_e:
            logger.error(f"ranker_node: LangSearch also failed ({ls_e}). Falling back to no reranking.")
            return documents[:top_k]


def ranker_node(state: GraphState) -> dict:
    """LangGraph node to handle document reranking."""
    
    top_k = load_settings().yaml.pipeline.top_papers
    
    query = state.queries[0] #TODO which query to rerank on?
    
    logger.info(
        "ranker_node: Initiating reranking for %d papers down to top %d.",
        len(state.raw_papers),
        top_k
    )
    
    selected_papers = safe_rerank(query, state.raw_papers, top_k)
    
    return {"ranked_papers": selected_papers}
