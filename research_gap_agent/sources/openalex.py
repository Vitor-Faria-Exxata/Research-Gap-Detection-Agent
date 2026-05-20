"""OpenAlex source.

We hit the public endpoint with `filter=is_oa:true` so the server
only returns open-access papers. We then drop any record without a usable
pdf_url, because OA in OpenAlex sometimes means "free to read on a webpage"
rather than "PDF you can download".

Abstracts are stored as an inverted index (word -> [positions]). We need to
rebuild the plain text before passing it downstream.

API docs: https://docs.openalex.org/api-entities/works
"""

import logging
from datetime import datetime
from typing import Optional

import requests

from research_gap_agent.schemas import Paper
from research_gap_agent.sources.base import PaperSource


logger = logging.getLogger(__name__)

API_URL = "https://api.openalex.org/works"


def reconstruct_abstract(inverted_index: Optional[dict]) -> str:
    """Rebuild a plain-text abstract from OpenAlex's inverted index.

    The index maps each word to a list of positions where it appears, so we
    flatten it back into (position, word) pairs, sort by position, and join.
    """
    if not inverted_index:
        return ""

    positions = []
    for word, word_positions in inverted_index.items():
        for pos in word_positions:
            positions.append((pos, word))

    positions.sort()
    return " ".join(word for _, word in positions)


def pick_pdf_url(work: dict) -> Optional[str]:
    """Return a PDF URL from the OpenAlex work, or None if not available."""
    best = (work.get("best_oa_location") or {}).get("pdf_url")
    if best:
        return best
    primary = (work.get("primary_location") or {}).get("pdf_url")
    return primary


def parse_date(date_str: Optional[str]):
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return None


def extract_arxiv_id_from_work(work: dict) -> Optional[str]:
    """OpenAlex sometimes stores the arXiv URL inside the ids dict."""
    ids = work.get("ids") or {}
    for value in ids.values():
        if isinstance(value, str) and "arxiv.org/abs/" in value:
            return value.rsplit("/", 1)[-1]
    return None


def normalize_doi(doi: Optional[str]) -> Optional[str]:
    """Strip the URL prefix from a DOI so it can be matched against other sources."""
    if not doi:
        return None
    if doi.startswith("https://doi.org/"):
        return doi[len("https://doi.org/"):]
    return doi


class OpenAlexSource(PaperSource):
    name = "openalex"

    def __init__(self, timeout_s: int = 30):
        self.timeout_s = timeout_s

    def search(self, query: str, limit: int) -> list[Paper]:
        params = {
            "search": query,
            "per-page": min(limit, 200),  # OpenAlex caps per-page at 200
            "filter": "is_oa:true",
        }
        headers = {}

        try:
            response = requests.get(
                API_URL, params=params, headers=headers, timeout=self.timeout_s
            )
            response.raise_for_status()
            payload = response.json()
        except requests.RequestException as exc:
            logger.warning("OpenAlex request failed for query=%r: %s", query, exc)
            return []

        papers = []
        for work in payload.get("results", []):
            paper = self.work_to_paper(work)
            if paper is not None:
                papers.append(paper)
        return papers

    def work_to_paper(self, work: dict) -> Optional[Paper]:
        """Convert one OpenAlex work into a Paper, or None if data is missing."""
        try:
            pdf_url = pick_pdf_url(work)
            if not pdf_url:
                # Flagged as OA but no actual PDF - drop it.
                return None

            abstract = reconstruct_abstract(work.get("abstract_inverted_index"))
            if not abstract:
                return None

            published = parse_date(work.get("publication_date"))
            if published is None:
                return None

            openalex_id = (work.get("id") or "").rsplit("/", 1)[-1]
            if not openalex_id:
                return None

            authors = []
            for authorship in work.get("authorships", []):
                author = authorship.get("author") or {}
                name = author.get("display_name")
                if name:
                    authors.append(name)

            concepts = work.get("concepts") or []
            categories = [
                c.get("display_name", "")
                for c in concepts[:5]
                if c.get("display_name")
            ]

            landing = (
                (work.get("primary_location") or {}).get("landing_page_url")
                or work.get("id")
                or ""
            )

            return Paper(
                id=f"openalex:{openalex_id}",
                source="openalex",
                title=work.get("display_name") or "",
                abstract=abstract,
                authors=authors,
                published_date=published,
                url=landing,
                pdf_url=pdf_url,
                is_open_access=True,
                oa_status=(work.get("open_access") or {}).get("oa_status"),
                doi=normalize_doi(work.get("doi")),
                arxiv_id=extract_arxiv_id_from_work(work),
                categories=categories,
            )
        except (AttributeError, ValueError, KeyError) as exc:
            logger.debug("Skipping malformed OpenAlex work: %s", exc)
            return None
