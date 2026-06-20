"""
Graph analyzer node (owner: Caio).
"""

import logging

from research_gap_agent.schemas import GraphInsight
from research_gap_agent.state import GraphState

logger = logging.getLogger(__name__)


def _run_graph_analysis(texts: list[str]) -> GraphInsight:
    """Recebe textos dos papers e retorna um GraphInsight com hipóteses geradas."""
    from tqdm import tqdm

    from research_gap_agent.graph_analyzer.embeddings.embedding_model import (
        embed,
    )
    from research_gap_agent.graph_analyzer.extraction.concept_extractor import (
        extract_entities,
    )
    from research_gap_agent.graph_analyzer.extraction.relation_extractor import (
        extract_relations,
    )
    from research_gap_agent.graph_analyzer.filters.scientific_salience import (
        ScientificSalienceFilter,
    )
    from research_gap_agent.graph_analyzer.graph.community_detection import (
        detect_communities,
    )
    from research_gap_agent.graph_analyzer.graph.graph_builder import (
        build_graph,
    )
    from research_gap_agent.graph_analyzer.graph.link_prediction import (
        generate_multiconcept_hypotheses,
    )
    from research_gap_agent.graph_analyzer.graph_config import MIN_SIMILARITY
    from research_gap_agent.graph_analyzer.ranking.hypothesis_ranker import (
        compute_hypothesis_score,
        maximal_marginal_relevance_ranking,
    )
    from research_gap_agent.graph_analyzer.utils.idf import (
        compute_document_frequency,
    )

    # ── salience ──────────────────────────────────────────────────────────────
    papers_entities_raw = [
        [e["text"] for e in extract_entities(t)]
        for t in texts
    ]
    salience_filter = ScientificSalienceFilter()
    salience_filter.fit(papers_entities_raw)

    # ── extração de conceitos e relações ──────────────────────────────────────
    all_relations = []
    all_concepts = set()
    papers_entities = []
    future_work_sentences = []

    for text in tqdm(texts, desc="Scientific extraction"):
        entities = extract_entities(text, salience_filter)
        entity_texts = [e["text"] for e in entities]

        papers_entities.append(entity_texts)
        all_concepts.update(entity_texts)

        for sentence in text.split("."):
            s_lower = sentence.lower()
            if any(kw in s_lower for kw in (
                "future work", "future research", "future direction",
                "future study", "further research",
            )):
                future_work_sentences.append(sentence)

            all_relations.extend(extract_relations(sentence, entities))

    # ── embeddings ────────────────────────────────────────────────────────────
    all_concepts = list(all_concepts)
    embeddings = embed(all_concepts)
    embeddings_dict = dict(zip(all_concepts, embeddings))

    # ── grafo e comunidades ───────────────────────────────────────────────────
    G = build_graph(all_relations)
    communities = detect_communities(G)
    partition = {node: cid for cid, nodes in communities.items() for node in nodes}

    # ── hipóteses ─────────────────────────────────────────────────────────────
    df, total_docs = compute_document_frequency(papers_entities)
    candidates = generate_multiconcept_hypotheses(G, embeddings_dict, partition, MIN_SIMILARITY)

    hypotheses = []
    for h in tqdm(candidates, desc="Scoring hypotheses"):
        concepts_lower = [c.lower() for c in h["concepts"]]

        future_bonus = sum(
            sum(1 for c in concepts_lower if c in fw.lower())
            for fw in future_work_sentences
            if sum(1 for c in concepts_lower if c in fw.lower()) >= 2
        )

        base_score = compute_hypothesis_score(h, df, total_docs, G)
        h["future_bonus"] = future_bonus
        h["base_score"] = float(base_score)
        h["score"] = float(base_score + future_bonus * 0.015)
        hypotheses.append(h)

    ranked = maximal_marginal_relevance_ranking(hypotheses, lambda_diversity=0.75, top_k=20)

    # ── monta GraphInsight ────────────────────────────────────────────────────
    disconnected_pairs = [
        (link[0], link[1])
        for h in ranked
        for link in h.get("missing_links", [])
    ]

    summary_lines = [f"#{i+1} {h['concepts']} (score: {h['score']:.4f})" for i, h in enumerate(ranked[:5])]
    summary = f"{len(ranked)} hypotheses generated. Top 5:\n" + "\n".join(summary_lines)

    return GraphInsight(
        summary=summary,
        disconnected_pairs=disconnected_pairs,
        raw={
            "hypothesis_count": len(hypotheses),
            "concept_count": len(all_concepts),
            "relation_count": len(all_relations),
            "graph_nodes": G.number_of_nodes(),
            "graph_edges": G.number_of_edges(),
            "community_count": len(communities),
            "ranked_hypotheses": ranked,
        },
    )


def _graph_analysis_stub(reason: str, detail: str) -> GraphInsight:
    return GraphInsight(
        summary=reason,
        disconnected_pairs=[],
        raw={
            "stub": True,
            "reason": reason,
            "detail": detail,
        },
    )


def graph_analyzer_node(state: GraphState) -> dict:
    texts = [p.abstract for p in state.ranked_papers if p.abstract]

    if not texts:
        logger.warning("graph_analyzer_node: no papers found in state.")
        return {"graph_insight": GraphInsight(
            summary="No papers available for graph analysis.",
            disconnected_pairs=[],
            raw={"stub": True},
        )}

    logger.info("graph_analyzer_node: analyzing %d abstracts.", len(texts))
    try:
        insight = _run_graph_analysis(texts)
    except (ImportError, ModuleNotFoundError, OSError) as exc:
        logger.warning(
            "graph_analyzer_node: optional graph-analysis dependency is "
            "unavailable; skipping graph branch. %s",
            exc,
        )
        return {
            "graph_insight": _graph_analysis_stub(
                reason=(
                    "Graph analysis skipped because optional NLP "
                    "dependencies are unavailable."
                ),
                detail=str(exc),
            )
        }

    logger.info("graph_analyzer_node: done. %s", insight.summary.splitlines()[0])
    return {"graph_insight": insight}
