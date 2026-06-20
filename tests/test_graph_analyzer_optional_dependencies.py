from datetime import date

import research_gap_agent.nodes.graph_analyzer as graph_analyzer_module
from research_gap_agent.schemas import Paper
from research_gap_agent.state import GraphState


def test_graph_analyzer_returns_stub_when_optional_dependency_is_missing(
    monkeypatch,
):
    def fail_graph_analysis(texts: list[str]):
        raise ModuleNotFoundError("No module named 'spacy'")

    monkeypatch.setattr(
        graph_analyzer_module,
        "_run_graph_analysis",
        fail_graph_analysis,
    )

    state = GraphState(
        initial_topic="Long-term reliability of AI agents",
        ranked_papers=[
            Paper(
                id="paper-1",
                source="arxiv",
                title="Paper One",
                abstract="Agent reliability is evaluated over short horizons.",
                authors=["Researcher"],
                published_date=date(2025, 1, 10),
                url="https://example.com/paper-1",
                pdf_url="https://example.com/paper-1.pdf",
            )
        ],
    )

    result = graph_analyzer_module.graph_analyzer_node(state)
    insight = result["graph_insight"]

    assert (
        insight.summary
        == "Graph analysis skipped because optional NLP dependencies are unavailable."
    )
    assert insight.disconnected_pairs == []
    assert insight.raw["stub"] is True
    assert insight.raw["detail"] == "No module named 'spacy'"
