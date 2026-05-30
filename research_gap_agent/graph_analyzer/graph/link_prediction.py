from itertools import combinations

from tqdm import tqdm

from research_gap_agent.graph_analyzer.graph_config import MAX_NEIGHBORS_PER_HUB

MAX_COMBO_EDGES = 6


def make_similarity_fn(embeddings_dict):
    cache = {}

    def similarity(a, b):
        key = (a, b) if a < b else (b, a)
        if key not in cache:
            cache[key] = float(
                embeddings_dict[a] @ embeddings_dict[b]
            )
        return cache[key]

    return similarity


def average_similarity(nodes, sim_fn):
    sims = [
        sim_fn(a, b)
        for a, b in combinations(nodes, 2)
    ]
    return sum(sims) / len(sims) if sims else 0.0


def generate_multiconcept_hypotheses(
    G,
    embeddings_dict,
    partition,
    min_similarity
):
    valid_nodes = {
        n for n in G.nodes()
        if n in embeddings_dict and n in partition
    }
    subG = G.subgraph(valid_nodes)
    adj = subG.adj

    sim_fn = make_similarity_fn(embeddings_dict)

    hypotheses = []
    visited = set()

    for center in tqdm(subG.nodes()):
        neighbors = set(adj[center])
        for n in list(adj[center]):
            neighbors.update(adj[n])
        neighbors.discard(center)

        if len(neighbors) > MAX_NEIGHBORS_PER_HUB:
            center_emb = embeddings_dict[center]
            neighbors = set(sorted(
                neighbors,
                key=lambda n: sim_fn(center, n),
                reverse=True
            )[:MAX_NEIGHBORS_PER_HUB])

        if len(neighbors) < 3:
            continue

        for trio in combinations(neighbors, 3):
            combo = tuple(sorted([center] + list(trio)))

            if combo in visited:
                continue
            visited.add(combo)

            edge_count = subG.subgraph(combo).number_of_edges()

            if edge_count < 4 or edge_count >= MAX_COMBO_EDGES:
                continue

            avg_sim = average_similarity(combo, sim_fn)
            if avg_sim < min_similarity:
                continue

            missing_links = [
                (a, b)
                for a, b in combinations(combo, 2)
                if b not in adj[a]
            ]

            cross_community = len({partition[c] for c in combo}) > 1

            hypotheses.append({
                "concepts": combo,
                "missing_links": missing_links,
                "avg_similarity": avg_sim,
                "cross_community": cross_community,
                "edge_count": edge_count,
            })

    return hypotheses