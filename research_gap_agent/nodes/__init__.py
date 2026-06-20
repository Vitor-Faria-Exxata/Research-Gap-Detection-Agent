<<<<<<< HEAD
from importlib import import_module
=======
"""LangGraph node functions, one per pipeline step.

The graph_analyzer node is the only one that pulls in a heavy optional
dependency (a spacy model loaded at import time). We try to import it
and silently drop it on failure so the rest of the pipeline keeps working
in environments that don't have the model installed. The graph builder
reads the `use_graph_analyzer` flag in `config.yaml` to decide whether
to wire the branch.
"""

import logging


logger = logging.getLogger(__name__)


from research_gap_agent.nodes.aggregator import aggregator_node
from research_gap_agent.nodes.gap_identifier import gap_identifier_node
from research_gap_agent.nodes.insight_extractor import insight_extractor_node
from research_gap_agent.nodes.paper_extractor import paper_extractor_node
from research_gap_agent.nodes.query_rewriter import query_rewriter_node
from research_gap_agent.nodes.ranker import ranker_node
from research_gap_agent.nodes.search import search_node
>>>>>>> origin/main

# Optional: graph_analyzer requires a spacy model that may not be
# installed in every environment. We log a single warning on failure
# and leave the symbol unbound; `graph.py` checks the config flag
# before trying to wire it.
try:
    from research_gap_agent.nodes.graph_analyzer import graph_analyzer_node
except Exception as exc:  # ImportError, OSError (missing spacy model), etc.
    logger.warning(
        "graph_analyzer_node unavailable (reason: %s: %s). "
        "The graph_analyzer branch will be skipped unless the dependency "
        "is installed and use_graph_analyzer=true in config.yaml.",
        exc.__class__.__name__, exc,
    )
    graph_analyzer_node = None  # type: ignore[assignment]


__all__ = [
    "query_rewriter_node",
    "search_node",
    "ranker_node",
    "paper_extractor_node",
    "insight_extractor_node",
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
