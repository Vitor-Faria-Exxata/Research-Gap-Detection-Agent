import logging
import re
import time
from datetime import datetime
from threading import Lock
from typing import Optional

import feedparser
import requests

from research_gap_agent.schemas import Paper
from research_gap_agent.sources.base import PaperSource


logger = logging.getLogger(__name__)

API_URL = "http://export.arxiv.org/api/query"
MIN_INTERVAL_S = 3.0

# Module-level rate limiter, shared by all ArxivSource instances. We never
# want two threads hitting the arXiv API at the same time.
_last_call_time = 0.0
_rate_limit_lock = Lock()


def wait_for_rate_limit():
    """Block until at least MIN_INTERVAL_S has passed since the last call."""
    global _last_call_time
    with _rate_limit_lock:
        elapsed = time.monotonic() - _last_call_time
        if elapsed < MIN_INTERVAL_S:
            time.sleep(MIN_INTERVAL_S - elapsed)
        _last_call_time = time.monotonic()


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

    def __init__(self, timeout_s: int = 30):
        self.timeout_s = timeout_s

    def search(self, query: str, limit: int) -> list[Paper]:
        params = {
            "search_query": f"all:{query}",
            "start": 0,
            "max_results": limit,
            "sortBy": "relevance",
            "sortOrder": "descending",
        }

        wait_for_rate_limit()
        try:
            response = requests.get(API_URL, params=params, timeout=self.timeout_s)
            response.raise_for_status()
        except requests.RequestException as exc:
            logger.warning("arXiv request failed for query=%r: %s", query, exc)
            return []

        feed = feedparser.parse(response.text)
        papers = []
        for entry in feed.entries:
            paper = self.entry_to_paper(entry)
            if paper is not None:
                papers.append(paper)
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
