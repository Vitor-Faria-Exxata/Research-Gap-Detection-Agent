import logging
from dotenv import load_dotenv

from research_gap_agent.schemas import Paper
from .reranker_base import Reranker
from .jina_reranker import JinaAPIReranker
from .langsearch_reranker import LangSearchAPIReranker
from .cross_encoder_reranker import CrossEncoderReranker
from .bge_reranker import BGEReranker
load_dotenv()

logger = logging.getLogger(__name__)

__all__ = [
    "Reranker",
    "JinaAPIReranker",
    "LangSearchAPIReranker",
    "CrossEncoderReranker",
    "BGEReranker",
    "get_reranker",
    "safe_rerank",
]


def get_reranker(name: str) -> Reranker:
    mapping = {
        "jina": JinaAPIReranker,
        "langsearch": LangSearchAPIReranker,
        "cross-encoder": CrossEncoderReranker,
        "bge": BGEReranker,
    }

    if name not in mapping:
        raise ValueError(
            f"Unknown reranker: '{name}'. Choose from: {list(mapping.keys())}"
        )

    try:
        return mapping[name]()
    except ImportError as e:
        logger.error("Failed to instantiate reranker '%s': %s", name, e)
        raise


def safe_rerank(
    query: str,
    documents: list[Paper],
    top_k: int,
    primary: Reranker,
    fallback: Reranker | None = None,
) -> list[Paper]:
    try:
        logger.info("safe_rerank: attempting primary reranker...")
        results = primary.rerank(query, documents, top_k)
        return [paper for paper, _score in results][:top_k]
    except Exception as e:
        logger.warning("safe_rerank: primary reranker failed with: %s", e)

        if fallback is not None:
            try:
                logger.info("safe_rerank: falling back to fallback reranker...")
                results = fallback.rerank(query, documents, top_k)
                return [paper for paper, _score in results][:top_k]
            except Exception as fb_e:
                logger.error("safe_rerank: fallback reranker also failed: %s", fb_e)

        logger.warning("safe_rerank: returning top_k documents without reranking.")
        return documents[:top_k]
