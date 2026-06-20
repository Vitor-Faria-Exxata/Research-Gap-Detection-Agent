import subprocess
import sys

from research_gap_agent.schemas import GapIdentificationResult
from research_gap_agent.state import GraphState


def test_state_preserves_extracted_and_gap_identification(extracted_insight):
    gap_identification = GapIdentificationResult(cutoff_date=None)

    state = GraphState(
        initial_topic="Longitudinal effects of AI agents",
        extracted=[extracted_insight],
        gap_identification=gap_identification,
    )

    assert state.extracted == [extracted_insight]
    assert state.gap_identification == gap_identification
    assert "content_gaps" not in GraphState.model_fields


def test_package_imports_are_lazy_and_preserve_public_apis():
    script = """
import sys

import research_gap_agent
import research_gap_agent.nodes
import research_gap_agent.schemas
import research_gap_agent.state
import research_gap_agent.nodes.gap_identifier

assert "research_gap_agent.graph" not in sys.modules
assert "research_gap_agent.nodes.graph_analyzer" not in sys.modules
assert research_gap_agent.__all__ == ["build_graph", "GraphState"]
assert research_gap_agent.nodes.__all__ == [
    "query_rewriter_node",
    "search_node",
    "ranker_node",
    "paper_extractor_node",
    "graph_analyzer_node",
    "gap_identifier_node",
    "aggregator_node",
]
assert research_gap_agent.GraphState.__name__ == "GraphState"
assert callable(research_gap_agent.nodes.gap_identifier_node)
assert "research_gap_agent.graph" not in sys.modules
assert "research_gap_agent.nodes.graph_analyzer" not in sys.modules
"""

    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
