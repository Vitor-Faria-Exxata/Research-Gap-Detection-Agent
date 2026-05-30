import math
from collections import Counter

from research_gap_agent.graph_analyzer.filters.rhetorical_noise import (
    RHETORICAL_PHRASES,
    BAD_PREFIXES,
    BAD_SUFFIXES,
    GENERIC_SINGLE_WORDS
)


class ScientificSalienceFilter:

    def __init__(self):
        self.document_frequency = Counter()
        self.total_documents = 0

    def fit(self, papers_entities):
        self.total_documents = len(papers_entities)

        for entities in papers_entities:
            unique_entities = set(entities)
            for e in unique_entities:
                self.document_frequency[e] += 1

    def compute_idf(self, concept):
        df = self.document_frequency.get(concept, 1)
        return math.log(self.total_documents / (1 + df))

    def is_rhetorical(self, concept):
        c = concept.lower().strip()

        if c in RHETORICAL_PHRASES:
            return True
        if c in GENERIC_SINGLE_WORDS:
            return True
        if c.startswith(BAD_PREFIXES):
            return True
        if c.endswith(BAD_SUFFIXES):
            return True

        return False

    def is_low_information(self, concept):
        c = concept.lower()

        if len(c) < 4:
            return True
        if len(c.split()) > 8:
            return True

        tokens = c.split()
        if len(set(tokens)) / len(tokens) < 0.5:
            return True

        return False

    def passes_idf(self, concept, min_idf=None):
        if min_idf is None:
            # Com poucos documentos o IDF máximo possível é log(N/2),
            # então o limiar escala proporcionalmente.
            max_possible_idf = (
                math.log(self.total_documents / 2)
                if self.total_documents > 2
                else 0.5
            )
            min_idf = min(1.2, max_possible_idf * 0.6)

        return self.compute_idf(concept) >= min_idf

    def is_scientifically_salient(self, concept):
        if self.is_rhetorical(concept):
            return False
        if self.is_low_information(concept):
            return False
        if not self.passes_idf(concept):
            return False

        return True