import logging
from unittest.mock import patch, MagicMock
from research_gap_agent.nodes.ranker import ranker_node
from research_gap_agent.schemas import SearchQuery
from mock_papers import MOCK_PAPERS

logging.basicConfig(level=logging.INFO)

class MockState:
    def __init__(self, queries, raw_papers):
        self.queries = queries
        self.raw_papers = raw_papers


@patch('research_gap_agent.nodes.ranker.load_settings')
def run_realistic_test(mock_load_settings):
    mock_settings = MagicMock()

    mock_settings.yaml.pipeline.top_papers = 3
    mock_settings.yaml.reranker.provider_name = "cross-encoder"
    mock_settings.yaml.reranker.fallback = None
    mock_load_settings.return_value = mock_settings

    state = MockState(
        queries=[SearchQuery(
            text="Self-supervised learning for medical imaging",
            rationale="Test query",
        )],
        raw_papers=MOCK_PAPERS,
    )

    print("\n--Starting integration test--")

    result = ranker_node(state)

    print("\n-- RANKING RESULTS --")
    for i, paper in enumerate(result["ranked_papers"], 1):
        print(f"\n--- #{i}: {paper.id} ---")
        print(f"Title: {paper.title}")
        print(f"Abstract: {paper.abstract[:200]}...")


if __name__ == "__main__":
    run_realistic_test()
