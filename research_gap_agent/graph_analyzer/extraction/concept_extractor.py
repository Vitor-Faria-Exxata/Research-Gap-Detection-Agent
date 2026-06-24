import spacy

from research_gap_agent.graph_analyzer.utils.text_utils import normalize
from research_gap_agent.graph_analyzer.extraction.role_classifier import classify_entity

nlp = spacy.load("en_core_web_trf")

STOPWORD_CONCEPTS = {
    "approach",
    "method",
    "model",
    "system",
    "framework",
    "technique",
    "result",
    "study",
    "work",
    "paper",
    "analysis",
    "use",
    "task",
    "performance",
    "experiment",
    "evaluation",
    "setting",
    "baseline",
}


def _is_valid_concept(concept: str) -> bool:
    if len(concept) < 4:
        return False

    alpha_chars = sum(1 for c in concept if c.isalpha())
    if alpha_chars < 3:
        return False

    concept_lower = concept.lower()

    if concept_lower in STOPWORD_CONCEPTS:
        return False

    tokens = concept_lower.split()

    if len(tokens) == 1 and tokens[0] in STOPWORD_CONCEPTS:
        return False

    return True


def _make_entity(concept: str, source: str) -> dict:
    entity_type = classify_entity(concept) or "SCIENTIFIC_CONCEPT"

    return {
        "text": concept,
        "type": entity_type,
        "source": source,
    }


def extract_entities(text: str, salience_filter=None) -> list[dict]:
    doc = nlp(text)

    source_priority = {
        "ner": 0,
        "noun_chunk": 1,
    }

    candidates: dict[str, dict] = {}

    def _try_add(concept: str, source: str):
        if not concept:
            return

        if not _is_valid_concept(concept):
            return

        if salience_filter:
            if not salience_filter.is_scientifically_salient(concept):
                return

        existing = candidates.get(concept)

        if (
            existing is None
            or source_priority[source]
            < source_priority[existing["source"]]
        ):
            candidates[concept] = _make_entity(concept, source)

    for ent in doc.ents:
        concept = normalize(ent.text)
        _try_add(concept, "ner")

    for chunk in doc.noun_chunks:
        concept = normalize(chunk.text)
        _try_add(concept, "noun_chunk")

    return list(candidates.values())