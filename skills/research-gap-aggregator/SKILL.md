---
name: research-gap-aggregator
description: Use when generating the prompt for the aggregator LLM in the Research Gap Detection Agent, especially when merging textual candidate gaps with graph niches and producing the final research-gap report.
---

# Research Gap Aggregator

## Purpose

Use this skill as the prompt contract for the `aggregator` LLM. It receives textual candidate gaps and graph niches, then produces one final ranked list of candidate research gaps.

## Domain Rules

- The final output contains **candidate** research gaps, not proven gaps.
- The graph cannot create a final gap by itself.
- No `graph_only` output is allowed.
- A graph niche may refine or strengthen a textual candidate gap.
- A textual gap that passed the threshold must remain in the final output unless it is a semantic duplicate of a stronger gap or the corpus clearly answers it.

## Input Contract

The LLM receives:

- `topic`: original user topic.
- `cutoff_date`: cutoff date used by the textual gap identifier.
- `textual_candidate_gaps`: gaps from `gap_identifier`.
- `ranked_graph_hypotheses`: the exact list stored in
  `graph_insight.raw["ranked_hypotheses"]`. Each item may contain:
  - `concepts`
  - `missing_links`
  - `avg_similarity`
  - `cross_community`
  - `edge_count`
  - `future_bonus`
  - `base_score`
  - `score`
  - `diversified_score`
  - ranking penalties

Do not use `graph_insight.summary`, the aggregated `disconnected_pairs`, or
the other `raw` metrics as LLM input in the initial version.
- `methodology_context`: sources, number of queries, papers retrieved, and papers considered.

## Fusion Rules

For each textual candidate, compare it against the ranked graph hypotheses.
Treat each hypothesis as an operational graph niche for matching purposes.

A valid match requires:

- overlap or clear equivalence between central concepts;
- compatibility between the textual research question and the underexplored graph relation;
- a short explanation of how the niche refines the question.

When a match is valid, refine the research question using the graph niche and mark `origin` as `textual_and_graph`. When no match is valid, preserve the textual candidate and mark `origin` as `textual_only`.
`origin` is required for every final gap. For `textual_only`, set
`matched_graph_hypothesis` and `graph_refinement` to `null`. For
`textual_and_graph`, fill both fields.

Do not add graph niches that have no matching textual candidate.

## Ranking Rules

Rank final gaps in this order:

1. `textual_and_graph`
2. `textual_only`

Within each group, sort by textual `evidence_strength` descending. Graph strength may break ties, but must not replace textual evidence.

## Output Contract

Return the complete `FinalReport` as structured output. Do not return an
intermediate aggregation result that must later be converted into a report.
Keep `IdentifiedGap` as the schema for every item in `FinalReport.gaps`; do not
introduce a separate final-gap model.
`IdentifiedGap` includes the optional fusion fields `origin`,
`matched_graph_hypothesis`, and `graph_refinement`.
The initial implementation accepts the model's values as returned once they
pass `FinalReport` schema validation; it does not reconcile report fields with
the graph state after the call.

Return only valid JSON:

```json
{
  "summary": "Short summary of the final candidate gaps.",
  "methodology_note": "Mention that gaps are candidates observed in the corpus up to the cutoff date.",
  "gaps": [
    {
      "research_question": "Final refined or preserved research question.",
      "description": "One short paragraph.",
      "origin": "textual_only",
      "evidence_strength": 0,
      "evidence": [
        {
          "paper_id": "paper-id",
          "evidence_type": "stated_limitations",
          "description": "Paraphrased evidence."
        }
      ],
      "matched_graph_hypothesis": null,
      "graph_refinement": null,
      "counter_evidence": [
        {
          "paper_id": "paper-id",
          "description": "Paraphrased counter-evidence."
        }
      ],
      "rationale": "Why this appears to be a candidate gap."
    }
  ]
}
```

For `textual_and_graph`, fill `matched_graph_hypothesis` with the full ranked
graph hypothesis dict used in the fusion and `graph_refinement` with how it
changed or sharpened the question.

## Prompt Assembly Checklist

- Include the no-`graph_only` rule near the top.
- Include all textual candidates before graph niches.
- Include ranked graph hypotheses as refinement context, not as independent
  final gaps.
- Require JSON-only output.
- Preserve traceability to supporting paper IDs.
