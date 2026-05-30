import community as community_louvain


def detect_communities(G):

    partition = community_louvain.best_partition(
        G
    )

    communities = {}

    for node, cid in partition.items():

        communities.setdefault(
            cid,
            []
        ).append(node)

    return communities