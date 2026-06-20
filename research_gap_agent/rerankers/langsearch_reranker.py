import logging
import os

import requests

from research_gap_agent.schemas import Paper
from .reranker_base import Reranker

logger = logging.getLogger(__name__)


class LangSearchAPIReranker(Reranker):

    def __init__(self, max_docs: int = 50):
        self.api_key = os.getenv("LANGSEARCH_API_KEY")
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        self.url = "https://api.langsearch.com/v1/rerank"
        self.max_docs = max_docs

    def rerank(self, query: str, documents: list[Paper], top_k: int) -> list[tuple[Paper, float]]:
        docs_to_send = documents[:self.max_docs]
        data = {
            "model": "langsearch-reranker-v1",
            "query": query,
            "documents": [doc.model_dump(mode="json") for doc in docs_to_send],
        }

        response = requests.post(self.url, headers=self.headers, json=data)
        response.raise_for_status()
        payload = response.json() or {}

        if not payload.get("success", False):
            raise RuntimeError(
                f"LangSearch API error: code={payload.get('code')!r} "
                f"msg={payload.get('msg')!r}"
            )

        results = payload.get("data") or []
        if not results:
            raise RuntimeError("LangSearch API returned empty data list")

        return [(docs_to_send[r["index"]], r["relevance_score"]) for r in results]
