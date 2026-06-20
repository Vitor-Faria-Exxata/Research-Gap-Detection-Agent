from datetime import date
from types import SimpleNamespace

import pytest

import research_gap_agent.nodes.paper_extractor as paper_extractor_module
from research_gap_agent.schemas import ExtractedInsights, Paper
from research_gap_agent.state import GraphState


def _paper(
    paper_id: str,
    title: str,
    published_date: date,
) -> Paper:
    return Paper(
        id=paper_id,
        source="arxiv",
        title=title,
        abstract=f"Abstract for {title}",
        authors=["Researcher"],
        published_date=published_date,
        url=f"https://example.com/{paper_id}",
        pdf_url=f"https://example.com/{paper_id}.pdf",
        arxiv_id=paper_id,
    )


class FakeConverter:
    def __init__(self, results: list[str | None]):
        self.results = results

    def convert_batch(self, sources: list[str]) -> list[str | None]:
        return self.results


def _settings(*, use_arxiv_html: bool = False) -> SimpleNamespace:
    return SimpleNamespace(
        yaml=SimpleNamespace(
            document_converter=SimpleNamespace(
                provider_name="fake",
                use_arxiv_html=use_arxiv_html,
            )
        )
    )


def test_node_preserves_documents_and_initializes_minimum_insights(monkeypatch):
    papers = [
        _paper("paper:one", "Paper One", date(2024, 1, 2)),
        _paper("paper:two", "Paper Two", date(2025, 3, 4)),
    ]
    converter = FakeConverter(["# Paper One", "# Paper Two"])
    monkeypatch.setattr(
        paper_extractor_module,
        "load_settings",
        lambda: _settings(),
    )
    monkeypatch.setattr(
        paper_extractor_module,
        "get_converter",
        lambda provider: converter,
    )

    result = paper_extractor_module.paper_extractor_node(
        GraphState(initial_topic="Agent evaluation", ranked_papers=papers)
    )

    assert result["extracted_documents"] == [
        papers[0].model_copy(update={"full_text": "# Paper One"}),
        papers[1].model_copy(update={"full_text": "# Paper Two"}),
    ]
    assert all(
        isinstance(document, Paper)
        for document in result["extracted_documents"]
    )
    assert result["extracted"] == [
        ExtractedInsights(
            paper_id="paper:one",
            title="Paper One",
            published_date=date(2024, 1, 2),
            questions_answered=[],
            methodologies=[],
            not_addressed=[],
            stated_limitations=[],
        ),
        ExtractedInsights(
            paper_id="paper:two",
            title="Paper Two",
            published_date=date(2025, 3, 4),
            questions_answered=[],
            methodologies=[],
            not_addressed=[],
            stated_limitations=[],
        ),
    ]
    assert all(
        isinstance(insight, ExtractedInsights)
        for insight in result["extracted"]
    )


@pytest.mark.parametrize("empty_result", [None, ""])
def test_node_excludes_only_documents_without_non_empty_text(
    monkeypatch,
    empty_result,
):
    papers = [
        _paper("paper-1", "Paper One", date(2024, 1, 2)),
        _paper("paper-2", "Paper Two", date(2024, 2, 3)),
        _paper("paper-3", "Paper Three", date(2024, 3, 4)),
    ]
    converter = FakeConverter(["First text", empty_result, "Third text"])
    monkeypatch.setattr(
        paper_extractor_module,
        "load_settings",
        lambda: _settings(),
    )
    monkeypatch.setattr(
        paper_extractor_module,
        "get_converter",
        lambda provider: converter,
    )

    result = paper_extractor_module.paper_extractor_node(
        GraphState(initial_topic="Agent evaluation", ranked_papers=papers)
    )

    assert [
        document.id for document in result["extracted_documents"]
    ] == ["paper-1", "paper-3"]
    assert [
        document.full_text for document in result["extracted_documents"]
    ] == ["First text", "Third text"]
    assert [
        insight.paper_id for insight in result["extracted"]
    ] == ["paper-1", "paper-3"]


def test_graph_state_validates_node_output_with_both_extracted_fields(
    monkeypatch,
):
    paper = _paper("paper-1", "Paper One", date(2024, 1, 2))
    converter = FakeConverter(["Converted text"])
    monkeypatch.setattr(
        paper_extractor_module,
        "load_settings",
        lambda: _settings(),
    )
    monkeypatch.setattr(
        paper_extractor_module,
        "get_converter",
        lambda provider: converter,
    )
    original_state = GraphState(
        initial_topic="Agent evaluation",
        ranked_papers=[paper],
    )

    node_output = paper_extractor_module.paper_extractor_node(original_state)
    merged_state = GraphState.model_validate(
        {**original_state.model_dump(), **node_output}
    )

    assert merged_state.extracted_documents == [
        paper.model_copy(update={"full_text": "Converted text"})
    ]
    assert merged_state.extracted == [
        ExtractedInsights(
            paper_id="paper-1",
            title="Paper One",
            published_date=date(2024, 1, 2),
        )
    ]


def test_extracted_insights_dump_never_contains_full_text(monkeypatch):
    paper = _paper("paper-1", "Paper One", date(2024, 1, 2))
    converter = FakeConverter(["Converted text"])
    monkeypatch.setattr(
        paper_extractor_module,
        "load_settings",
        lambda: _settings(),
    )
    monkeypatch.setattr(
        paper_extractor_module,
        "get_converter",
        lambda provider: converter,
    )

    result = paper_extractor_module.paper_extractor_node(
        GraphState(initial_topic="Agent evaluation", ranked_papers=[paper])
    )

    assert all(
        "full_text" not in insight.model_dump()
        for insight in result["extracted"]
    )
