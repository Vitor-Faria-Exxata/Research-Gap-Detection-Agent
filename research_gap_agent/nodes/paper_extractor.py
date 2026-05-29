"""
Paper extractor node (owner: Vinicius).
"""

import logging
from research_gap_agent.config import load_settings
from research_gap_agent.schemas import ExtractedInsights, Paper
from research_gap_agent.state import GraphState
from research_gap_agent.document_converters import (
    JinaConverter,
    PyMuPDFConverter,
    MarkerGPUConverter,
    ArxivHtmlFallbackConverter,
    DocumentConverter,
)
import concurrent

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
    extracted_results = {}
    papers = state.ranked_papers

    # Try fetching papers in HTML form from arxiv
    if use_html_fallback:
        logger.info("Attempting arXiv HTML fallback for %d papers...", len(papers))
        try:
            html_converter = ArxivHtmlFallbackConverter()
            
            def try_html(paper: Paper):
                try:
                    md = html_converter.convert(paper.arxiv_id) 
                    return paper.id, md
                except Exception as e:
                    logger.debug("HTML fallback failed for %s: %s", paper.arxiv_id, e)
                    return paper.id, None

            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                for paper_id, md_text in executor.map(try_html, papers):
                    if md_text:
                        extracted_results[paper_id] = md_text
            logger.info("Successfully fetched HTML for %d papers.", len(extracted_results))
        except ImportError as e:
             logger.warning(e)

    # Route remaining papers to conversion pipelines
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

    extracted = []
    for paper in papers:
        if paper.id in extracted_results:
            extracted.append(
                paper.model_copy(update={'full_text': extracted_results[paper.id]})
            )

    logger.info(
        "paper_extractor_node: successfully extracted markdown for %d papers.",
        len(extracted),
    )
    
    return {"extracted": extracted}
