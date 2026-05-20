"""Search node

For each (source, query) pair we hit the corresponding API in a worker
thread. All papers go into one big list, which is then deduplicated before
being written back to the state.

Every Paper that leaves this node is open access and has a working pdf_url,
because each source implementation drops records that fail those checks.
"""

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from research_gap_agent.config import load_settings
from research_gap_agent.sources import (
    ArxivSource,
    OpenAlexSource,
    PaperSource,
    SemanticScholarSource,
    dedup_papers,
)
from research_gap_agent.state import GraphState


logger = logging.getLogger(__name__)


def enabled_sources() -> list[PaperSource]:
    """Instantiate one source object per enabled API."""
    settings = load_settings()
    sources_cfg = settings.yaml.sources
    timeout = settings.yaml.pipeline.request_timeout_s

    sources: list[PaperSource] = []
    if sources_cfg.arxiv_enabled:
        sources.append(ArxivSource(timeout_s=timeout))
    if sources_cfg.openalex_enabled:
        sources.append(
            OpenAlexSource(timeout_s=timeout)
        )
    if sources_cfg.semantic_scholar_enabled:
        sources.append(
            SemanticScholarSource(
                timeout_s=timeout,
                api_key=settings.secrets.semantic_scholar_api_key,
            )
        )
    return sources


def search_node(state: GraphState) -> dict:
    """Fetch papers from every (source, query) pair and dedup the union."""
    settings = load_settings()
    per_query = settings.yaml.pipeline.papers_per_query_per_source
    max_workers = settings.yaml.pipeline.max_workers

    sources = enabled_sources()
    if not sources:
        logger.warning("No sources enabled - search returning empty result set.")
        return {"raw_papers": []}

    # Build the list of (source, query) jobs to run in parallel.
    jobs = []
    for source in sources:
        for query in state.queries:
            jobs.append((source, query))

    all_papers = []
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        future_to_job = {
            pool.submit(source.search, query.text, per_query): (source.name, query.text)
            for source, query in jobs
        }

        for future in as_completed(future_to_job):
            source_name, query_text = future_to_job[future]
            try:
                papers = future.result()
            except Exception as exc:
                # We log and continue: a single failing source should not
                # take down the whole search.
                logger.warning(
                    "Source %s failed on query %r: %s",
                    source_name,
                    query_text,
                    exc,
                )
                continue

            logger.info(
                "  %s <- %d papers for query %r",
                source_name,
                len(papers),
                query_text,
            )
            all_papers.extend(papers)

    deduped = dedup_papers(all_papers)
    logger.info(
        "search_node: %d papers fetched, %d unique after dedup.",
        len(all_papers),
        len(deduped),
    )
    return {"raw_papers": deduped}
