"""Command-line entrypoint.

Examples:
    python -m research_gap_agent "Self-supervised learning for medical imaging"
    python -m research_gap_agent --json "topic..." --output report.json
    python -m research_gap_agent -vv "topic..."           # verbose logs
    python -m research_gap_agent "topic..." --stop-after insight_extractor
"""

import argparse
import json
import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

from research_gap_agent.graph import TEXT_CHAIN, build_graph
from research_gap_agent.cli.render import render_partial_state, render_report
from research_gap_agent.state import GraphState


LOG_FORMAT = "%(asctime)s  %(levelname)-7s  %(name)s  %(message)s"
LOG_DIR = Path("logs")
LOG_FILE = LOG_DIR / "research_gap_agent.log"
LOG_MAX_BYTES = 10 * 1024 * 1024
LOG_BACKUP_COUNT = 3


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
        "--stop-after",
        choices=TEXT_CHAIN,
        default=None,
        help=(
            "Terminate the pipeline after the given node and print the "
            "intermediate state. Useful while downstream nodes are still TODO."
        ),
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
    # Root level stays at INFO so the file handler always gets something
    # useful, even on default-verbosity runs. The console handler does the
    # per-verbosity filtering so the user only sees what they asked for.
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    for h in list(root.handlers):
        root.removeHandler(h)

    formatter = logging.Formatter(LOG_FORMAT)

    console_level = logging.WARNING
    if verbosity == 1:
        console_level = logging.INFO
    elif verbosity >= 2:
        console_level = logging.DEBUG
    console = logging.StreamHandler()
    console.setLevel(console_level)
    console.setFormatter(formatter)
    root.addHandler(console)

    if os.environ.get("RGA_LOG_TO_FILE", "true").lower() in ("1", "true", "yes"):
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            LOG_FILE,
            maxBytes=LOG_MAX_BYTES,
            backupCount=LOG_BACKUP_COUNT,
            encoding="utf-8",
        )
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)


def _coerce_state(raw_final) -> GraphState:
    if isinstance(raw_final, GraphState):
        return raw_final
    return GraphState.model_validate(raw_final)


def main(argv: Optional[list[str]] = None) -> int:
    args = parse_args(argv)
    configure_logging(args.verbose)

    graph = build_graph(stop_after=args.stop_after)
    initial_state = GraphState(initial_topic=args.topic)

    final_state = _coerce_state(graph.invoke(initial_state))

    if args.stop_after:
        payload = final_state.model_dump(mode="json")
        output = json.dumps(payload, indent=2, ensure_ascii=False) if args.json \
            else render_partial_state(final_state, args.stop_after)
    else:
        report = final_state.final_report
        payload = report.model_dump(mode="json") if report else {}
        output = json.dumps(payload, indent=2, ensure_ascii=False) if args.json \
            else render_report(report)

    if args.output:
        args.output.write_text(output, encoding="utf-8")
    else:
        sys.stdout.write(output + "\n")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
