"""LangGraph state for the Research Gap Agent.

LangGraph accepts Pydantic models as state schemas and merges each node's
return dict into the state automatically. So nodes only need to return the
keys they actually modified.

The state is filled progressively along the pipeline:
    query_rewriter   -> queries
    search           -> raw_papers
    ranker           -> ranked_papers
    paper_extractor  -> extracted
    graph_analyzer   -> graph_insight (parallel)
    gap_identifier   -> content_gaps
    aggregator       -> final_report
"""

from typing import Optional

from pydantic import BaseModel, Field

from research_gap_agent.schemas import (
    ExtractedInsights,
    FinalReport,
    GapIdentificationResult,
    GraphInsight,
    Paper,
    SearchQuery,
)


class GraphState(BaseModel):
    initial_topic: str

    queries: list[SearchQuery] = Field(default_factory=list)
    raw_papers: list[Paper] = Field(default_factory=list)
    ranked_papers: list[Paper] = Field(default_factory=list)
    extracted: list[ExtractedInsights] = Field(default_factory=list)

    graph_insight: Optional[GraphInsight] = None

    gap_identification: Optional[GapIdentificationResult] = None
    final_report: Optional[FinalReport] = None
