from datetime import date
import json
import string
import subprocess
import sys

import pytest

from research_gap_agent.cli import _inline_markdown, render_report
from research_gap_agent.schemas import (
    CounterEvidence,
    FinalReport,
    GapEvidence,
    GapWarning,
    IdentifiedGap,
)


def _report(
    *,
    gaps: list[IdentifiedGap],
    warnings: list[GapWarning] | None = None,
    cutoff_date: date | None = date(2025, 4, 3),
) -> FinalReport:
    return FinalReport(
        topic="Longitudinal effects of AI agents",
        cutoff_date=cutoff_date,
        warnings=warnings or [],
        gaps=gaps,
        summary="Found candidate gaps in the available corpus.",
        methodology_note="Compared structured textual evidence.",
        sources_used=["arxiv", "openalex"],
        papers_considered=4,
    )


def test_render_report_includes_structured_candidate_gap_details():
    gap = IdentifiedGap(
        research_question="How do AI-agent effects change over time?",
        description="Longitudinal effects remain insufficiently studied.",
        evidence_strength=88,
        evidence=[
            GapEvidence(
                paper_id="paper-2",
                evidence_type="stated_limitations",
                description="The study requests longer follow-up.",
            ),
            GapEvidence(
                paper_id="paper-2",
                evidence_type="contrast",
                description="Only short-term outcomes were measured.",
            ),
            GapEvidence(
                paper_id="paper-1",
                evidence_type="recurring_not_addressed",
                description="Repeated evaluations omit longitudinal effects.",
            ),
        ],
        rationale="Multiple papers leave the same temporal scope unresolved.",
        counter_evidence=[
            CounterEvidence(
                paper_id="paper-3",
                description="One study includes a limited follow-up period.",
            )
        ],
    )
    report = _report(
        gaps=[gap],
        warnings=[
            GapWarning(
                code="invalid_counter_evidence_reference",
                message="An invalid counterevidence item was removed.",
            )
        ],
    )

    rendered = render_report(report)

    assert (
        "# Research Gap Report — Longitudinal effects of AI agents"
        in rendered
    )
    assert "_Sources used: arxiv, openalex_" in rendered
    assert "_Papers considered: 4_" in rendered
    assert "_Cutoff date: 2025-04-03_" in rendered
    assert "## Warnings" in rendered
    assert (
        "- invalid\\_counter\\_evidence\\_reference: "
        "An invalid counterevidence item was removed\\."
    ) in rendered
    assert "## Summary" in rendered
    assert "Found candidate gaps in the available corpus\\." in rendered
    assert "## Methodology" in rendered
    assert "Compared structured textual evidence\\." in rendered
    assert "## Candidate Research Gaps" in rendered
    assert (
        "### 1. How do AI\\-agent effects change over time\\?"
        in rendered
    )
    assert "Longitudinal effects remain insufficiently studied\\." in rendered
    assert "**Evidence strength:** 88/100" in rendered
    assert (
        "**Rationale:** Multiple papers leave the same temporal scope "
        "unresolved\\."
    ) in rendered
    assert (
        "- stated\\_limitations \\| paper\\-2 \\| "
        "The study requests longer follow\\-up\\."
    ) in rendered
    assert (
        "- contrast \\| paper\\-2 \\| "
        "Only short\\-term outcomes were measured\\."
    ) in rendered
    assert (
        "- recurring\\_not\\_addressed \\| paper\\-1 \\| "
        "Repeated evaluations omit longitudinal effects\\."
    ) in rendered
    assert "**Supporting paper IDs:** paper\\-2, paper\\-1" in rendered
    assert "paper\\-2, paper\\-2" not in rendered
    assert "#### Counter-evidence" in rendered
    assert (
        "- paper\\-3 \\| One study includes a limited "
        "follow\\-up period\\."
    ) in rendered


def test_render_report_explains_empty_result_without_extracted_insights():
    report = _report(
        gaps=[],
        warnings=[
            GapWarning(
                code="no_extracted_insights",
                message="No structured article insights were available.",
            )
        ],
        cutoff_date=None,
    )

    rendered = render_report(report)

    assert "_Cutoff date: unavailable_" in rendered
    assert "## Candidate Research Gaps" in rendered
    assert (
        "Analysis was not performed because no structured article insights "
        "were available."
    ) in rendered


def test_render_report_explains_empty_result_below_textual_threshold():
    rendered = render_report(_report(gaps=[], warnings=[]))

    assert (
        "No candidate research gaps met the textual evidence threshold."
    ) in rendered


def test_render_report_explains_empty_result_after_missing_evidence():
    report = _report(
        gaps=[],
        warnings=[
            GapWarning(
                code="missing_evidence",
                message="A candidate contained no evidence.",
            )
        ],
    )

    rendered = render_report(report)

    assert (
        "Candidate research gaps returned by the analysis were discarded "
        "because their evidence failed integrity or traceability validation."
    ) in rendered
    assert "textual evidence threshold" not in rendered


def test_render_report_explains_empty_result_after_invalid_reference():
    report = _report(
        gaps=[],
        warnings=[
            GapWarning(
                code="invalid_evidence_reference",
                message="A candidate referenced an unknown paper.",
            )
        ],
    )

    rendered = render_report(report)

    assert (
        "Candidate research gaps returned by the analysis were discarded "
        "because their evidence failed integrity or traceability validation."
    ) in rendered
    assert "textual evidence threshold" not in rendered


def test_render_report_normalizes_and_escapes_free_text():
    unsafe = (
        "Line one\n# Fake heading `code` | [link] <tag> "
        "*em* _under_ \\ tail"
    )
    escaped = (
        "Line one \\# Fake heading \\`code\\` \\| \\[link\\] "
        "\\<tag\\> \\*em\\* \\_under\\_ \\\\ tail"
    )
    gap = IdentifiedGap(
        research_question=unsafe,
        description=unsafe,
        evidence_strength=90,
        evidence=[
            GapEvidence(
                paper_id="paper`1|[source]",
                evidence_type="stated_limitations",
                description=unsafe,
            )
        ],
        rationale=unsafe,
        counter_evidence=[
            CounterEvidence(
                paper_id="counter`1|[source]",
                description=unsafe,
            )
        ],
    )
    report = FinalReport(
        topic=unsafe,
        cutoff_date=date(2025, 4, 3),
        warnings=[
            GapWarning(
                code="warning`code|[value]",
                message=unsafe,
            )
        ],
        gaps=[gap],
        summary=unsafe,
        methodology_note=unsafe,
        sources_used=["semantic_scholar"],
        papers_considered=1,
    )

    rendered = render_report(report)

    assert f"# Research Gap Report — {escaped}" in rendered
    assert "_Sources used: semantic\\_scholar_" in rendered
    assert (
        "- warning\\`code\\|\\[value\\]: "
        f"{escaped}"
    ) in rendered
    assert f"### 1. {escaped}" in rendered
    assert (
        "- stated\\_limitations \\| "
        "paper\\`1\\|\\[source\\] \\| "
        f"{escaped}"
    ) in rendered
    assert (
        "**Supporting paper IDs:** paper\\`1\\|\\[source\\]"
    ) in rendered
    assert (
        "- counter\\`1\\|\\[source\\] \\| "
        f"{escaped}"
    ) in rendered
    assert rendered.count(escaped) >= 7
    assert "\n# Fake heading" not in rendered
    assert "\n| " not in rendered
    assert unsafe not in rendered


def test_render_report_neutralizes_unicode_control_characters():
    controls = "\x1b\x07\x9b"
    gap = IdentifiedGap(
        research_question=f"Gap{controls}question?",
        description=f"Gap{controls}description.",
        evidence_strength=90,
        evidence=[
            GapEvidence(
                paper_id=f"paper{controls}1",
                evidence_type="contrast",
                description=f"Evidence{controls}description.",
            )
        ],
        rationale=f"Gap{controls}rationale.",
    )
    report = FinalReport(
        topic=f"Unsafe{controls}topic",
        cutoff_date=date(2025, 4, 3),
        warnings=[
            GapWarning(
                code=f"warning{controls}code",
                message=f"Warning{controls}message.",
            )
        ],
        gaps=[gap],
        summary="Summary.",
        methodology_note="Methodology.",
        sources_used=["arxiv"],
        papers_considered=1,
    )

    rendered = render_report(report)

    assert "# Research Gap Report — Unsafe topic" in rendered
    assert "- warning code: Warning message\\." in rendered
    assert "### 1. Gap question\\?" in rendered
    assert "Gap description\\." in rendered
    assert "paper 1" in rendered
    assert "Evidence description\\." in rendered
    assert "Gap rationale\\." in rendered
    assert all(control not in rendered for control in controls)


def test_inline_markdown_neutralizes_unicode_format_characters():
    format_characters = "\u202e\u2066\u2069\u200b\u200c\u200d\ufeff"

    rendered = _inline_markdown(f"safe{format_characters}text")

    assert rendered == "safe text"
    assert all(
        character not in rendered
        for character in format_characters
    )


@pytest.mark.parametrize(
    ("value", "escaped"),
    [
        ("~~~python", "\\~\\~\\~python"),
        ("---", "\\-\\-\\-"),
        ("- item", "\\- item"),
        ("+ item", "\\+ item"),
        ("1. item", "1\\. item"),
        ("> quote", "\\> quote"),
        ("```python", "\\`\\`\\`python"),
        ("\\# heading", "\\\\\\# heading"),
    ],
)
def test_inline_markdown_escapes_structural_prefixes(value, escaped):
    rendered = _inline_markdown(value)

    assert rendered == escaped
    assert not rendered.startswith(("~~~", "---", "- ", "+ ", "> ", "```"))
    assert "1. item" not in rendered
    assert "```" not in rendered
    assert "~~~" not in rendered


def test_inline_markdown_escapes_every_ascii_punctuation_character():
    rendered = _inline_markdown(string.punctuation)
    expected = "".join(f"\\{character}" for character in string.punctuation)

    assert rendered == expected


def test_final_report_model_dump_serializes_cutoff_date_as_json():
    payload = _report(gaps=[]).model_dump(mode="json")

    assert payload["cutoff_date"] == "2025-04-03"
    assert json.dumps(payload)


def test_importing_cli_does_not_load_graph_or_graph_analyzer():
    script = """
import sys

import research_gap_agent.cli

assert "research_gap_agent.graph" not in sys.modules
assert "research_gap_agent.nodes.graph_analyzer" not in sys.modules
"""

    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr


def test_main_help_exits_before_importing_graph():
    script = """
import builtins

import research_gap_agent.cli as cli

original_import = builtins.__import__

def guarded_import(name, *args, **kwargs):
    if name == "research_gap_agent.graph":
        raise AssertionError("graph imported before --help completed")
    return original_import(name, *args, **kwargs)

builtins.__import__ = guarded_import

try:
    cli.main(["--help"])
except SystemExit as exc:
    assert exc.code == 0
else:
    raise AssertionError("--help did not exit")
"""

    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert "usage: research_gap_agent" in result.stdout
