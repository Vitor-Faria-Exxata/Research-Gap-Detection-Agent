"""
Insight extractor node.

Sits between paper_extractor and gap_identifier on the text branch. For each
paper whose PDF has already been converted to markdown, it asks an LLM four
questions and stores the answers in an ExtractedInsights record:

    1. What was answered?        -> questions_answered
    2. How it was answered?      -> methodologies
    3. What wasn't addressed?    -> not_addressed
    4. What was presented as a
       limitation?                -> stated_limitations

The LLM call is issued once per paper in parallel, bounded by
`pipeline.llm_max_concurrency` (NOT the search-step `max_workers`, because
the free-tier NVIDIA endpoint returns 429 on more than ~2 concurrent chat
completions). A failure on one paper is logged and skipped so the rest of
the batch still produces insights; transient rate-limit / 5xx errors are
retried with exponential backoff.
"""

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from research_gap_agent.config import load_settings
from research_gap_agent.llm import get_llm
from research_gap_agent.prompts.insight_extractor import (
    INSIGHT_EXTRACTOR_SYSTEM,
    INSIGHT_EXTRACTOR_USER,
)
from research_gap_agent.schemas import ExtractedInsights, Paper
from research_gap_agent.state import GraphState


logger = logging.getLogger(__name__)

# Soft cap on the per-paper text sent to the LLM. Keeps prompts inside the
# context window of the smaller models and avoids one giant paper starving
# the rest of the batch.
MAX_TEXT_CHARS = 80_000

# Retry settings for transient LLM errors (429, 5xx, network).
LLM_MAX_RETRIES = 3
LLM_RETRY_BASE_S = 2.0


def _is_retryable(exc: Exception) -> bool:
    """True if the exception looks like a transient rate-limit / 5xx / network error."""
    # openai >= 1.x surfaces HTTP status via the error body.
    status = getattr(exc, "status_code", None) or getattr(exc, "code", None)
    if status in (408, 409, 425, 429, 500, 502, 503, 504):
        return True
    name = exc.__class__.__name__.lower()
    if "ratelimit" in name or "timeout" in name or "connection" in name or "httpx" in name:
        return True
    msg = str(exc).lower()
    return "rate limit" in msg or "429" in msg or "too many requests" in msg


def _extract_for_paper(paper: Paper, llm) -> tuple[str, ExtractedInsights]:
    if not paper.full_text:
        logger.debug("paper %s has no full_text; emitting empty insights.", paper.id)
        return paper.id, ExtractedInsights(paper_id=paper.id)

    text = paper.full_text
    if len(text) > MAX_TEXT_CHARS:
        logger.debug(
            "truncating full_text for %s from %d to %d chars",
            paper.id, len(text), MAX_TEXT_CHARS,
        )
        text = text[:MAX_TEXT_CHARS]

    messages = [
        ("system", INSIGHT_EXTRACTOR_SYSTEM),
        (
            "human",
            INSIGHT_EXTRACTOR_USER.format(title=paper.title, text=text),
        ),
    ]

    last_exc: Exception | None = None
    result = None
    for attempt in range(1, LLM_MAX_RETRIES + 1):
        try:
            result = llm.invoke(messages)
            last_exc = None
            break
        except Exception as exc:
            last_exc = exc
            if attempt < LLM_MAX_RETRIES and _is_retryable(exc):
                wait = LLM_RETRY_BASE_S * (2 ** (attempt - 1))
                logger.warning(
                    "LLM extraction for %s failed (attempt %d/%d): %s. Retrying in %.1fs.",
                    paper.id, attempt, LLM_MAX_RETRIES, exc, wait,
                )
                time.sleep(wait)
                continue
            break

    if last_exc is not None:
        logger.warning("LLM extraction failed for paper %s: %s", paper.id, last_exc)
        return paper.id, ExtractedInsights(paper_id=paper.id)

    # `result` is an ExtractedInsights thanks to with_structured_output. We
    # re-construct with paper_id forced to the real paper id so the field is
    # always correct even if the model returned something else.
    return paper.id, ExtractedInsights(
        paper_id=paper.id,
        questions_answered=list(getattr(result, "questions_answered", []) or []),
        methodologies=list(getattr(result, "methodologies", []) or []),
        not_addressed=list(getattr(result, "not_addressed", []) or []),
        stated_limitations=list(getattr(result, "stated_limitations", []) or []),
    )


def insight_extractor_node(state: GraphState) -> dict:
    settings = load_settings()
    max_workers = settings.yaml.pipeline.llm_max_concurrency

    llm = get_llm("insight_extractor").with_structured_output(ExtractedInsights)

    papers = state.extracted
    if not papers:
        logger.warning("insight_extractor_node: no papers to process.")
        return {"insights": []}

    insights_by_id: dict[str, ExtractedInsights] = {}

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {
            pool.submit(_extract_for_paper, paper, llm): paper.id
            for paper in papers
        }
        for future in as_completed(futures):
            paper_id, insights = future.result()
            insights_by_id[paper_id] = insights

    insights = [insights_by_id[p.id] for p in papers if p.id in insights_by_id]

    n_with_text = sum(1 for p in papers if p.full_text)
    logger.info(
        "insight_extractor_node: produced %d ExtractedInsights from %d papers "
        "(%d had full_text, concurrency=%d).",
        sum(1 for i in insights if i.questions_answered or i.methodologies
            or i.not_addressed or i.stated_limitations),
        len(papers),
        n_with_text,
        max_workers,
    )
    return {"insights": insights}
