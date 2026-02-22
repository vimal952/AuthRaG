import logging
import chromadb
from chromadb.config import Settings as ChromaSettings
from config import settings

logger = logging.getLogger(__name__)

chroma_client: chromadb.Client = None
collection = None


def init_vector_store():
    global chroma_client, collection
    logger.info("⏳ Vector store loading into memory, please wait...")
    chroma_client = chromadb.PersistentClient(
        path=settings.CHROMA_PATH,
        settings=ChromaSettings(anonymized_telemetry=False),
    )
    collection = chroma_client.get_or_create_collection(
        name="enterprise_docs",
        metadata={"hnsw:space": "cosine"},
    )
    # Force the HNSW index off disk and into memory now, not on the first query
    doc_count = collection.count()
    logger.info("✅ Vector store ready — %d document chunks loaded.", doc_count)


def get_collection():
    return collection


def get_access_filter(role: str) -> dict | None:
    if role == "admin":
        return None
    if role == "employee":
        return {"access_level": {"$in": ["employee", "all"]}}
    return {"access_level": {"$eq": "all"}}


def add_chunks(chunks: list[dict]):
    if not chunks:
        return
    collection.add(
        ids=[c["id"] for c in chunks],
        embeddings=[c["embedding"] for c in chunks],
        documents=[c["text"] for c in chunks],
        metadatas=[c["metadata"] for c in chunks],
    )


def query_chunks(embedding: list[float], role: str, n_results: int = 5) -> list[dict]:
    where = get_access_filter(role)

    total = collection.count()
    if total == 0:
        return []

    try:
        kwargs = {"query_embeddings": [embedding], "n_results": min(n_results, total)}
        if where:
            kwargs["where"] = where
        results = collection.query(**kwargs)
    except Exception:
        return []

    docs = []
    for i, doc in enumerate(results["documents"][0]):
        docs.append({
            "text": doc,
            "metadata": results["metadatas"][0][i],
            "distance": results["distances"][0][i],
        })
    return docs


def delete_document_chunks(document_id: str):
    results = collection.get(where={"document_id": {"$eq": document_id}})
    if results["ids"]:
        collection.delete(ids=results["ids"])
