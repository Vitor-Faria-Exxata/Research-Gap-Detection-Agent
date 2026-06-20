from datetime import date

from research_gap_agent.prompts.gap_identifier import (
    build_gap_identifier_messages,
)
from research_gap_agent.schemas import ExtractedInsights


def test_prompt_contains_complete_corpus_and_domain_rules():
    insights = [
        ExtractedInsights(
            paper_id="paper-1",
            title="Longitudinal Agent Evaluation",
            published_date=date(2024, 6, 10),
            questions_answered=["How agents perform in short tasks"],
            methodologies=["Controlled benchmark"],
            not_addressed=["Long-term deployment"],
            stated_limitations=["No longitudinal follow-up"],
        ),
        ExtractedInsights(
            paper_id="paper-2",
            title="Agents in Clinical Workflows",
            published_date=date(2025, 2, 3),
            questions_answered=["How clinicians use agent assistance"],
            methodologies=["Field study"],
            not_addressed=["Cross-site replication"],
            stated_limitations=["Single-site sample"],
        ),
    ]

    messages = build_gap_identifier_messages(
        "Long-term reliability of AI agents",
        insights,
    )

    assert [role for role, _ in messages] == ["system", "human"]
    system_message = messages[0][1]
    human_message = messages[1][1]
    rendered = "\n".join(content for _, content in messages)

    assert "Long-term reliability of AI agents" in human_message
    for expected in [
        "paper-1",
        "Longitudinal Agent Evaluation",
        "2024-06-10",
        "How agents perform in short tasks",
        "Controlled benchmark",
        "Long-term deployment",
        "No longitudinal follow-up",
        "paper-2",
        "Agents in Clinical Workflows",
        "2025-02-03",
        "How clinicians use agent assistance",
        "Field study",
        "Cross-site replication",
        "Single-site sample",
    ]:
        assert expected in human_message

    for expected_rule in [
        "candidate gap",
        "observed corpus",
        "latest published_date",
        "stated_limitations",
        "explicitly describe limitations or future work",
        "recurring_not_addressed",
        "same or equivalent scope",
        "more than one article",
        "contrast",
        "answered questions imply a neighboring research question",
        "outside the observed scope",
        "paper_id",
        "faithful paraphrase",
        "clearly answers",
        "recurrence across independent articles increases",
        "explicit stated limitations are stronger than inferred contrast",
        "recurring not_addressed signals are stronger than one-off omissions",
        "thematic coherence with answered questions increases",
        "counterevidence lowers",
        "evidence_strength",
        "70 to 100",
        "evidence_strength >= 70",
        "GapIdentificationResult",
        "JSON",
    ]:
        assert expected_rule in system_message

    assert "graph evidence" in system_message.lower()
    assert "return the received insights" in system_message.lower()
    assert "complete article text" in system_message.lower()
    assert "full_text" not in rendered


def test_prompt_documents_supported_warning_codes_and_conditions():
    messages = build_gap_identifier_messages("Agent evaluation", [])
    system_message = messages[0][1]

    expected_warning_rules = {
        "no_extracted_insights": (
            "no structured article insights were available"
        ),
        "missing_evidence": "candidate contained no evidence",
        "invalid_evidence_reference": (
            "evidence referenced an unknown paper_id"
        ),
        "invalid_counter_evidence_reference": (
            "counterevidence referenced an unknown paper_id"
        ),
    }

    for code, condition in expected_warning_rules.items():
        assert code in system_message
        assert condition in system_message

    assert '"warnings": []' in system_message
    assert "node fills processing warnings" in system_message


def test_prompt_sends_all_insights_as_json_in_one_human_message():
    insights = [
        ExtractedInsights(
            paper_id="paper-1",
            title="Paper One",
            published_date=date(2025, 1, 2),
        ),
        ExtractedInsights(
            paper_id="paper-2",
            title="Paper Two",
            published_date=date(2025, 1, 3),
        ),
    ]

    messages = build_gap_identifier_messages("Agent evaluation", insights)
    human_messages = [content for role, content in messages if role == "human"]

    assert len(human_messages) == 1
    assert '"paper_id": "paper-1"' in human_messages[0]
    assert '"paper_id": "paper-2"' in human_messages[0]
    assert '"published_date": "2025-01-02"' in human_messages[0]
    assert '"published_date": "2025-01-03"' in human_messages[0]
    assert human_messages[0].index("paper-1") < human_messages[0].index("paper-2")
