from abc import ABC, abstractmethod

from research_gap_agent.schemas import Paper


class Reranker(ABC):

    @abstractmethod
    def rerank(self, query: str, documents: list[Paper], top_k: int) -> list[tuple[Paper, float]]:
        pass
