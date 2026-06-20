"""Convert ranked papers and initialize the minimum structured contract."""

import logging
from research_gap_agent.arxiv import FullTextCache
from research_gap_agent.config import load_settings
from research_gap_agent.schemas import Paper
from research_gap_agent.state import GraphState
from research_gap_agent.document_converters import (
    JinaConverter,
    PyMuPDFConverter,
    MarkerGPUConverter,
    ArxivHtmlFallbackConverter,
    DocumentConverter,
)

logger = logging.getLogger(__name__)


def get_converter(name: str) -> DocumentConverter:
    try:
        if name == "jina":
            api_key = '' #TODO ADD KEY GETTER
            return JinaConverter(api_key=api_key)
        elif name == "pymupdf":
            return PyMuPDFConverter()
        elif name == "marker":
            return MarkerGPUConverter()
        else:
            raise ValueError(f"Unknown document converter provider: {name}")
    except ImportError as e:
        logger.error(f"Failed to load optional dependency for {name}: {e}")
        raise


def paper_extractor_node(state: GraphState) -> dict:
    settings = load_settings()
    provider = settings.yaml.document_converter.provider_name
    use_html_fallback = settings.yaml.document_converter.use_arxiv_html

    converter = get_converter(provider)
    cache = FullTextCache()
    extracted_results = {}
    papers = state.ranked_papers
    n_cache_hits = 0

    for paper in papers:
        if not paper.arxiv_id:
            continue
        cached = cache.get(paper.arxiv_id)
        if cached is not None:
            extracted_results[paper.id] = cached
            n_cache_hits += 1
    if n_cache_hits:
        logger.info("Full-text cache: %d / %d papers served from disk.",
                    n_cache_hits, len(papers))

    if use_html_fallback:
        uncached = [p for p in papers if p.id not in extracted_results and p.arxiv_id]
        if uncached:
            logger.info("Attempting arXiv HTML fallback for %d papers...", len(uncached))
            try:
                html_converter = ArxivHtmlFallbackConverter()
                n_html_ok = 0
                for paper in uncached:
                    try:
                        md = html_converter.convert(paper.arxiv_id)
                        extracted_results[paper.id] = md
                        cache.put(paper.arxiv_id, md)
                        n_html_ok += 1
                    except Exception as e:
                        logger.debug("HTML fallback failed for %s: %s", paper.arxiv_id, e)
                logger.info("Successfully fetched HTML for %d / %d papers.", n_html_ok, len(uncached))
            except ImportError as e:
                 logger.warning(e)

    papers_for_primary = [p for p in papers if p.id not in extracted_results]

    if papers_for_primary:
        sources = [p.pdf_url for p in papers_for_primary]
        logger.info(
            "Sending remaining %d papers to primary converter (%s)...",
            len(sources), provider
        )

        primary_md_results = converter.convert_batch(sources)

        for paper, md_text in zip(papers_for_primary, primary_md_results):
            extracted_results[paper.id] = md_text
            if paper.arxiv_id and md_text:
                cache.put(paper.arxiv_id, md_text)

    extracted_documents = []
    extracted = []
    for paper in papers:
        markdown = extracted_results.get(paper.id)
        if isinstance(markdown, str) and markdown:
            extracted_documents.append(
                paper.model_copy(update={"full_text": markdown})
            )
            extracted.append(
                ExtractedInsights(
                    paper_id=paper.id,
                    title=paper.title,
                    published_date=paper.published_date,
                )
            )

    logger.info(
        "paper_extractor_node: converted %d documents and initialized the "
        "minimum structured insight contract.",
        len(extracted_documents),
    )
<<<<<<< HEAD
    
    return {
        "extracted_documents": extracted_documents,
        "extracted": extracted,
    }
=======

    return {"extracted": extracted}
>>>>>>> origin/main
