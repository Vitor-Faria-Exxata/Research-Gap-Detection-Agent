from research_gap_agent.sources.arxiv import ArxivSource
from research_gap_agent.sources.base import PaperSource
from research_gap_agent.sources.dedup import dedup_papers
from research_gap_agent.sources.openalex import OpenAlexSource
from research_gap_agent.sources.semantic_scholar import SemanticScholarSource

__all__ = [
    "PaperSource",
    "ArxivSource",
    "OpenAlexSource",
    "SemanticScholarSource",
    "dedup_papers",
]
