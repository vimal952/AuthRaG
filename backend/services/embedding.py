import logging
from sentence_transformers import SentenceTransformer
from config import settings

logger = logging.getLogger(__name__)

_model: SentenceTransformer = None


def init_embedding_model():
    global _model
    logger.info("⏳ Loading embedding model '%s', please wait...", settings.EMBEDDING_MODEL)
    _model = SentenceTransformer(settings.EMBEDDING_MODEL)
    logger.info("✅ Embedding model ready.")


def get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer(settings.EMBEDDING_MODEL)
    return _model


def embed_texts(texts: list[str]) -> list[list[float]]:
    model = get_model()
    embeddings = model.encode(texts, convert_to_numpy=True, normalize_embeddings=True)
    return embeddings.tolist()


def embed_query(text: str) -> list[float]:
    return embed_texts([text])[0]


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    words = text.split()
    chunks = []
    start = 0
    while start < len(words):
        end = start + chunk_size
        chunk = " ".join(words[start:end])
        chunks.append(chunk)
        start += chunk_size - overlap
    return chunks
