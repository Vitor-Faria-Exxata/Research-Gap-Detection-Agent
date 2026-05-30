import logging
from datetime import date

from research_gap_agent.nodes.graph_analyzer import graph_analyzer_node
from research_gap_agent.schemas import Paper
from research_gap_agent.state import GraphState

logging.basicConfig(level=logging.INFO)

MOCK_PAPERS = [
    Paper(
        id="paper_001",
        source="openalex",
        title="Federated Learning for Medical Imaging",
        abstract=(
            "Federated learning enables training across decentralized medical imaging datasets "
            "without sharing raw patient data, addressing data privacy and data silos. "
            "Personalized federated learning adapts global models to local distributions. "
            "Future work should explore privacy-preserving AI techniques for radiology and pathology."
        ),
        authors=["Author A"],
        published_date=date(2023, 1, 1),
        url="https://example.com/paper_001",
        pdf_url="https://example.com/paper_001.pdf",
    ),
    Paper(
        id="paper_002",
        source="openalex",
        title="Vision Transformers for Medical Image Segmentation",
        abstract=(
            "Transformer-based architectures have shown strong performance on medical image segmentation. "
            "Vision transformers applied to MRI and CT scans outperform CNN baselines on benchmark datasets. "
            "Further research on multimodal fusion of radiology reports and imaging data is warranted."
        ),
        authors=["Author B"],
        published_date=date(2023, 2, 1),
        url="https://example.com/paper_002",
        pdf_url="https://example.com/paper_002.pdf",
    ),
    Paper(
        id="paper_003",
        source="openalex",
        title="Diffusion Models for Medical Image Synthesis",
        abstract=(
            "Diffusion models have emerged as a powerful generative framework for medical image synthesis. "
            "Privacy-preserving synthetic data generation addresses data regulation constraints. "
            "Federated learning combined with diffusion-based augmentation is an underexplored direction."
        ),
        authors=["Author C"],
        published_date=date(2023, 3, 1),
        url="https://example.com/paper_003",
        pdf_url="https://example.com/paper_003.pdf",
    ),
    Paper(
        id="paper_004",
        source="openalex",
        title="Graph Neural Networks for Anatomical Structure Modeling",
        abstract=(
            "Graph neural networks model relationships between anatomical structures in medical imaging. "
            "Link prediction between federated optimization and calibration methods remains unexplored. "
            "Embedding-based similarity between clinical concepts enables automated gap identification."
        ),
        authors=["Author D"],
        published_date=date(2023, 4, 1),
        url="https://example.com/paper_004",
        pdf_url="https://example.com/paper_004.pdf",
    ),
    Paper(
        id="paper_005",
        source="openalex",
        title="Contrastive Learning for Histopathology Classification",
        abstract=(
            "Contrastive learning improves representation quality for histopathology image classification. "
            "Multi-institutional federated benchmarks are scarce in the oncology imaging literature. "
            "We plan to investigate federated contrastive learning for cross-institutional pathology."
        ),
        authors=["Author E"],
        published_date=date(2023, 5, 1),
        url="https://example.com/paper_005",
        pdf_url="https://example.com/paper_005.pdf",
    ),
]


# ── Helpers de validação ──────────────────────────────────────────────────────

def _check_graph_insight(insight) -> list[str]:
    issues = []

    if not insight.summary:
        issues.append("summary está vazio")

    if not isinstance(insight.disconnected_pairs, list):
        issues.append("disconnected_pairs não é lista")

    if not isinstance(insight.raw, dict):
        issues.append("raw não é dict")

    missing = {
        "hypothesis_count", "concept_count", "relation_count",
        "graph_nodes", "graph_edges", "community_count",
    } - insight.raw.keys()
    if missing:
        issues.append(f"raw faltando chaves: {missing}")

    if insight.raw.get("hypothesis_count", 0) == 0:
        issues.append("nenhuma hipótese gerada — verifique MIN_SIMILARITY ou densidade do grafo")

    if insight.raw.get("graph_edges", 0) == 0:
        issues.append("grafo sem arestas — extração de relações pode estar falhando")

    return issues


# ── Teste principal ───────────────────────────────────────────────────────────

def run_graph_analyzer_test():
    state = GraphState(
        initial_topic="federated learning medical imaging",
        ranked_papers=MOCK_PAPERS,
    )

    print("\n" + "=" * 60)
    print("GRAPH ANALYZER NODE — INTEGRATION TEST")
    print("=" * 60)
    print(f"Papers no estado: {len(state.ranked_papers)}")

    result = graph_analyzer_node(state)

    assert "graph_insight" in result, "Retorno não contém 'graph_insight'"
    insight = result["graph_insight"]

    print("\n-- GraphInsight retornado --")
    print(f"Summary:\n{insight.summary}")
    print(f"\nDisconnected pairs ({len(insight.disconnected_pairs)}):")
    for pair in insight.disconnected_pairs[:10]:
        print(f"  {pair}")

    print("\n-- Métricas internas (raw) --")
    for k, v in insight.raw.items():
        if k != "ranked_hypotheses":
            print(f"  {k}: {v}")

    ranked = insight.raw.get("ranked_hypotheses", [])
    if ranked:
        print("\n-- Top 3 hipóteses --")
        for i, h in enumerate(ranked[:3], 1):
            print(f"  #{i} concepts={h['concepts']}  score={h['score']:.4f}")

    print("\n-- Validação --")
    issues = _check_graph_insight(insight)
    if issues:
        for issue in issues:
            print(f"  [WARN] {issue}")
    else:
        print("  OK — nenhum problema encontrado")

    print("\n" + "=" * 60)


# ── Teste com estado vazio ────────────────────────────────────────────────────

def run_empty_state_test():
    state = GraphState(
        initial_topic="federated learning medical imaging",
        ranked_papers=[],
    )

    print("\n" + "=" * 60)
    print("GRAPH ANALYZER NODE — EMPTY STATE TEST")
    print("=" * 60)

    result = graph_analyzer_node(state)
    insight = result["graph_insight"]

    assert insight.raw.get("stub") is True, "Estado vazio deveria retornar stub"
    print("  OK — retornou placeholder corretamente para estado vazio")
    print("=" * 60)
    
    
# Adicione essa função no teste e chame antes do run_graph_analyzer_test()

def run_debug_test():
    from research_gap_agent.graph_analyzer.extraction.concept_extractor import extract_entities
    from research_gap_agent.graph_analyzer.extraction.relation_extractor import extract_relations
    from research_gap_agent.graph_analyzer.filters.scientific_salience import ScientificSalienceFilter

    texts = [p.abstract for p in MOCK_PAPERS]

    print("\n" + "=" * 60)
    print("DEBUG — EXTRAÇÃO DE ENTIDADES")
    print("=" * 60)

    # ── salience sem filtro ainda ─────────────────────────────────────────────
    papers_entities_raw = [
        [e["text"] for e in extract_entities(t)]
        for t in texts
    ]
    print(f"Entidades raw por paper:")
    for i, ents in enumerate(papers_entities_raw):
        print(f"  paper_{i+1:03d}: {len(ents)} entidades → {ents[:5]}")

    # ── salience fitado ───────────────────────────────────────────────────────
    salience_filter = ScientificSalienceFilter()
    salience_filter.fit(papers_entities_raw)

    print(f"\nEntidades após salience_filter:")
    for i, text in enumerate(texts):
        ents = extract_entities(text, salience_filter)
        print(f"  paper_{i+1:03d}: {len(ents)} entidades → {[e['text'] for e in ents[:5]]}")

    # ── relações ──────────────────────────────────────────────────────────────
    print(f"\nRelações extraídas (primeiras 10):")
    count = 0
    for text in texts:
        entities = extract_entities(text, salience_filter)
        for sentence in text.split("."):
            rels = extract_relations(sentence, entities)
            for r in rels:
                print(f"  {r}")
                count += 1
                if count >= 10:
                    break
        if count >= 10:
            break

    if count == 0:
        print("  Nenhuma relação extraída — verifique relation_extractor.py")

    print("=" * 60)


if __name__ == "__main__":
    run_debug_test()
    run_graph_analyzer_test()
    run_empty_state_test()
