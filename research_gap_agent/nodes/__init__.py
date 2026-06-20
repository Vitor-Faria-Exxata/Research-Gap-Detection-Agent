from importlib import import_module

__all__ = [
    "query_rewriter_node",
    "search_node",
    "ranker_node",
    "paper_extractor_node",
    "graph_analyzer_node",
    "gap_identifier_node",
    "aggregator_node",
]

_NODE_MODULES = {
    "query_rewriter_node": "query_rewriter",
    "search_node": "search",
    "ranker_node": "ranker",
    "paper_extractor_node": "paper_extractor",
    "graph_analyzer_node": "graph_analyzer",
    "gap_identifier_node": "gap_identifier",
    "aggregator_node": "aggregator",
}


def __getattr__(name: str):
    module_name = _NODE_MODULES.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    value = getattr(
        import_module(f"research_gap_agent.nodes.{module_name}"),
        name,
    )
    globals()[name] = value
    return value
