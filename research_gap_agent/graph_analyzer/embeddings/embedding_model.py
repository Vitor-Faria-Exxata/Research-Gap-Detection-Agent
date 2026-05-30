from sentence_transformers import SentenceTransformer

from research_gap_agent.graph_analyzer.graph_config import EMBEDDING_MODEL

model = SentenceTransformer(
    EMBEDDING_MODEL
)


def embed(texts):
    return model.encode(
        texts,
        normalize_embeddings=True,
        show_progress_bar=True
    )