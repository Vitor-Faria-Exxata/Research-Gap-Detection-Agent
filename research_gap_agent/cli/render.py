"""Render the final report and intermediate pipeline state as markdown.

Pure functions — no I/O, no globals. Imported by `cli.py`.
"""

from typing import Optional

from research_gap_agent.schemas import FinalReport
from research_gap_agent.state import GraphState


INSIGHT_SECTIONS = [
    ("questions_answered", "Questions answered"),
    ("methodologies", "Methodologies"),
    ("not_addressed", "Not addressed"),
    ("stated_limitations", "Stated limitations"),
]


def render_report(report: Optional[FinalReport]) -> str:
    if report is None:
        return "(no report produced)"

    lines = [
        f"# Research Gap Report — {report.topic}",
        "",
        f"_Sources used: {', '.join(report.sources_used) or 'none'}_",
        f"_Papers considered: {report.papers_considered}_",
        "",
        "## Summary",
        report.summary,
        "",
        "## Methodology",
        report.methodology_note,
        "",
        "## Identified Gaps",
    ]

    if not report.gaps:
        lines.append("_None — gap_identifier returned an empty list._")
    else:
        for i, gap in enumerate(report.gaps, start=1):
            lines.append(f"### {i}. {gap.description}")
            lines.append("")
            lines.append(gap.evidence)
            if gap.supporting_paper_ids:
                lines.append("")
                lines.append(
                    "_Supporting papers: "
                    + ", ".join(gap.supporting_paper_ids)
                    + "_"
                )
            lines.append("")

    return "\n".join(lines)


def _render_insight(insight, title_lookup) -> list[str]:
    title = title_lookup.get(insight.paper_id, insight.paper_id)
    lines = [f"### {insight.paper_id} — {title}"]
    for field, label in INSIGHT_SECTIONS:
        items = getattr(insight, field) or []
        lines.append(f"  - {label} ({len(items)}):")
        if not items:
            lines.append("    _(empty)_")
        else:
            for it in items:
                lines.append(f"    - {it}")
    lines.append("")
    return lines


def render_partial_state(state: GraphState, stop_after: str) -> str:
    """Human-readable summary of the state at an intermediate node."""
    lines = [
        f"# Partial state — stopped after `{stop_after}`",
        "",
        f"_Topic: {state.initial_topic}_",
        "",
        f"- queries:        {len(state.queries)}",
        f"- raw_papers:     {len(state.raw_papers)}",
        f"- ranked_papers:  {len(state.ranked_papers)}",
        f"- extracted:      {len(state.extracted)}",
        f"- insights:       {len(state.insights)}",
    ]
    if state.graph_insight is not None:
        lines.append(f"- graph_insight:  present ({state.graph_insight.summary[:80]})")
    if state.content_gaps:
        lines.append(f"- content_gaps:   {len(state.content_gaps)}")
    if state.final_report is not None:
        lines.append(f"- final_report:   present")

    if state.queries:
        lines += ["", "## Queries"]
        for i, q in enumerate(state.queries, 1):
            lines.append(f"{i}. **{q.text}** — {q.rationale}")

    if stop_after in ("insight_extractor", "gap_identifier", "aggregator") and state.insights:
        title_lookup = {p.id: p.title for p in state.extracted}
        lines += ["", "## Insights"]
        for insight in state.insights:
            lines += _render_insight(insight, title_lookup)

    return "\n".join(lines)
