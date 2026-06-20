---
name: research-gap-identifier
description: Use when generating the prompt for the gap_identifier LLM in the Research Gap Detection Agent, especially from structured article insights, limitations, not-addressed scopes, publication dates, and candidate research gaps.
---

# Research Gap Identifier

## Purpose

Use this skill as the prompt contract for the `gap_identifier` LLM. It receives structured article insights and returns current candidate research gaps supported only by textual evidence from the articles.

## Domain Rules

- A **research gap** is a research question that has not yet been explored.
- A **current candidate gap** is a proposed gap that appears unexplored in the observed corpus up to the cutoff date.
- The **cutoff date** is the latest `published_date` among the structured article insights.
- Do not use graph evidence in this block.
- Do not claim definitive certainty; report candidates as hypotheses supported by the corpus.

## Input Contract

The LLM receives:

- `topic`: original user topic.
- `extracted_insights`: list of `ExtractedInsights` produced by `paper_extractor`, with:
  - `paper_id`
  - `title`
  - `published_date`
  - `questions_answered`
  - `methodologies`
  - `not_addressed`
  - `stated_limitations`

Do not expect or analyze `full_text`. Article interpretation belongs to
`paper_extractor`; this block compares the structured insights across papers.

Empty lists in an `ExtractedInsights` item are valid. They mean that the
previous block found no evidence for that field; they do not make the item
invalid.

Before identifying gaps, calculate `cutoff_date` as the latest
`published_date` among all received `extracted_insights`. Do not expect the
previous block to provide it.

Send the complete set of received `extracted_insights` in the same LLM analysis
request so the model can compare evidence across the corpus. Do not analyze
each paper independently in this block.

The initial implementation uses exactly one LLM call. In that call, the model
calculates `cutoff_date`, compares evidence and counterevidence, assigns
`evidence_strength`, filters candidates below the threshold, and returns the
structured result.

## Evidence Rules

Accept only these evidence types:

- `stated_limitations`: authors explicitly describe limitations or future work.
- `recurring_not_addressed`: the same or equivalent scope is marked as not addressed by more than one article.
- `contrast`: answered questions imply a neighboring research question that remains outside the observed scope.

Do not create additional evidence type labels. Every
`evidence[].evidence_type` value must be one of:

```text
stated_limitations
recurring_not_addressed
contrast
```

Counterevidence must be listed when the corpus contains a paper that partially
or fully addresses the proposed question. Each item must identify the related
`paper_id` and explain the caveat. Discard the candidate if the corpus clearly
answers the proposed question.

Every evidence `paper_id` must exactly match a `paper_id` from the received
`extracted_insights`. Never invent, normalize, shorten, or rewrite paper
identifiers. Every candidate must contain at least one evidence item.

## Scoring

The conceptual rubric for `evidence_strength` spans 0 to 100:

- recurrence across independent papers increases the score;
- explicit stated limitations are stronger than inferred contrast;
- recurring `not_addressed` signals are stronger than one-off omissions;
- thematic coherence with answered questions increases the score;
- counterevidence lowers the score.

The structured response contains only qualified candidates with
`evidence_strength` from 70 to 100. Conceptually score weaker candidates on the
same 0-to-100 rubric, then omit every candidate below 70 from the response.

## Output Contract

Return only valid JSON matching the `GapIdentificationResult` contract:

```json
{
  "cutoff_date": "YYYY-MM-DD",
  "warnings": [],
  "gaps": [
    {
      "research_question": "Clear unanswered research question.",
      "description": "One short paragraph describing the candidate gap.",
      "evidence_strength": 70,
      "evidence": [
        {
          "paper_id": "paper-id",
          "evidence_type": "stated_limitations",
          "description": "Evidence grounded in the structured article fields."
        }
      ],
      "rationale": "Why this qualifies as a current candidate gap.",
      "counter_evidence": [
        {
          "paper_id": "paper-id",
          "description": "Relevant caveat or partial answer from this paper."
        }
      ]
    }
  ]
}
```

When `extracted_insights` is non-empty, `cutoff_date` must be non-null and equal
to the latest received `published_date`.

For a non-empty input, the LLM must return `"warnings": []`. The node generates
processing warnings deterministically while validating the structured response;
warnings are not model-authored analysis.

Each object in `gaps` maps to the existing `IdentifiedGap` model. Despite the
technical name, every item must be phrased as a candidate gap relative to the
observed corpus, never as a definitive claim about the entire literature.

The target model is:

```python
class IdentifiedGap(BaseModel):
    research_question: str
    description: str
    evidence_strength: int
    evidence: list[GapEvidence]
    rationale: str
    counter_evidence: list[CounterEvidence]
```

Where:

```python
class CounterEvidence(BaseModel):
    paper_id: str
    description: str


class GapEvidence(BaseModel):
    paper_id: str
    evidence_type: EvidenceType
    description: str


EvidenceType = Literal[
    "stated_limitations",
    "recurring_not_addressed",
    "contrast",
]
```

The target structured model accepts `evidence_strength` only as an integer from
70 to 100. The conceptual scoring rubric remains 0 to 100, but scores below 70
must be filtered out before constructing the response. `cutoff_date` belongs
to the enclosing `GapIdentificationResult` and must not be duplicated in each
gap. Every counterevidence `paper_id` must exactly match a received insight.

Every evidence item must reference a received `paper_id`, use one allowed
`EvidenceType`, and explain the relevant signal from that article. Supporting
paper IDs are derived from `evidence[].paper_id`; do not return a separate
`supporting_paper_ids` field.

Write `GapEvidence.description` as a faithful paraphrase of the relevant
`ExtractedInsights` fields. Do not claim it is a verbatim quotation, invent a
quotation, or add information absent from the structured input.

Apply the same rule to `CounterEvidence.description`: use a faithful paraphrase
of the relevant structured insight, with no invented quotation or unsupported
information.

Do not return a separate `evidence_types` field. The candidate's evidence types
are derived from `evidence[].evidence_type`.

Each warning generated by the node must match:

```json
{
  "code": "stable_machine_readable_code",
  "message": "Human-readable explanation."
}
```

Use stable warning codes. The initial supported code is:

- `no_extracted_insights`: no structured article insights were available, so
  no gap analysis was performed.
- `invalid_counter_evidence_reference`: a counterevidence item referenced an
  unknown paper ID and was removed by the node.
- `invalid_evidence_reference`: an evidence item referenced an unknown paper ID
  and caused the candidate to be discarded.
- `missing_evidence`: a candidate contained no traceable evidence items and was
  discarded by the node.

The LLM does not emit these processing warnings. It returns an empty `warnings`
list, and the node creates the applicable warnings from deterministic
validation outcomes.

If no candidate reaches the threshold, return:

```json
{
  "cutoff_date": "YYYY-MM-DD",
  "warnings": [],
  "gaps": []
}
```

Do not return or rewrite the received `ExtractedInsights`. The
`gap_identifier` node preserves the original input directly in the application
state. When there are inputs but no qualifying gaps, return an empty `gaps`
list.

The node stores the validated response in `GraphState.gap_identification`.
The `aggregator` consumes this complete object rather than a separate
`content_gaps` list.

Remove individual counterevidence items whose `paper_id` is unknown and append
an `invalid_counter_evidence_reference` warning. Do not automatically discard
the enclosing gap solely because one counterevidence reference is invalid.

Discard a candidate when any evidence item references an unknown paper ID or
when its `evidence` list is empty. Append the corresponding structured warning,
preserve other valid gaps, and do not make a second LLM call.

If `extracted_insights` is empty, do not infer gaps and do not invent a cutoff
date. Return:

```json
{
  "cutoff_date": null,
  "warnings": [
    {
      "code": "no_extracted_insights",
      "message": "No structured article insights were available for gap identification."
    }
  ],
  "gaps": []
}
```

## Prompt Assembly Checklist

- Include the domain rules before article data.
- Calculate and include the cutoff date explicitly.
- Require a non-null cutoff date whenever insights are present.
- Include all `ExtractedInsights`, not full paper text.
- Send all received insights together for corpus-level analysis.
- Use exactly one LLM call in the initial implementation.
- Do not ask the LLM to return or rewrite the received insights.
- Require every evidence paper ID to exist in the received insights.
- Require at least one evidence item per candidate.
- Use faithful paraphrases for evidence descriptions.
- Require every counterevidence paper ID to exist in the received insights.
- Use faithful paraphrases for counterevidence descriptions.
- Discard only candidates with invalid or missing evidence and add a structured
  warning.
- Require the LLM to return `warnings: []`; generate warnings deterministically
  in the node.
- Return the structured `no_extracted_insights` warning for an empty input.
- Require JSON-only output.
- Remind the LLM that graph evidence is unavailable in this block.
