"""LangGraph wiring.

Pipeline shape:

    START -> query_rewriter -> search -> ranker -> paper_extractor ─┬─> insight_extractor -> gap_identifier ─┐
                                                                    |                                          |
                                                                    +-> graph_analyzer ───────────────────────┴─> aggregator -> END

`stop_after` lets a caller terminate the graph after a given node — useful
while downstream nodes are still TODO. When stopped, the graph_analyzer
branch and the aggregator are dropped so the graph terminates cleanly.

The `graph_analyzer` branch sources from `paper_extractor` (not from
`query_rewriter`) because it consumes the extracted papers. The
`graph_analyzer -> aggregator` edge guarantees aggregator waits for the
graph insight to be written to state.
"""

from typing import Optional

from langgraph.graph import END, START, StateGraph

from research_gap_agent.nodes import (
    aggregator_node,
    gap_identifier_node,
    graph_analyzer_node,
    insight_extractor_node,
    paper_extractor_node,
    query_rewriter_node,
    ranker_node,
    search_node,
)
from research_gap_agent.state import GraphState


# Ordered list of nodes on the text branch. The order here IS the pipeline
# order; everything else in this file follows from it.
TEXT_CHAIN = [
    "query_rewriter",
    "search",
    "ranker",
    "paper_extractor",
    "insight_extractor",
    "gap_identifier",
    "aggregator",
]

NODES = {
    "query_rewriter": query_rewriter_node,
    "search": search_node,
    "ranker": ranker_node,
    "paper_extractor": paper_extractor_node,
    "insight_extractor": insight_extractor_node,
    "graph_analyzer": graph_analyzer_node,
    "gap_identifier": gap_identifier_node,
    "aggregator": aggregator_node,
}


def build_graph(stop_after: Optional[str] = None):
    if stop_after is not None and stop_after not in TEXT_CHAIN:
        raise ValueError(
            f"Unknown stop_after={stop_after!r}. "
            f"Valid options: {TEXT_CHAIN}"
        )

    workflow = StateGraph(GraphState)
    for name, fn in NODES.items():
        workflow.add_node(name, fn)

    workflow.add_edge(START, "query_rewriter")

    # Truncate the text chain if a stop point was requested.
    chain = TEXT_CHAIN if stop_after is None else TEXT_CHAIN[: TEXT_CHAIN.index(stop_after) + 1]

    for src, dst in zip(chain, chain[1:]):
        workflow.add_edge(src, dst)

    # graph_analyzer consumes the extracted papers, so it branches off
    # paper_extractor (not query_rewriter). The edge into aggregator keeps
    # the fan-in: aggregator only runs after both gap_identifier and
    # graph_analyzer have written to state. Only include the branch when
    # the text chain reaches the aggregator — otherwise the output would
    # be discarded.
    if chain[-1] == "aggregator":
        workflow.add_edge("paper_extractor", "graph_analyzer")
        workflow.add_edge("graph_analyzer", "aggregator")

    workflow.add_edge(chain[-1], END)

    return workflow.compile()
