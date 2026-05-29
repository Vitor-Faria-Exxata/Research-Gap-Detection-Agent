import logging
from unittest.mock import patch, MagicMock
from research_gap_agent.nodes.paper_extractor import paper_extractor_node
from .mock_papers import MOCK_PAPERS

logging.basicConfig(level=logging.INFO)

class MockState:
    def __init__(self, papers):
        self.ranked_papers = papers


@patch('research_gap_agent.nodes.paper_extractor.load_settings')
def run_realistic_test(mock_load_settings):
    mock_settings = MagicMock()
    
    mock_settings.yaml.document_converter.provider_name = "pymupdf" 
    mock_settings.yaml.document_converter.use_arxiv_fallback = True
    mock_load_settings.return_value = mock_settings
    
    state = MockState(papers=MOCK_PAPERS)

    print("\n--Starting integration test--")
    
    result = paper_extractor_node(state)

    print("\n-- EXTRACTION RESULTS --")
    for insight in result["extracted"]:
        print(f"\n--- Paper ID: {insight.id} ---")
        
        # Replace newlines with spaces just so it prints cleanly in the terminal
        md_preview = insight.full_text[:5000]
        
        print(f"Preview: {md_preview}...\n")
        print(f"Total Markdown Length: {len(insight.full_text)} characters")

if __name__ == "__main__":
    run_realistic_test()