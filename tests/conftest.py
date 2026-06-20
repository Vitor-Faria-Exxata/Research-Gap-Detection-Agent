from datetime import date
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture
def extracted_insight():
    from research_gap_agent.schemas import ExtractedInsights

    return ExtractedInsights(
        paper_id="paper-1",
        title="Paper One",
        published_date=date(2025, 1, 2),
        questions_answered=[],
        methodologies=[],
        not_addressed=["Longitudinal evaluation"],
        stated_limitations=[],
    )
