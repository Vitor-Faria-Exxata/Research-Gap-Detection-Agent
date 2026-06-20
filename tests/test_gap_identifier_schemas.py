from datetime import date

import pytest
from pydantic import ValidationError

from research_gap_agent.schemas import (
    CounterEvidence,
    ExtractedInsights,
    GapEvidence,
    GapIdentificationResult,
    IdentifiedGap,
)


def _gap_payload(**overrides):
    payload = {
        "research_question": "How does the effect change over time?",
        "description": "Longitudinal effects remain insufficiently studied.",
        "evidence_strength": 85,
        "evidence": [
            {
                "paper_id": "paper-1",
                "evidence_type": "stated_limitations",
                "description": "The paper calls for longitudinal follow-up.",
            }
        ],
        "rationale": "The corpus repeatedly identifies this missing scope.",
        "counter_evidence": [],
    }
    payload.update(overrides)
    return payload


@pytest.mark.parametrize("missing_field", ["title", "published_date"])
def test_extracted_insights_requires_title_and_published_date(missing_field):
    payload = {
        "paper_id": "paper-1",
        "title": "Paper One",
        "published_date": date(2025, 1, 2),
    }
    payload.pop(missing_field)

    with pytest.raises(ValidationError):
        ExtractedInsights(**payload)


def test_extracted_insights_keeps_independent_default_lists():
    first = ExtractedInsights(
        paper_id="paper-1",
        title="Paper One",
        published_date=date(2025, 1, 2),
    )
    second = ExtractedInsights(
        paper_id="paper-2",
        title="Paper Two",
        published_date=date(2025, 2, 3),
    )

    first.not_addressed.append("Longitudinal evaluation")

    assert first.questions_answered == []
    assert first.methodologies == []
    assert first.stated_limitations == []
    assert second.not_addressed == []


@pytest.mark.parametrize(
    "evidence_type",
    ["stated_limitations", "recurring_not_addressed", "contrast"],
)
def test_identified_gap_accepts_only_documented_evidence_types(evidence_type):
    gap = IdentifiedGap(
        **_gap_payload(
            evidence=[
                {
                    "paper_id": "paper-1",
                    "evidence_type": evidence_type,
                    "description": "Evidence from the corpus.",
                }
            ]
        )
    )

    assert gap.evidence[0].evidence_type == evidence_type

    with pytest.raises(ValidationError):
        IdentifiedGap(
            **_gap_payload(
                evidence=[
                    {
                        "paper_id": "paper-1",
                        "evidence_type": "graph_signal",
                        "description": "Unsupported evidence type.",
                    }
                ]
            )
        )


@pytest.mark.parametrize("score", [69, 101])
def test_identified_gap_rejects_scores_outside_70_to_100(score):
    with pytest.raises(ValidationError):
        IdentifiedGap(**_gap_payload(evidence_strength=score))


@pytest.mark.parametrize("score", [70, 100])
def test_identified_gap_accepts_score_boundaries(score):
    gap = IdentifiedGap(**_gap_payload(evidence_strength=score))

    assert gap.evidence_strength == score


def test_gap_identification_allows_null_cutoff_date():
    result = GapIdentificationResult(cutoff_date=None)

    assert result.cutoff_date is None
    assert result.warnings == []
    assert result.gaps == []


def test_identified_gap_uses_structured_evidence_without_legacy_fields():
    gap = IdentifiedGap(
        **_gap_payload(
            counter_evidence=[
                {
                    "paper_id": "paper-2",
                    "description": "A related setting has partial coverage.",
                }
            ]
        )
    )

    assert isinstance(gap.evidence[0], GapEvidence)
    assert isinstance(gap.counter_evidence[0], CounterEvidence)
    assert "supporting_paper_ids" not in IdentifiedGap.model_fields
    assert IdentifiedGap.model_fields["evidence"].annotation == list[GapEvidence]


@pytest.mark.parametrize(
    ("field_name", "field_value"),
    [
        ("supporting_paper_ids", ["paper-1"]),
        ("evidence_types", ["stated_limitations"]),
    ],
)
def test_identified_gap_rejects_prohibited_extra_fields(
    field_name,
    field_value,
):
    with pytest.raises(ValidationError):
        IdentifiedGap(**_gap_payload(**{field_name: field_value}))
