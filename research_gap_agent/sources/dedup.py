"""Deduplication of papers across the three sources.

Two papers are considered the same when they share ANY of:
  - DOI (case-insensitive)
  - arXiv ID
  - normalized title (lowercase, punctuation stripped)

When a duplicate is found we keep the "richer" copy - the one with more
fields populated, the better open-access tier, and arXiv as a tiebreaker
(arXiv PDFs are the most stable to download from).
"""

import logging
import re

from research_gap_agent.schemas import Paper


logger = logging.getLogger(__name__)

# Score the open-access tier so we can compare two versions of the same paper.
# Higher is better. Anything not in this dict gets 0.
OA_RANK = {"gold": 4, "hybrid": 3, "green": 2, "bronze": 1}

# Tiebreaker when papers are otherwise equal.
SOURCE_RANK = {"arxiv": 3, "openalex": 2, "semantic_scholar": 1}


def normalize_title(title: str) -> str:
    """Lowercase the title and strip punctuation and extra whitespace."""
    title = title.lower()
    title = re.sub(r"[^\w\s]", " ", title)
    title = re.sub(r"\s+", " ", title)
    return title.strip()


def richness(paper: Paper) -> tuple:
    """Score a paper so we can compare duplicates and pick the better one.

    We return a tuple so Python's tuple comparison handles tiebreaking from
    left to right: first compare populated fields, then OA tier, then source.
    """
    populated_fields = sum(
        1
        for value in (
            paper.doi,
            paper.arxiv_id,
            paper.abstract,
            paper.authors,
            paper.categories,
        )
        if value
    )
    oa_score = OA_RANK.get(paper.oa_status or "", 0)
    source_score = SOURCE_RANK.get(paper.source, 0)
    return (populated_fields, oa_score, source_score)


def dedup_papers(papers: list[Paper]) -> list[Paper]:
    """Return a deduplicated list of papers, keeping the richest copy of each.

    The algorithm keeps three lookup tables (DOI, arXiv ID, normalized
    title). For each new paper we check whether any of its identifiers
    already point to a known paper; if so we compare richness and keep the
    better one. Otherwise the paper joins the pool with its own entry.
    """
    if not papers:
        return []

    # Maps identifier -> index inside `survivors`. Sharing the same index
    # across the three maps is what links them.
    doi_to_index: dict[str, int] = {}
    arxiv_to_index: dict[str, int] = {}
    title_to_index: dict[str, int] = {}
    survivors: list[Paper] = []

    def register(index: int, paper: Paper) -> None:
        """Add this paper's identifiers to the lookup tables."""
        if paper.doi:
            doi_to_index[paper.doi.lower().strip()] = index
        if paper.arxiv_id:
            arxiv_to_index[paper.arxiv_id.lower().strip()] = index
        if paper.title:
            title_to_index[normalize_title(paper.title)] = index

    for paper in papers:
        # Try to find an existing entry that shares any identifier with us.
        existing_index = None
        if paper.doi and paper.doi.lower().strip() in doi_to_index:
            existing_index = doi_to_index[paper.doi.lower().strip()]
        elif paper.arxiv_id and paper.arxiv_id.lower().strip() in arxiv_to_index:
            existing_index = arxiv_to_index[paper.arxiv_id.lower().strip()]
        elif paper.title and normalize_title(paper.title) in title_to_index:
            existing_index = title_to_index[normalize_title(paper.title)]

        if existing_index is None:
            survivors.append(paper)
            register(len(survivors) - 1, paper)
            continue

        # We have a duplicate: keep the richer paper.
        current = survivors[existing_index]
        if richness(paper) > richness(current):
            survivors[existing_index] = paper
        # Either way, register the loser's identifiers too — they might
        # help link a future paper to this group.
        register(existing_index, survivors[existing_index])

    logger.info(
        "Deduplication: %d papers in, %d unique out (%d duplicates merged).",
        len(papers),
        len(survivors),
        len(papers) - len(survivors),
    )
    return survivors
