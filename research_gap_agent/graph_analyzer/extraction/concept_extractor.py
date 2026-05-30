import spacy

from research_gap_agent.graph_analyzer.utils.text_utils import normalize
from research_gap_agent.graph_analyzer.extraction.role_classifier import classify_entity

nlp = spacy.load("en_core_sci_md")

# Sufixos e prefixos comuns em jargão científico/técnico de nicho.
# Cobre termos novos sem precisar listá-los explicitamente.
SCIENTIFIC_SUFFIXES = (
    "tion", "ment", "ance", "ence", "ity", "ism", "ogy", "ics",
    "sis", "ase", "ome", "ine", "oid", "oma", "ria", "net",
    "former", "fusion", "head", "wise", "based", "driven", "aware",
)

SCIENTIFIC_PREFIXES = (
    "multi", "semi", "self", "cross", "bio", "neuro", "cardio",
    "onco", "radio", "patho", "hetero", "homo", "pseudo", "meta",
    "hyper", "auto", "contra", "retro", "poly",
)

# Tokens explícitos de alta relevância para domínios de ML/saúde.
# Mantidos como âncora para termos que não caem em sufixo/prefixo.
SCIENTIFIC_ANCHOR_TOKENS = {
    "learning", "network", "transformer", "segmentation", "detection",
    "classification", "privacy", "federated", "multimodal", "diffusion",
    "vision", "medical", "imaging", "healthcare", "optimization",
    "domain", "adaptation", "calibration", "pathology", "radiology",
    "language", "foundation", "diagnostic", "benchmark", "inference",
    "attention", "embedding", "dataset", "annotation", "augmentation",
    "cnn", "bert", "gan", "vit", "llm", "mri", "ct", "ehr",
}

# Palavras que contaminam noun chunks mas não têm valor semântico sozinhas.
STOPWORD_CONCEPTS = {
    "approach", "method", "model", "system", "framework", "technique",
    "result", "study", "work", "paper", "analysis", "use", "task",
    "performance", "experiment", "evaluation", "setting", "baseline",
}


def contains_scientific_signal(text: str) -> bool:
    text_lower = text.lower()
    words = text_lower.split()

    # Rejeita se for composto só por stopwords conceituais
    if all(w in STOPWORD_CONCEPTS for w in words):
        return False

    # Âncoras explícitas
    if any(token in text_lower for token in SCIENTIFIC_ANCHOR_TOKENS):
        return True

    # Sufixos/prefixos científicos em qualquer palavra do chunk
    for word in words:
        if len(word) < 5:
            continue
        if any(word.endswith(s) for s in SCIENTIFIC_SUFFIXES):
            return True
        if any(word.startswith(p) for p in SCIENTIFIC_PREFIXES):
            return True

    return False


def _is_valid_concept(concept: str) -> bool:
    """Filtros básicos de qualidade antes de qualquer classificação."""
    if len(concept) < 4:
        return False
    # Rejeita tokens puramente numéricos ou com maioria de dígitos
    alnum = [c for c in concept if c.isalpha()]
    if len(alnum) < 3:
        return False
    # Rejeita conceitos de uma única palavra que são stopwords conceituais
    if concept.lower() in STOPWORD_CONCEPTS:
        return False
    return True


def _make_entity(concept: str, source: str) -> dict:
    entity_type = classify_entity(concept) or "SCIENTIFIC_CONCEPT"
    return {"text": concept, "type": entity_type, "source": source}


def extract_entities(text: str, salience_filter=None) -> list[dict]:
    doc = nlp(text)

    # Guarda source por conceito: NER tem prioridade sobre noun_chunk
    source_priority = {"ner": 0, "noun_chunk": 1}
    candidates: dict[str, dict] = {}

    def _try_add(concept: str, source: str):
        if not _is_valid_concept(concept):
            return
        if salience_filter and not salience_filter.is_scientifically_salient(concept):
            return
        existing = candidates.get(concept)
        if existing is None or source_priority[source] < source_priority[existing["source"]]:
            candidates[concept] = _make_entity(concept, source)

    # ── NER (alta confiança) ──────────────────────────────────────────────────
    for ent in doc.ents:
        _try_add(normalize(ent.text), "ner")

    # ── Noun chunks (média confiança) ─────────────────────────────────────────
    for chunk in doc.noun_chunks:
        concept = normalize(chunk.text)
        if contains_scientific_signal(concept):
            _try_add(concept, "noun_chunk")

    return list(candidates.values())