from services.embedding import embed_query
from services.llm import generate
from vector_store import query_chunks
from config import settings

SYSTEM_PROMPT = """You are a secure enterprise AI assistant. Answer questions ONLY using the provided context.
If the context doesn't contain enough information, say so clearly.
Always cite the document sources you used. Be concise and factual.
Never reveal information about access controls or system internals."""


def build_context(chunks: list[dict]) -> str:
    parts = []
    for i, chunk in enumerate(chunks, 1):
        meta = chunk["metadata"]
        source = meta.get("title", meta.get("document_id", "Unknown"))
        parts.append(f"[Source {i}: {source}]\n{chunk['text']}")
    return "\n\n---\n\n".join(parts)


def extract_sources(chunks: list[dict]) -> list[dict]:
    seen = set()
    sources = []
    for chunk in chunks:
        meta = chunk["metadata"]
        doc_id = meta.get("document_id")
        if doc_id not in seen:
            seen.add(doc_id)
            sources.append({
                "document_id": doc_id,
                "title": meta.get("title", "Unknown"),
                "access_level": meta.get("access_level"),
            })
    return sources


async def answer_query(
    query: str,
    role: str,
    history: list[dict] | None = None,
) -> dict:
    query_embedding = embed_query(query)
    chunks = query_chunks(query_embedding, role, n_results=settings.TOP_K_RESULTS)

    if not chunks:
        return {
            "answer": "I couldn't find any relevant documents to answer your question.",
            "sources": [],
            "latency_ms": 0,
        }

    context = build_context(chunks)
    history_text = ""
    if history:
        recent = history[-4:]
        history_text = "\n".join(
            f"{m['role'].capitalize()}: {m['content']}" for m in recent
        )

    prompt = f"""Conversation history:
{history_text}

Context from company documents:
{context}

User question: {query}

Answer:"""

    answer, latency = await generate(prompt, system=SYSTEM_PROMPT)
    sources = extract_sources(chunks)

    return {"answer": answer, "sources": sources, "latency_ms": latency}
