"""Data models shared by all nodes in the pipeline.

These Pydantic models define the contracts between nodes. Whenever a node
reads or writes a piece of structured data, it should use one of the models
below so that we get validation for free at every step.
"""

from datetime import date
from typing import Literal, Optional

from pydantic import BaseModel, Field


SourceName = Literal["arxiv", "openalex", "semantic_scholar"]


class SearchQuery(BaseModel):
    """A single search query produced by the query rewriter."""

    text: str
    rationale: str


class Paper(BaseModel):
    """A normalized academic paper.

    Every Paper that flows past the search node is guaranteed to be open
    access and to have a working pdf_url, so downstream nodes can download
    the full text without worrying about paywalls.
    """

    id: str
    source: SourceName
    title: str
    abstract: str
    authors: list[str] = Field(default_factory=list)
    published_date: date
    url: str
    pdf_url: str
    is_open_access: bool = True
    oa_status: Optional[str] = None
    doi: Optional[str] = None
    arxiv_id: Optional[str] = None
    categories: list[str] = Field(default_factory=list)
    full_text: Optional[str] = None


class ExtractedInsights(BaseModel):
    """Structured extraction from a single paper.

    Produced by the paper_extractor node. The four fields mirror the
    questions defined in the project spec.
    """

    paper_id: str
    questions_answered: list[str] = Field(default_factory=list)
    methodologies: list[str] = Field(default_factory=list)
    not_addressed: list[str] = Field(default_factory=list)
    stated_limitations: list[str] = Field(default_factory=list)


class GraphInsight(BaseModel):
    """Output of the graph analyzer.

    TODO(caio): may need to change.
    """

    summary: str
    disconnected_pairs: list[tuple[str, str]] = Field(default_factory=list)
    raw: dict = Field(default_factory=dict)


class IdentifiedGap(BaseModel):
    """A candidate research gap built from the extracted insights."""

    description: str
    supporting_paper_ids: list[str] = Field(default_factory=list)
    evidence: str


class FinalReport(BaseModel):
    """What the user sees at the end of the pipeline."""

    topic: str
    gaps: list[IdentifiedGap]
    summary: str
    methodology_note: str
    sources_used: list[SourceName]
    papers_considered: int
