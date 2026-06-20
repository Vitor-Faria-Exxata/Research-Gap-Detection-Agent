import logging
import os

import requests

from research_gap_agent.schemas import Paper
from .reranker_base import Reranker

logger = logging.getLogger(__name__)


class JinaAPIReranker(Reranker):

    def __init__(self):
        self.api_key = os.getenv("JINA_API_KEY")
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        self.url = "https://api.jina.ai/v1/rerank"

    def rerank(self, query: str, documents: list[Paper], top_k: int) -> list[tuple[Paper, float]]:
        text_docs = [
            {"text": f"{doc.title}. {doc.abstract}".strip()}
            for doc in documents
        ]
        data = {
            "model": "jina-reranker-v3",
            "query": query,
            "documents": text_docs,
            "top_n": top_k,
        }

        response = requests.post(self.url, headers=self.headers, json=data)

        if response.status_code == 402:
            raise PermissionError("Jina out of tokens")

        response.raise_for_status()
        results = response.json().get("results", [])

        return [(documents[r["index"]], r["relevance_score"]) for r in results]
