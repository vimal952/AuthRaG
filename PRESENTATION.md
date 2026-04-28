# AuthRAG — Presentation

## What We Built

An **enterprise-grade AI assistant** that lets employees ask questions about company documents and get accurate, sourced answers — with strict role-based access control so people only see what they're allowed to see.

---

## The Problem We're Solving

Companies store critical knowledge in PDFs, Word documents, and reports that are hard to search. Employees waste time digging through files, and sensitive documents (HR policies, financial data) can end up exposed to the wrong people.

**AuthRAG** fixes both problems:
- Ask a question in plain English, get an answer with sources
- Every answer is filtered by what your role is allowed to read

---

## How It Works (RAG Pipeline)

```
User asks a question
        ↓
Question is converted to a vector embedding
        ↓
ChromaDB finds the most relevant document chunks
(filtered by the user's role — admin / employee / user)
        ↓
Those chunks + the question are sent to Gemini
        ↓
Gemini generates an answer grounded in those chunks
        ↓
Answer + source document names returned to the user
```

This is called **Retrieval-Augmented Generation (RAG)** — the LLM never guesses, it only answers from documents you've uploaded.

---

## Role-Based Access Control

| Role | What They Can See | What They Can Do |
|------|------------------|-----------------|
| **Admin** | Every document | Chat, upload/delete docs, view analytics, manage users |
| **Employee** | Employee-level + public docs | Chat only |
| **User** | Public docs only | Chat only |

- The **first person to register** becomes Admin automatically
- Access is enforced at the **vector search level** — restricted chunks are never even retrieved for unauthorised users

---

## Tech Stack

| What | Technology | Why |
|------|-----------|-----|
| Backend API | FastAPI (Python) | Async, fast, auto-generates API docs |
| LLM | Google Gemini 2.5 Flash | Fast, high quality, no GPU needed |
| Embeddings | paraphrase-multilingual-MiniLM-L12-v2 | Multilingual, runs locally, free |
| Vector DB | ChromaDB | Lightweight, persistent, runs in-process |
| Database | MongoDB | Flexible schema for docs, users, audit logs |
| Frontend | React + Vite | Fast dev experience, modern UI |
| Deployment | Docker + Docker Compose | One command to run everything |

---

## Key Technical Decisions

**Why Gemini instead of a local LLM?**
Running Ollama inside Docker has no GPU access on Mac/Windows, making inference extremely slow (60+ seconds per query). Gemini gives fast, high-quality answers over the API with no hardware requirements.

**Why eager model loading?**
Both the embedding model and the ChromaDB HNSW index are loaded into memory when the app starts — not on the first request. This means the first user query is just as fast as every other one.

**Why ChromaDB over Pinecone/Weaviate?**
No external service to manage. ChromaDB runs inside the backend container, persists to a Docker volume, and requires zero configuration. For an enterprise demo, simplicity beats scalability.

---

## What Happens When You Upload a Document

1. File is received (PDF / DOCX / TXT)
2. Text is extracted and split into overlapping chunks (500 words, 50 word overlap)
3. Each chunk is embedded using the local sentence-transformers model
4. Chunks + embeddings + metadata (document ID, title, access level) are stored in ChromaDB
5. Document record saved to MongoDB

---

## Admin Dashboard Features

- **Analytics** — total queries, active users, average response latency, most-accessed documents
- **User management** — promote/demote users between roles
- **Audit log** — every login, upload, delete, query, and role change is logged with timestamp and user

---

## Deployment

Single command to start the entire stack:

```bash
docker compose up --build
```

This starts:
- MongoDB (document + user store)
- ChromaDB (vector store)
- FastAPI backend (API + RAG pipeline)
- React frontend served via Nginx

Frontend → `http://localhost:3000`
API docs → `http://localhost:8000/docs`

---

## Challenges We Solved

| Challenge | Solution |
|-----------|----------|
| passlib incompatible with bcrypt 4.x | Pinned `bcrypt==4.0.1` |
| Ollama timing out inside Docker (no GPU) | Switched to Gemini API |
| ChromaDB telemetry crash (`capture()` error) | Upgraded ChromaDB to `0.5.23` |
| First query slow due to lazy model loading | Eager load both embedding model and HNSW index at startup |
| `.env` not read inside Docker containers | Added `env_file` directive in `docker-compose.yml` |

---

## Future Scope

- Support for more document types (Excel, PowerPoint, images via OCR)
- Streaming responses for a better chat experience
- SSO integration (Google Workspace / Azure AD)
- Per-document expiry and automatic re-indexing
- Semantic caching to reduce redundant Gemini API calls
