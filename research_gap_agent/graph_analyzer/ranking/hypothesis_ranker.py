import math
import numpy as np

from itertools import combinations


def compute_pmi(
    freq_ab,
    freq_a,
    freq_b,
    total
):

    p_ab = freq_ab / total
    p_a = freq_a / total
    p_b = freq_b / total

    if p_ab == 0:
        return -999

    return np.log2(
        p_ab / (p_a * p_b)
    )


def tokenize_concept(text):

    return set(
        t
        for t in (
            text.lower()
            .replace("-", " ")
            .replace("/", " ")
            .split()
        )
        if len(t) > 2
    )


def jaccard_overlap(a, b):

    ta = tokenize_concept(a)
    tb = tokenize_concept(b)

    if not ta or not tb:
        return 0.0

    inter = len(ta & tb)
    union = len(ta | tb)

    return inter / union


def substring_overlap(a, b):

    a = a.lower()
    b = b.lower()

    return (
        a in b
        or b in a
    )


def shared_ngram_penalty(
    concepts,
    overlap_threshold=0.45
):

    penalty = 0.0

    for a, b in combinations(
        concepts,
        2
    ):

        if substring_overlap(a, b):

            penalty += 1.0
            continue

        overlap = jaccard_overlap(
            a,
            b
        )

        if overlap >= overlap_threshold:

            penalty += overlap

    return penalty


def concept_repetition_penalty(
    concepts,
    used_concepts
):

    penalty = 0.0

    for c in concepts:

        penalty += used_concepts.get(
            c,
            0
        )

    return penalty / len(concepts)


def score_hypothesis(
    semantic_similarity,
    graph_distance,
    rarity,
    centrality,
    topology_bonus,
    community_bonus,
    overlap_penalty
):

    return (
        0.40 * semantic_similarity +
        0.25 * rarity +
        0.15 * centrality +
        0.15 * topology_bonus +
        0.10 * community_bonus -
        0.20 * graph_distance -
        0.35 * overlap_penalty
    )


def maximal_marginal_relevance_ranking(
    hypotheses,
    lambda_diversity=0.7,
    top_k=20
):

    if len(hypotheses) == 0:
        return []

    hypotheses = sorted(
        hypotheses,
        key=lambda x: x["score"],
        reverse=True
    )

    selected = []

    used_concepts = {}

    while (
        len(selected) < top_k
        and len(hypotheses) > 0
    ):

        best_idx = None
        best_score = -999999

        for idx, h in enumerate(
            hypotheses
        ):

            concepts = h["concepts"]

            repetition_penalty = (
                concept_repetition_penalty(
                    concepts,
                    used_concepts
                )
            )

            overlap_penalty = (
                shared_ngram_penalty(
                    concepts
                )
            )

            diversified_score = (
                lambda_diversity
                * h["score"]
                -
                (1 - lambda_diversity)
                * repetition_penalty
                -
                0.25
                * overlap_penalty
            )

            if diversified_score > best_score:

                best_score = diversified_score
                best_idx = idx

        best = hypotheses.pop(
            best_idx
        )

        best["diversified_score"] = (
            float(best_score)
        )

        selected.append(best)

        for c in best["concepts"]:

            used_concepts[c] = (
                used_concepts.get(c, 0)
                + 1
            )

    for h in selected:

        concepts = h["concepts"]

        h["diversity_penalty"] = (
            concept_repetition_penalty(
                concepts,
                used_concepts
            )
        )

        h["ngram_penalty"] = (
            shared_ngram_penalty(
                concepts
            )
        )

    return selected


def compute_hypothesis_score(
    h,
    df,
    total_docs,
    G
):

    semantic_similarity = (
        h["avg_similarity"]
    )

    rarity = 0.0

    for c in h["concepts"]:

        rarity += math.log(
            total_docs
            /
            (
                1
                + df.get(c, 0)
            )
        )

    rarity /= len(h["concepts"])

    centrality = 0.0

    for c in h["concepts"]:

        centrality += G.degree(c)

    centrality /= len(h["concepts"])

    graph_distance = (
        6 - h["edge_count"]
    )

    topology_bonus = (
        h["edge_count"] / 6.0
    )

    community_bonus = (
        1.0
        if h.get(
            "cross_community",
            False
        )
        else 0.0
    )

    overlap_penalty = (
        shared_ngram_penalty(
            h["concepts"]
        )
    )

    final_score = score_hypothesis(
        semantic_similarity,
        graph_distance,
        rarity,
        centrality,
        topology_bonus,
        community_bonus,
        overlap_penalty
    )

    h["overlap_penalty"] = float(
        overlap_penalty
    )

    h["rarity"] = float(rarity)

    h["centrality"] = float(
        centrality
    )

    return float(final_score)