import logging

from research_gap_agent.schemas import Paper
from .reranker_base import Reranker

logger = logging.getLogger(__name__)


class CrossEncoderReranker(Reranker):

    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2", device: str = "cpu"):
        try:
            from sentence_transformers.cross_encoder import CrossEncoder
        except ImportError:
            raise ImportError(
                "sentence-transformers is required for CrossEncoderReranker. "
                "Install it with: pip install sentence-transformers"
            )
        self.model = CrossEncoder(model_name, device=device)

    def rerank(self, query: str, documents: list[Paper], top_k: int) -> list[tuple[Paper, float]]:
        pairs = [(query, doc.abstract) for doc in documents]
        scores = self.model.predict(pairs)
        scored = sorted(zip(documents, scores), key=lambda x: x[1], reverse=True)
        return scored[:top_k]
