"""LangGraph wiring.

Pipeline shape:

    START -> query_rewriter -+-> search -> ranker -> paper_extractor -> gap_identifier -+
                             |                                                          |
                             +-> graph_analyzer ----------------------------------------+-> aggregator -> END

LangGraph handles the fan-in for us: aggregator only runs once both
branches have written to the state, because both gap_identifier and
graph_analyzer have edges pointing into it.
"""

from langgraph.graph import END, START, StateGraph

from research_gap_agent.nodes import (
    aggregator_node,
    gap_identifier_node,
    graph_analyzer_node,
    paper_extractor_node,
    query_rewriter_node,
    ranker_node,
    search_node,
)
from research_gap_agent.state import GraphState


def build_graph():
    workflow = StateGraph(GraphState)

    # Register one node per pipeline step.
    workflow.add_node("query_rewriter", query_rewriter_node)
    workflow.add_node("search", search_node)
    workflow.add_node("ranker", ranker_node)
    workflow.add_node("paper_extractor", paper_extractor_node)
    workflow.add_node("graph_analyzer", graph_analyzer_node)
    workflow.add_node("gap_identifier", gap_identifier_node)
    workflow.add_node("aggregator", aggregator_node)

    workflow.add_edge(START, "query_rewriter")

    # Fan out after query_rewriter: text branch and graph branch run in parallel.
    workflow.add_edge("query_rewriter", "search")

    # Text branch.
    workflow.add_edge("search", "ranker")
    workflow.add_edge("ranker", "paper_extractor")
    workflow.add_edge("paper_extractor", "graph_analyzer") # My section will use the extracted papers as input to the graph analyzer
    workflow.add_edge("paper_extractor", "gap_identifier")

    # Fan in: both branches feed into aggregator.
    workflow.add_edge("gap_identifier", "aggregator")
    workflow.add_edge("graph_analyzer", "aggregator")

    workflow.add_edge("aggregator", END)

    return workflow.compile()
