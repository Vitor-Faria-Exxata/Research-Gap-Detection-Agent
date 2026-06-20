"""Command-line entrypoint.

Examples:
    python -m research_gap_agent "Self-supervised learning for medical imaging"
    python -m research_gap_agent --json "topic..." --output report.json
    python -m research_gap_agent -vv "topic..."           # verbose logs
"""

import argparse
import json
import logging
import string
import sys
import unicodedata
from pathlib import Path
from typing import Optional

from research_gap_agent.schemas import FinalReport
from research_gap_agent.state import GraphState


def _inline_markdown(value: object) -> str:
    without_controls = "".join(
        (
            " "
            if unicodedata.category(character) in {"Cc", "Cf"}
            else character
        )
        for character in str(value)
    )
    normalized = " ".join(without_controls.split())
    return "".join(
        f"\\{character}"
        if character in string.punctuation
        else character
        for character in normalized
    )


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="research_gap_agent",
        description="Identify open research questions for a given topic.",
    )
    parser.add_argument("topic", help="Topic in natural language.")
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the final report as JSON instead of human-readable text.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Write the report to this file instead of stdout.",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Increase log verbosity (-v INFO, -vv DEBUG).",
    )
    return parser.parse_args(argv)


def configure_logging(verbosity: int) -> None:
    level = logging.WARNING
    if verbosity == 1:
        level = logging.INFO
    elif verbosity >= 2:
        level = logging.DEBUG

    logging.basicConfig(
        level=level,
        format="%(asctime)s  %(levelname)-7s  %(name)s  %(message)s",
    )


def render_report(report: Optional[FinalReport]) -> str:
    if report is None:
        return "(no report produced)"

    cutoff_date = (
        report.cutoff_date.isoformat()
        if report.cutoff_date
        else "unavailable"
    )
    lines = [
        f"# Research Gap Report — {_inline_markdown(report.topic)}",
        "",
        (
            "_Sources used: "
            + (
                ", ".join(
                    _inline_markdown(source)
                    for source in report.sources_used
                )
                or "none"
            )
            + "_"
        ),
        f"_Papers considered: {report.papers_considered}_",
        f"_Cutoff date: {cutoff_date}_",
        "",
        "## Warnings",
    ]

    if report.warnings:
        lines.extend(
            f"- {_inline_markdown(warning.code)}: "
            f"{_inline_markdown(warning.message)}"
            for warning in report.warnings
        )
    else:
        lines.append("_None._")

    lines.extend(
        [
            "",
            "## Summary",
            _inline_markdown(report.summary),
            "",
            "## Methodology",
            _inline_markdown(report.methodology_note),
            "",
            "## Candidate Research Gaps",
        ]
    )

    if not report.gaps:
        warning_codes = {warning.code for warning in report.warnings}
        if "no_extracted_insights" in warning_codes:
            lines.append(
                "Analysis was not performed because no structured article "
                "insights were available."
            )
        elif warning_codes & {
            "missing_evidence",
            "invalid_evidence_reference",
        }:
            lines.append(
                "Candidate research gaps returned by the analysis were "
                "discarded because their evidence failed integrity or "
                "traceability validation."
            )
        else:
            lines.append(
                "No candidate research gaps met the textual evidence "
                "threshold."
            )
    else:
        for i, gap in enumerate(report.gaps, start=1):
            lines.append(
                f"### {i}. {_inline_markdown(gap.research_question)}"
            )
            lines.append("")
            lines.append(_inline_markdown(gap.description))
            lines.append("")
            lines.append(
                f"**Evidence strength:** {gap.evidence_strength}/100"
            )
            lines.append("")
            lines.append(
                f"**Rationale:** {_inline_markdown(gap.rationale)}"
            )
            lines.append("")
            lines.append("#### Evidence")
            for evidence in gap.evidence:
                lines.append(
                    f"- {_inline_markdown(evidence.evidence_type)} \\| "
                    f"{_inline_markdown(evidence.paper_id)} \\| "
                    f"{_inline_markdown(evidence.description)}"
                )

            supporting_paper_ids = list(
                dict.fromkeys(
                    evidence.paper_id for evidence in gap.evidence
                )
            )
            if supporting_paper_ids:
                lines.append("")
                lines.append(
                    "**Supporting paper IDs:** "
                    + ", ".join(
                        _inline_markdown(paper_id)
                        for paper_id in supporting_paper_ids
                    )
                )

            if gap.counter_evidence:
                lines.append("")
                lines.append("#### Counter-evidence")
                for counter_evidence in gap.counter_evidence:
                    lines.append(
                        f"- {_inline_markdown(counter_evidence.paper_id)} "
                        f"\\| "
                        f"{_inline_markdown(counter_evidence.description)}"
                    )
            lines.append("")

    return "\n".join(lines)


def main(argv: Optional[list[str]] = None) -> int:
    args = parse_args(argv)
    configure_logging(args.verbose)

    from research_gap_agent.graph import build_graph

    graph = build_graph()
    initial_state = GraphState(initial_topic=args.topic)

    raw_final = graph.invoke(initial_state)
    if isinstance(raw_final, GraphState):
        final_state = raw_final
    else:
        final_state = GraphState.model_validate(raw_final)

    report = final_state.final_report

    if args.json:
        payload = report.model_dump(mode="json") if report else {}
        output = json.dumps(payload, indent=2, ensure_ascii=False)
    else:
        output = render_report(report)

    if args.output:
        args.output.write_text(output, encoding="utf-8")
    else:
        sys.stdout.write(output + "\n")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
