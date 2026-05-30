from collections import defaultdict
import math


def compute_document_frequency(
    papers_entities
):
    df = defaultdict(int)

    total_docs = len(papers_entities)

    for entities in papers_entities:

        unique = set(entities)

        for e in unique:
            df[e] += 1

    return df, total_docs


def compute_idf(
    concept,
    df,
    total_docs
):
    freq = df.get(concept, 1)

    return math.log(
        total_docs / (1 + freq)
    )