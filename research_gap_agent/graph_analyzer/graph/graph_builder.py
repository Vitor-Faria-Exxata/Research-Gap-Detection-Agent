import networkx as nx

from research_gap_agent.graph_analyzer.graph_config import MAX_HUB_DEGREE


def build_graph(relations):

    G = nx.Graph()

    for r in relations:

        a = r["source"]
        b = r["target"]

        if a == b:
            continue

        if G.has_edge(a, b):

            G[a][b]["weight"] += 1

        else:

            G.add_edge(
                a,
                b,
                weight=1,
                relation=r["relation"]
            )

    #
    # Hubs: prune arestas de menor peso, preservando o nó
    #

    for node in list(G.nodes()):

        if G.degree(node) <= MAX_HUB_DEGREE:
            continue

        edges = sorted(
            G.edges(node, data=True),
            key=lambda e: e[2]["weight"],
            reverse=True
        )

        to_remove = [
            (u, v)
            for u, v, _ in edges[MAX_HUB_DEGREE:]
        ]

        G.remove_edges_from(to_remove)

    return G