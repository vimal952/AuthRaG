# AuthRAG - Secure Document RAG Assistant

Access-controlled RAG system with role-based document permissions, conversation memory, and admin analytics.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI + Motor (async MongoDB) |
| Vector DB | ChromaDB (local persistent) |
| Embeddings | `paraphrase-multilingual-MiniLM-L12-v2` (sentence-transformers) |
| LLM | Google Gemini API (`gemini-2.5-flash`) |
| Database | MongoDB |
| Frontend | React + Vite |
| Deployment | Docker + Docker Compose |

## Roles & Access Control

| Role | Document Access | Features |
|------|----------------|---------|
| **Admin** | All documents | Chat, upload/delete docs, analytics dashboard, user management |
| **Employee** | `employee` + `all` docs | Chat only |
| **User** | `all` docs only | Chat only |

> The **first registered account** automatically becomes Admin. All subsequent registrations are Users.

Document chunks are stored in ChromaDB with `access_level` metadata (`admin` / `employee` / `all`). Queries are filtered at retrieval time based on the requesting user's role.

## Startup Behaviour

On boot the backend eagerly loads both heavy resources before accepting requests:

1. **Embedding model** — `paraphrase-multilingual-MiniLM-L12-v2` is loaded into memory.
2. **Vector store** — ChromaDB's HNSW index is read off disk and into memory.

You'll see these log lines in `docker compose logs -f backend`:

```
INFO: ⏳ Loading embedding model 'paraphrase-multilingual-MiniLM-L12-v2', please wait...
INFO: ✅ Embedding model ready.
INFO: ⏳ Vector store loading into memory, please wait...
INFO: ✅ Vector store ready — <N> document chunks loaded.
```

The server only starts accepting requests after both are ready.

## Running with Docker (Recommended)

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running
- A [Google Gemini API key](https://aistudio.google.com/app/apikey)

### 1. Configure environment

Add your API key to `backend/.env`:

```env
MONGO_URL=mongodb://localhost:27017
MONGO_DB=enterprise_copilot
JWT_SECRET=your-strong-secret-key
CHROMA_PATH=./chroma_db
GEMINI_API_KEY=your-gemini-api-key-here
GEMINI_MODEL=gemini-2.5-flash
```

### 2. Start all services

```bash
cd AuthRaG
docker compose up --build
```

First build takes several minutes (downloads Python packages and the embedding model ~120 MB).

### 3. Access the app

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| Backend API docs | http://localhost:8000/docs |

## Running Locally (Without Docker)

### Prerequisites

- Python 3.11+
- Node.js 18+
- MongoDB running on `localhost:27017`

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173).

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MONGO_URL` | `mongodb://localhost:27017` | MongoDB connection string |
| `MONGO_DB` | `enterprise_copilot` | Database name |
| `JWT_SECRET` | — | Secret for signing JWTs (change in production) |
| `JWT_EXPIRE_HOURS` | `24` | Token expiry |
| `GEMINI_API_KEY` | — | Google Gemini API key (required) |
| `GEMINI_MODEL` | `gemini-2.5-flash` | Gemini model to use |
| `CHROMA_PATH` | `./chroma_db` | ChromaDB persistence directory |
| `EMBEDDING_MODEL` | `paraphrase-multilingual-MiniLM-L12-v2` | Sentence-transformers model |
| `TOP_K_RESULTS` | `5` | Number of chunks retrieved per query |
| `MAX_CHUNK_SIZE` | `500` | Words per document chunk |
| `CHUNK_OVERLAP` | `50` | Overlap between consecutive chunks |

## API Endpoints

### Auth
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/auth/register` | Register (first account = admin) |
| POST | `/api/auth/login` | Login, returns JWT |
| GET | `/api/auth/me` | Current user info |

### Documents (admin only for write)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/documents/` | List accessible documents |
| POST | `/api/documents/upload` | Upload + index document |
| DELETE | `/api/documents/{id}` | Delete document + chunks |

### Chat
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/chat/query` | Send message, get RAG answer |
| GET | `/api/chat/conversations` | List user conversations |
| GET | `/api/chat/conversations/{id}` | Load conversation history |

### Admin
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/admin/users` | All users |
| PATCH | `/api/admin/users/{id}/role` | Promote/demote user |
| GET | `/api/admin/analytics` | Metrics dashboard data |
| GET | `/api/admin/audit-logs` | Paginated audit log |
| GET | `/api/admin/document-access/{doc_id}` | Who accessed a document |

## Audit Logging

Every action is recorded via `utils/audit.py`. Events:

- `register` / `login`
- `document_upload` / `document_delete`
- `chat_query` (includes sources accessed and latency)
- `role_change`

Admin analytics are computed by aggregating these logs — no separate metrics store needed.

## Supported Document Formats

- PDF (`.pdf`)
- Word documents (`.docx`)
- Plain text (`.txt`)

## Project Structure

```
AuthRaG/
├── docker-compose.yml
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py              # FastAPI app + lifespan (eager model/DB loading)
│   ├── config.py            # Pydantic settings (reads .env)
│   ├── database.py          # MongoDB connection (Motor)
│   ├── vector_store.py      # ChromaDB wrapper + startup loader
│   ├── utils/audit.py       # Central audit logger
│   ├── models/schemas.py    # Pydantic request/response models
│   ├── services/
│   │   ├── embedding.py     # Sentence-transformers model + chunking
│   │   ├── llm.py           # Gemini API client
│   │   └── rag.py           # RAG pipeline (retrieve + generate)
│   └── routes/
│       ├── auth.py          # Register, login, JWT
│       ├── documents.py     # Upload, list, delete
│       ├── chat.py          # Query + conversation history
│       └── admin.py         # Users, analytics, audit logs
└── frontend/
    ├── Dockerfile
    ├── nginx.conf
    └── src/
        ├── App.jsx
        ├── contexts/AuthContext.jsx
        ├── services/api.js
        └── pages/
            ├── LoginPage.jsx
            ├── ChatPage.jsx
            ├── DocumentsPage.jsx
            └── AdminPage.jsx
```

## Docker Troubleshooting

**Backend takes long to start:** Normal — the embedding model and vector index both load into memory at boot. Watch logs with `docker compose logs -f backend`.

**"403 Forbidden" from Gemini:** Your `GEMINI_API_KEY` is missing or invalid. Check `backend/.env` and ensure `env_file` is set in `docker-compose.yml`.

**"MongoDB connection refused":** The `mongodb` service may still be initialising. Docker Compose restarts the backend automatically via `restart: unless-stopped`.

**"Frontend can't reach backend":** Nginx proxies `/api/` to `http://backend:8000`. Ensure the backend container is healthy with `docker compose ps`.
