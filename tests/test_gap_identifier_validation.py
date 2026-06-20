from datetime import date

import pytest

from research_gap_agent.nodes.gap_identifier import (
    validate_gap_identification,
)
from research_gap_agent.schemas import (
    CounterEvidence,
    ExtractedInsights,
    GapEvidence,
    GapIdentificationResult,
    GapWarning,
    IdentifiedGap,
)


def _insights() -> list[ExtractedInsights]:
    return [
        ExtractedInsights(
            paper_id="paper-1",
            title="Paper One",
            published_date=date(2025, 1, 2),
        ),
        ExtractedInsights(
            paper_id="paper-2",
            title="Paper Two",
            published_date=date(2025, 2, 3),
        ),
    ]


def _gap(
    question: str,
    *,
    evidence: list[GapEvidence] | None = None,
    counter_evidence: list[CounterEvidence] | None = None,
) -> IdentifiedGap:
    return IdentifiedGap(
        research_question=question,
        description="A candidate gap relative to the corpus.",
        evidence_strength=82,
        evidence=(
            [
                GapEvidence(
                    paper_id="paper-1",
                    evidence_type="stated_limitations",
                    description="The paper requests follow-up work.",
                )
            ]
            if evidence is None
            else evidence
        ),
        rationale="The textual evidence supports this candidate.",
        counter_evidence=counter_evidence or [],
    )


def test_rejects_missing_cutoff_when_extracted_insights_are_available():
    result = GapIdentificationResult(
        cutoff_date=None,
        gaps=[],
    )

    with pytest.raises(
        ValueError,
        match=(
            "^cutoff_date is required when extracted insights are available$"
        ),
    ):
        validate_gap_identification(result, _insights())


def test_rejects_cutoff_that_differs_from_latest_insight_publication_date():
    result = GapIdentificationResult(
        cutoff_date=date(2025, 1, 2),
        gaps=[],
    )

    with pytest.raises(
        ValueError,
        match=(
            "^cutoff_date must equal the latest extracted insight "
            "publication date$"
        ),
    ):
        validate_gap_identification(result, _insights())


def test_keeps_valid_gap_and_ignores_all_llm_warnings():
    result = GapIdentificationResult(
        cutoff_date=date(2025, 2, 3),
        warnings=[
            GapWarning(
                code="invented_warning",
                message="The LLM invented this processing warning.",
            ),
            GapWarning(
                code="invalid_counter_evidence_reference",
                message="The LLM duplicated a supported processing warning.",
            ),
        ],
        gaps=[_gap("What remains unexplored?")],
    )

    validated = validate_gap_identification(result, _insights())

    assert validated.warnings == []
    assert validated.gaps == result.gaps
    assert validated.cutoff_date == date(2025, 2, 3)
    assert validated.gaps[0].evidence_strength == 82


def test_discards_only_gap_without_evidence_and_warns():
    valid_gap = _gap("Which valid question remains?")
    missing_evidence_gap = _gap(
        "Which unsupported question remains?",
        evidence=[],
    )
    result = GapIdentificationResult(
        cutoff_date=date(2025, 2, 3),
        warnings=[],
        gaps=[valid_gap, missing_evidence_gap],
    )

    validated = validate_gap_identification(result, _insights())

    assert validated.gaps == [valid_gap]
    assert validated.warnings == [
        GapWarning(
            code="missing_evidence",
            message=(
                "Discarded candidate gap 'Which unsupported question "
                "remains?' because it contained no evidence."
            ),
        )
    ]
    assert result.gaps == [valid_gap, missing_evidence_gap]


def test_discards_only_gap_with_unknown_evidence_reference_and_warns():
    invalid_gap = _gap(
        "Which invalidly supported question remains?",
        evidence=[
            GapEvidence(
                paper_id="unknown-paper",
                evidence_type="contrast",
                description="This reference is not in the corpus.",
            )
        ],
    )
    valid_gap = _gap("Which valid question remains?")
    result = GapIdentificationResult(
        cutoff_date=date(2025, 2, 3),
        warnings=[
            GapWarning(
                code="invalid_evidence_reference",
                message="The LLM must not supply processing warnings.",
            )
        ],
        gaps=[invalid_gap, valid_gap],
    )

    validated = validate_gap_identification(result, _insights())

    assert validated.gaps == [valid_gap]
    assert validated.warnings == [
        GapWarning(
            code="invalid_evidence_reference",
            message=(
                "Discarded candidate gap 'Which invalidly supported question "
                "remains?' because evidence referenced unknown paper_id "
                "'unknown-paper'."
            ),
        ),
    ]
    assert validated.cutoff_date == result.cutoff_date


def test_invalid_evidence_emits_one_warning_with_unique_ids_in_first_seen_order():
    invalid_gap = _gap(
        "Which multiply unsupported question remains?",
        evidence=[
            GapEvidence(
                paper_id="unknown-b",
                evidence_type="contrast",
                description="First invalid reference.",
            ),
            GapEvidence(
                paper_id="unknown-a",
                evidence_type="stated_limitations",
                description="Second invalid reference.",
            ),
            GapEvidence(
                paper_id="unknown-b",
                evidence_type="recurring_not_addressed",
                description="Repeated invalid reference.",
            ),
        ],
    )
    result = GapIdentificationResult(
        cutoff_date=date(2025, 2, 3),
        gaps=[invalid_gap],
    )

    validated = validate_gap_identification(result, _insights())

    assert validated.gaps == []
    assert validated.warnings == [
        GapWarning(
            code="invalid_evidence_reference",
            message=(
                "Discarded candidate gap 'Which multiply unsupported "
                "question remains?' because evidence referenced unknown "
                "paper_ids 'unknown-b', 'unknown-a'."
            ),
        )
    ]


def test_removes_only_unknown_counter_evidence_and_warns():
    gap = _gap(
        "How does the effect change over time?",
        counter_evidence=[
            CounterEvidence(
                paper_id="paper-2",
                description="A valid partial answer.",
            ),
            CounterEvidence(
                paper_id="unknown-paper",
                description="An invalid partial answer.",
            ),
            CounterEvidence(
                paper_id="paper-1",
                description="Another valid caveat.",
            ),
        ],
    )
    result = GapIdentificationResult(
        cutoff_date=date(2025, 2, 3),
        gaps=[gap],
    )

    validated = validate_gap_identification(result, _insights())

    assert validated.gaps[0].counter_evidence == [
        gap.counter_evidence[0],
        gap.counter_evidence[2],
    ]
    assert validated.warnings == [
        GapWarning(
            code="invalid_counter_evidence_reference",
            message=(
                "Removed counterevidence from candidate gap 'How does the "
                "effect change over time?' because it referenced unknown "
                "paper_id 'unknown-paper'."
            ),
        )
    ]
    assert len(result.gaps[0].counter_evidence) == 3


def test_validated_result_is_referentially_independent_from_llm_result():
    gap = _gap(
        "How does the effect change over time?",
        counter_evidence=[
            CounterEvidence(
                paper_id="paper-2",
                description="A valid partial answer.",
            ),
            CounterEvidence(
                paper_id="unknown-paper",
                description="An invalid partial answer.",
            ),
        ],
    )
    result = GapIdentificationResult(
        cutoff_date=date(2025, 2, 3),
        gaps=[gap],
    )

    validated = validate_gap_identification(result, _insights())

    result.gaps[0].evidence[0].description = "Mutated original evidence."
    result.gaps[0].counter_evidence[0].description = "Mutated original caveat."
    validated.gaps[0].rationale = "Mutated validated rationale."

    assert (
        validated.gaps[0].evidence[0].description
        == "The paper requests follow-up work."
    )
    assert (
        validated.gaps[0].counter_evidence[0].description
        == "A valid partial answer."
    )
    assert result.gaps[0].rationale == (
        "The textual evidence supports this candidate."
    )
