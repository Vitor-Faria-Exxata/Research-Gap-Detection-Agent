import logging
from research_gap_agent.nodes.paper_extractor import paper_extractor_node
from research_gap_agent.nodes.insight_extractor import insight_extractor_node
from .mock_papers import MOCK_PAPERS

logging.basicConfig(level=logging.INFO)


class MockStateForExtractor:
    def __init__(self, ranked_papers):
        self.ranked_papers = ranked_papers


class MockStateForInsight:
    def __init__(self, extracted):
        self.extracted = extracted


def run_realistic_test():
    print("\n--Starting insight_extractor integration test--")
    print(f"Running with {len(MOCK_PAPERS)} mock paper(s) from mock_papers.py\n")

    # Step 1: real paper_extractor downloads PDFs and turns them into markdown.
    extractor_state = MockStateForExtractor(ranked_papers=MOCK_PAPERS)
    extractor_result = paper_extractor_node(extractor_state)
    extracted = extractor_result["extracted"]

    print(
        f"paper_extractor produced markdown for {len(extracted)} paper(s); "
        f"total chars: {sum(len(p.full_text or '') for p in extracted)}\n"
    )

    # Step 2: real insight_extractor calls the real LLM on each paper.
    insight_state = MockStateForInsight(extracted=extracted)
    result = insight_extractor_node(insight_state)

    print(f"insight_extractor produced {len(result['insights'])} ExtractedInsights\n")

    for insight in result["insights"]:
        print(f"--- Paper {insight.paper_id} ---")
        print(f"  questions_answered ({len(insight.questions_answered)}):")
        for q in insight.questions_answered:
            print(f"    - {q}")
        print(f"  methodologies ({len(insight.methodologies)}):")
        for m in insight.methodologies:
            print(f"    - {m}")
        print(f"  not_addressed ({len(insight.not_addressed)}):")
        for n in insight.not_addressed:
            print(f"    - {n}")
        print(f"  stated_limitations ({len(insight.stated_limitations)}):")
        for l in insight.stated_limitations:
            print(f"    - {l}")
        print()


if __name__ == "__main__":
    run_realistic_test()
