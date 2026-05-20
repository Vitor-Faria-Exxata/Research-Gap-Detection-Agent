"""Semantic Scholar source.

We ask for the `openAccessPdf` field and drop any paper that does not have
one. That field carries both the URL and the OA tier (gold/green/...).

API docs: https://api.semanticscholar.org/api-docs/graph
"""

import logging
import time
from datetime import date, datetime
from threading import Lock
from typing import Optional

import requests

from research_gap_agent.schemas import Paper
from research_gap_agent.sources.base import PaperSource


logger = logging.getLogger(__name__)

API_URL = "https://api.semanticscholar.org/graph/v1/paper/search"

# Minimum seconds between requests. Without an API key we share a tight
# global pool (1000 per second), so we go slow.
MIN_INTERVAL_NO_KEY_S = 1.1
MIN_INTERVAL_WITH_KEY_S = 0.2

# Retry up to this many times when the API returns 429.
MAX_RETRIES = 3
# Backoff between retries: 2s, 4s, 8s.
BACKOFF_BASE_S = 2.0

# Fields we ask Semantic Scholar to return. Listing them explicitly avoids
# the API returning the heavy default payload.
FIELDS = ",".join(
    [
        "paperId",
        "title",
        "abstract",
        "authors",
        "year",
        "publicationDate",
        "externalIds",
        "openAccessPdf",
        "fieldsOfStudy",
        "url",
    ]
)

# Module-level rate limiter, shared by all SemanticScholarSource instances.
_last_call_time = 0.0
_rate_limit_lock = Lock()


def wait_for_rate_limit(min_interval_s: float):
    """Block until at least `min_interval_s` has passed since the last call."""
    global _last_call_time
    with _rate_limit_lock:
        elapsed = time.monotonic() - _last_call_time
        if elapsed < min_interval_s:
            time.sleep(min_interval_s - elapsed)
        _last_call_time = time.monotonic()


def parse_date(item: dict) -> Optional[date]:
    """Pull a date out of a Semantic Scholar item.

    Prefers the full publicationDate; falls back to year (January 1st of
    that year) so we always have something to compare chronologically.
    """
    pub = item.get("publicationDate")
    if pub:
        try:
            return datetime.strptime(pub, "%Y-%m-%d").date()
        except ValueError:
            pass

    year = item.get("year")
    if year:
        try:
            return date(int(year), 1, 1)
        except (ValueError, TypeError):
            pass

    return None


class SemanticScholarSource(PaperSource):
    name = "semantic_scholar"

    def __init__(self, timeout_s: int = 30, api_key: Optional[str] = None):
        self.timeout_s = timeout_s
        self.api_key = api_key
        self.min_interval_s = (
            MIN_INTERVAL_WITH_KEY_S if api_key else MIN_INTERVAL_NO_KEY_S
        )

    def search(self, query: str, limit: int) -> list[Paper]:
        params = {
            "query": query,
            "limit": min(limit, 100),
            "fields": FIELDS,
        }
        headers = {}
        if self.api_key:
            headers["x-api-key"] = self.api_key

        payload = self.request_with_retry(params, headers, query)
        if payload is None:
            return []

        papers = []
        for item in payload.get("data", []):
            paper = self.item_to_paper(item)
            if paper is not None:
                papers.append(paper)
        return papers

    def request_with_retry(self, params, headers, query) -> Optional[dict]:
        """Hit the API, retrying with exponential backoff on 429."""
        for attempt in range(MAX_RETRIES + 1):
            wait_for_rate_limit(self.min_interval_s)
            try:
                response = requests.get(
                    API_URL, params=params, headers=headers, timeout=self.timeout_s
                )
            except requests.RequestException as exc:
                logger.warning(
                    "Semantic Scholar request failed for query=%r: %s", query, exc
                )
                return None

            # Retry on 429 (rate limit) until we run out of attempts.
            if response.status_code == 429 and attempt < MAX_RETRIES:
                wait_s = BACKOFF_BASE_S * (2 ** attempt)
                logger.info(
                    "Semantic Scholar 429 for query=%r — backing off %.1fs (attempt %d/%d).",
                    query,
                    wait_s,
                    attempt + 1,
                    MAX_RETRIES,
                )
                time.sleep(wait_s)
                continue

            try:
                response.raise_for_status()
                return response.json()
            except (requests.RequestException, ValueError) as exc:
                logger.warning(
                    "Semantic Scholar request failed for query=%r: %s", query, exc
                )
                return None

        logger.warning(
            "Semantic Scholar gave up on query=%r after %d retries.", query, MAX_RETRIES
        )
        return None

    def item_to_paper(self, item: dict) -> Optional[Paper]:
        """Convert one Semantic Scholar item into a Paper, or None on failure."""
        try:
            oa = item.get("openAccessPdf") or {}
            pdf_url = oa.get("url")
            if not pdf_url:
                # No OA PDF available - skip.
                return None

            abstract = (item.get("abstract") or "").strip()
            if not abstract:
                return None

            published = parse_date(item)
            if published is None:
                return None

            paper_id = item.get("paperId")
            if not paper_id:
                return None

            authors = [
                a.get("name", "")
                for a in item.get("authors", [])
                if a.get("name")
            ]

            external_ids = item.get("externalIds") or {}
            landing_url = (
                item.get("url")
                or f"https://www.semanticscholar.org/paper/{paper_id}"
            )

            return Paper(
                id=f"semantic_scholar:{paper_id}",
                source="semantic_scholar",
                title=item.get("title") or "",
                abstract=abstract,
                authors=authors,
                published_date=published,
                url=landing_url,
                pdf_url=pdf_url,
                is_open_access=True,
                oa_status=oa.get("status"),
                doi=external_ids.get("DOI"),
                arxiv_id=external_ids.get("ArXiv"),
                categories=item.get("fieldsOfStudy") or [],
            )
        except (AttributeError, ValueError, KeyError) as exc:
            logger.debug("Skipping malformed Semantic Scholar item: %s", exc)
            return None
