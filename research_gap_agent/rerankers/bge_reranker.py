import logging

from research_gap_agent.schemas import Paper
from .reranker_base import Reranker

logger = logging.getLogger(__name__)


class BGEReranker(Reranker):

    def __init__(self, model_name: str = "BAAI/bge-reranker-v2-m3", use_fp16: bool = True):
        try:
            from FlagEmbedding import FlagReranker
        except ImportError:
            raise ImportError(
                "FlagEmbedding is required for BGEReranker. "
                "Install it with: pip install FlagEmbedding"
            )
        self.model = FlagReranker(model_name, use_fp16=use_fp16)

    def rerank(self, query: str, documents: list[Paper], top_k: int) -> list[tuple[Paper, float]]:
        pairs = [[query, doc.abstract] for doc in documents]
        scores = self.model.compute_score(pairs)
        scored = sorted(zip(documents, scores), key=lambda x: x[1], reverse=True)
        return scored[:top_k]
