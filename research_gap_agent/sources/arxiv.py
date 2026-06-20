import logging
import re
import time
from datetime import datetime
from typing import Optional

import feedparser
import requests

from research_gap_agent.arxiv import MetadataCache, wait as arxiv_throttle_wait
from research_gap_agent.schemas import Paper
from research_gap_agent.sources.base import PaperSource


logger = logging.getLogger(__name__)

API_URL = "http://export.arxiv.org/api/query"
MAX_RETRIES = 3
RETRY_BACKOFF_S = 6.0
RETRY_AFTER_MAX_S = 60.0

def wait_for_rate_limit():
    arxiv_throttle_wait()


def _is_retryable_status(status: int) -> bool:
    return status in (408, 425, 429, 500, 502, 503, 504)


def _retry_after_seconds(response) -> Optional[float]:
    """Parse the Retry-After header (seconds or HTTP date)."""
    raw = response.headers.get("Retry-After")
    if not raw:
        return None
    try:
        return max(0.0, min(float(raw), RETRY_AFTER_MAX_S))
    except ValueError:
        # HTTP date format — fall back to a conservative default.
        return None


def _backoff(response, attempt: int) -> float:
    """Prefer the server's Retry-After, fall back to exponential backoff."""
    retry_after = _retry_after_seconds(response) if response is not None else None
    if retry_after is not None:
        return retry_after
    return RETRY_BACKOFF_S * (2 ** (attempt - 1))


def extract_arxiv_id(entry_id: str) -> Optional[str]:
    """Pull the arxiv_id out of a feed entry id like
    'http://arxiv.org/abs/2401.12345v2'."""
    match = re.search(r"abs/([^/]+?)(?:v\d+)?$", entry_id)
    return match.group(1) if match else None


def find_pdf_link(entry) -> Optional[str]:
    """Look for the PDF link in a feedparser entry."""
    for link in getattr(entry, "links", []):
        if getattr(link, "type", "") == "application/pdf":
            return link.href
    return None


def clean_whitespace(text: str) -> str:
    """Collapse runs of whitespace and strip leading/trailing spaces."""
    return re.sub(r"\s+", " ", text).strip()


class ArxivSource(PaperSource):
    name = "arxiv"

    def __init__(self, timeout_s: int = 60, metadata_cache: Optional[MetadataCache] = None):
        self.timeout_s = timeout_s
        self.metadata_cache = metadata_cache or MetadataCache()

    def search(self, query: str, limit: int) -> list[Paper]:
        # Query-level cache: if we've already searched this exact query
        # recently, skip the throttle + the network call entirely.
        cached = self.metadata_cache.get_fresh(query)
        if cached is not None:
            logger.info("arXiv metadata cache hit for query=%r (%d papers)", query, len(cached))
            return cached[:limit]

        params = {
            "search_query": f"all:{query}",
            "start": 0,
            "max_results": limit,
            "sortBy": "relevance",
            "sortOrder": "descending",
        }

        for attempt in range(1, MAX_RETRIES + 1):
            arxiv_throttle_wait()
            response = None
            try:
                response = requests.get(API_URL, params=params, timeout=self.timeout_s)
                if _is_retryable_status(response.status_code) and attempt < MAX_RETRIES:
                    wait = _backoff(response, attempt)
                    logger.warning(
                        "arXiv %s for query=%r (attempt %d/%d). "
                        "Server asked to wait %.1fs.",
                        response.status_code, query, attempt, MAX_RETRIES, wait,
                    )
                    time.sleep(wait)
                    continue
                response.raise_for_status()
                break
            except requests.RequestException as exc:
                if attempt < MAX_RETRIES:
                    wait = _backoff(response, attempt)
                    logger.warning(
                        "arXiv request failed for query=%r (attempt %d/%d): %s. "
                        "Retrying in %.1fs.",
                        query, attempt, MAX_RETRIES, exc, wait,
                    )
                    time.sleep(wait)
                    continue
                logger.warning("arXiv request failed for query=%r: %s", query, exc)
                return []
        else:
            logger.warning("arXiv request exhausted retries for query=%r", query)
            return []

        feed = feedparser.parse(response.text)
        papers = []
        for entry in feed.entries:
            paper = self.entry_to_paper(entry)
            if paper is not None:
                papers.append(paper)

        self.metadata_cache.put(query, papers)
        return papers

    def entry_to_paper(self, entry) -> Optional[Paper]:
        """Convert a single feedparser entry into a Paper, or None on failure."""
        try:
            arxiv_id = extract_arxiv_id(entry.id)
            if not arxiv_id:
                return None

            # arXiv dates look like "2024-01-15T18:00:00Z" - we only keep the date part.
            published_date = datetime.strptime(entry.published[:10], "%Y-%m-%d").date()

            authors = [a.name for a in getattr(entry, "authors", []) if hasattr(a, "name")]
            categories = [t.term for t in getattr(entry, "tags", []) if hasattr(t, "term")]
            pdf_url = find_pdf_link(entry) or f"https://arxiv.org/pdf/{arxiv_id}.pdf"

            abstract = clean_whitespace(entry.summary)
            if not abstract:
                return None

            return Paper(
                id=f"arxiv:{arxiv_id}",
                source="arxiv",
                title=clean_whitespace(entry.title),
                abstract=abstract,
                authors=authors,
                published_date=published_date,
                url=f"https://arxiv.org/abs/{arxiv_id}",
                pdf_url=pdf_url,
                is_open_access=True,
                oa_status="green", # all arXiv papers are green OA
                doi=getattr(entry, "arxiv_doi", None),
                arxiv_id=arxiv_id,
                categories=categories,
            )
        except (AttributeError, ValueError, KeyError) as exc:
            logger.debug("Skipping malformed arXiv entry: %s", exc)
            return None
