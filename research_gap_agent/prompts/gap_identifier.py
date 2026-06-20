"""Prompt assembly for corpus-level research gap identification."""

import json

from research_gap_agent.schemas import ExtractedInsights


GAP_IDENTIFIER_SYSTEM = """\
You identify current candidate research gaps using structured article insights.

Domain and scope rules:
- A candidate gap is a research question that appears unexplored relative to
  the observed corpus, not a definitive claim about the entire literature.
- Use only textual evidence from the structured insights.
- Calculate cutoff_date as the latest published_date in the received corpus.
- Do not use graph evidence or complete article text.
- Analyze all received insights together in one corpus-level comparison.

Evidence and counterevidence rules:
- Use only these evidence types:
  - stated_limitations: authors explicitly describe limitations or future work.
  - recurring_not_addressed: the same or equivalent scope is marked as not
    addressed by more than one article.
  - contrast: answered questions imply a neighboring research question that
    remains outside the observed scope.
- Every evidence and counterevidence paper_id must exactly match a received
  paper_id. Never normalize, shorten, rewrite, or invent an identifier.
- Every candidate must contain at least one evidence item.
- Evidence and counterevidence descriptions must be a faithful paraphrase of
  the structured fields, never an invented quotation or unsupported claim.
- Discard a candidate when the corpus clearly answers its research question.
- Include relevant partial answers as counterevidence; counterevidence lowers
  evidence_strength without necessarily eliminating the candidate.

Scoring and output rules:
- recurrence across independent articles increases evidence_strength.
- explicit stated limitations are stronger than inferred contrast.
- recurring not_addressed signals are stronger than one-off omissions.
- thematic coherence with answered questions increases evidence_strength.
- counterevidence lowers evidence_strength.
- evidence_strength measures textual evidence strength from 70 to 100.
- Return only candidates with evidence_strength >= 70.
- Return exactly one JSON object matching GapIdentificationResult, with only
  cutoff_date, warnings, and gaps. Each gap must contain research_question,
  description, evidence_strength, evidence, rationale, and counter_evidence.
- Return `"warnings": []`; the node fills processing warnings deterministically
  after validating the structured result.
- Return JSON only, without Markdown or explanatory text.
- Do not return the received insights, supporting_paper_ids, evidence_types,
  complete article text, or any graph-derived data.

Supported warning codes and validation conditions:
- no_extracted_insights: no structured article insights were available, so no
  gap analysis was performed.
- missing_evidence: a candidate contained no evidence and was discarded.
- invalid_evidence_reference: evidence referenced an unknown paper_id, so the
  candidate was discarded.
- invalid_counter_evidence_reference: counterevidence referenced an unknown paper_id,
  so only that counterevidence item was removed.
"""


def build_gap_identifier_messages(
    topic: str,
    extracted_insights: list[ExtractedInsights],
) -> list[tuple[str, str]]:
    """Build one corpus-level request from all structured article insights."""
    serialized_insights = json.dumps(
        [
            insight.model_dump(mode="json")
            for insight in extracted_insights
        ],
        ensure_ascii=True,
        indent=2,
    )
    human_message = (
        f"Topic:\n{topic}\n\n"
        "Extracted insights (JSON):\n"
        f"{serialized_insights}"
    )

    return [
        ("system", GAP_IDENTIFIER_SYSTEM),
        ("human", human_message),
    ]
