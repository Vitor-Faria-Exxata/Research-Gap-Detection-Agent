"""Command-line entrypoint.

Examples:
    python -m research_gap_agent "Self-supervised learning for medical imaging"
    python -m research_gap_agent --json "topic..." --output report.json
    python -m research_gap_agent -vv "topic..."           # verbose logs
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Optional

from research_gap_agent.graph import build_graph
from research_gap_agent.schemas import FinalReport
from research_gap_agent.state import GraphState


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


def main(argv: Optional[list[str]] = None) -> int:
    args = parse_args(argv)
    configure_logging(args.verbose)

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
