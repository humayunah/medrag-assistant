# MedRAG Assistant

**AI-powered medical document assistant with retrieval-augmented generation.**

Upload medical documents. Ask questions in plain English. Get citation-backed answers grounded in your data.

[Live Demo](#) &nbsp;&middot;&nbsp; [API Docs](#) &nbsp;&middot;&nbsp; [Architecture](#architecture)

---

## What It Does

MedRAG Assistant is a multi-tenant SaaS application for healthcare organizations. Staff upload medical documents (PDFs, scanned images), and the system processes them through a RAG pipeline to answer natural language queries with precise, citation-backed responses.

**Key capabilities:**

- **Document processing** &mdash; PDF extraction, OCR for scanned documents (Tesseract), section-aware chunking with medical header recognition
- **Hybrid search** &mdash; BM25 full-text + pgvector cosine similarity + Reciprocal Rank Fusion for superior medical retrieval
- **Citation-backed answers** &mdash; Every claim links to source document, page number, and section
- **Multi-provider LLM** &mdash; Gemini &rarr; Groq &rarr; HuggingFace &rarr; Claude failover with circuit breaker pattern
- **Multi-tenant RBAC** &mdash; Admin, Doctor, Nurse, Staff roles with PostgreSQL Row-Level Security
- **Real-time updates** &mdash; WebSocket-based document processing status
- **Demo mode** &mdash; Pre-loaded MTSamples dataset across 6 medical specialties for instant evaluation

## Architecture

```
                          Vercel (Free Tier)
  ┌──────────────────────────────────────────────────────┐
  │              React + Vite + TypeScript SPA            │
  │  Landing  |  Dashboard  |  Query UI  |  Admin Panel   │
  └─────────────────────────┬────────────────────────────┘
                            │ HTTPS + JWT
                            ▼
                        Render (Free Tier)
  ┌──────────────────────────────────────────────────────┐
  │                FastAPI + SQLAlchemy Async              │
  │                                                       │
  │  Auth ──── Documents ──── RAG Query ──── Admin        │
  │   │            │              │             │          │
  │   │     ┌──────┴──────┐   ┌──┴───┐    Audit Log      │
  │   │     │  Processor  │   │Search│                    │
  │   │     │ PDF→OCR→    │   │BM25 +│    Rate Limiter    │
  │   │     │ Chunk→Embed │   │Vector│                    │
  │   │     └──────┬──────┘   │+ RRF │    WebSocket Mgr   │
  │   │            │          └──┬───┘                    │
  │   │            ▼             ▼                        │
  │   │    ┌─────────────────────────┐                    │
  │   │    │     Provider Router     │                    │
  │   │    │  Gemini → Groq → HF →  │                    │
  │   │    │  Claude (circuit break) │                    │
  │   │    └─────────────────────────┘                    │
  └───┼──────────────┼──────────────────────────────────┘
      │              │
      ▼              ▼
  Supabase (Free Tier)              External APIs
  ┌──────────────────────┐    ┌──────────────────────┐
  │ Auth (JWT + RLS)     │    │ Gemini 2.0 Flash     │
  │ PostgreSQL + pgvector│    │ Groq (Llama 3.3 70B) │
  │ Storage (documents)  │    │ HuggingFace Inference│
  └──────────────────────┘    │ PubMedBERT embeddings│
                              └──────────────────────┘
```

### RAG Pipeline

```
Document Upload
    │
    ▼
┌─────────────┐     ┌──────────────┐     ┌───────────────┐
│ PDF Extract  │────▶│ Section-Aware │────▶│  PubMedBERT   │
│ + OCR (<50   │     │  Chunking     │     │  Embeddings   │
│  chars/page) │     │  512 tokens   │     │  768 dims     │
└─────────────┘     └──────────────┘     └───────┬───────┘
                                                  │
                    Query Time                    ▼
                        │               ┌─────────────────┐
                        ▼               │ pgvector HNSW   │
                 ┌─────────────┐        │ + tsvector BM25 │
                 │ Embed Query │───────▶│ + RRF Fusion    │
                 └─────────────┘        └────────┬────────┘
                                                 │ Top 8 chunks
                                                 ▼
                                        ┌─────────────────┐
                                        │  LLM Generation  │
                                        │  with citations  │
                                        └─────────────────┘
```

## Tech Stack

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| **Frontend** | React 19 + Vite 8 + TypeScript | Fast DX, SPA sufficient (no SSR needed) |
| **Styling** | TailwindCSS v4 | Utility-first, design token consistency |
| **State** | TanStack Query v5 | Server-state management, caching, optimistic updates |
| **Backend** | FastAPI + Python 3.13 | Async-first, auto-generated OpenAPI docs |
| **ORM** | SQLAlchemy 2.0 (async) | Full async support, Alembic migrations |
| **Database** | PostgreSQL + pgvector (Supabase) | Vector search + relational in one database |
| **Auth** | Supabase Auth | Free tier, JWT + RLS, email verification |
| **Embeddings** | NeuML/pubmedbert-base-embeddings | 95.62% on medical benchmarks (vs 93.46% MiniLM) |
| **LLM** | Multi-provider with circuit breaker | Zero-cost resilience across 4 providers |
| **OCR** | Tesseract via PyMuPDF | Handles scanned medical documents |
| **Deployment** | Render (backend) + Vercel (frontend) | True zero-cost free tiers |
| **CI/CD** | GitHub Actions | Lint, type check, build on every PR |

**Deliberate non-choices:**
- No LangChain/LlamaIndex &mdash; framework-free RAG for full control and debuggability
- No ChromaDB/Qdrant &mdash; pgvector consolidates infrastructure
- No Next.js &mdash; SPA is sufficient, simpler deployment

## Project Structure

```
medrag-assistant/
├── backend/
│   ├── app/
│   │   ├── api/v1/          # REST endpoints (auth, documents, queries, audit, demo, ws)
│   │   ├── core/            # Config, auth, database, exceptions, logging
│   │   ├── middleware/      # Correlation ID, logging, rate limiting, error handling
│   │   ├── models/          # SQLAlchemy models (tenant, user, document, chunk, conversation...)
│   │   ├── providers/       # LLM providers (Gemini, Groq, HuggingFace, Claude) + router
│   │   ├── schemas/         # Pydantic v2 request/response schemas
│   │   └── services/        # Business logic (RAG, chunking, embedding, processing, audit, WS)
│   ├── migrations/          # Alembic database migrations
│   ├── Dockerfile           # Production container (Python 3.13 + Tesseract)
│   └── main.py              # FastAPI application entry point (29 routes)
├── frontend/
│   ├── src/
│   │   ├── components/      # Layout, AuthProvider, ProtectedRoute, RoleGate, ColdStartGuard
│   │   ├── hooks/           # useAuth, useHealthCheck, useWebSocket
│   │   ├── pages/           # Landing, Dashboard, QueryChat, Demo, admin/*
│   │   ├── services/        # Axios API client, Supabase client
│   │   └── types/           # TypeScript interfaces
│   └── vercel.json          # SPA rewrite rules
├── scripts/
│   ├── seed_demo_data.py    # MTSamples dataset seeding (60 docs, 6 specialties)
│   └── keep_alive.py        # Supabase inactivity prevention
├── .github/workflows/
│   ├── ci.yml               # Backend lint + frontend type check + build
│   └── keep-alive.yml       # Cron ping every 5 days
└── docs/
    ├── brainstorms/         # Design exploration documents
    └── plans/               # Implementation plans
```

## Local Development

### Prerequisites

- Python 3.13+ with [uv](https://docs.astral.sh/uv/)
- Node.js 22+ with [pnpm](https://pnpm.io/)
- A [Supabase](https://supabase.com/) project (free tier)
- At least one LLM API key (Gemini recommended &mdash; free tier)

### Setup

```bash
# Clone
git clone https://github.com/YOUR_USERNAME/medrag-assistant.git
cd medrag-assistant

# Copy environment variables
cp .env.example .env
# Edit .env with your Supabase and LLM API keys

# Backend
cd backend
uv sync                          # Install Python dependencies
uv run alembic upgrade head      # Run database migrations
uv run uvicorn main:app --reload # Start dev server on :8000

# Frontend (new terminal)
cd frontend
pnpm install                     # Install Node dependencies
pnpm dev                         # Start dev server on :5173
```

### Seed Demo Data

```bash
# From repo root — downloads MTSamples CSV and seeds 60 documents
cd backend
uv run python ../scripts/seed_demo_data.py

# To clear and re-seed
uv run python ../scripts/seed_demo_data.py --clear
```

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | Yes | PostgreSQL connection string (asyncpg) |
| `DATABASE_POOL_URL` | No | Supabase connection pooler URL |
| `SUPABASE_URL` | Yes | Supabase project URL |
| `SUPABASE_ANON_KEY` | Yes | Supabase anonymous key |
| `SUPABASE_SERVICE_KEY` | Yes | Supabase service role key |
| `SUPABASE_JWT_SECRET` | Yes | JWT secret for token verification |
| `GEMINI_API_KEY` | Recommended | Google Gemini API key (free tier) |
| `GROQ_API_KEY` | Optional | Groq API key (free tier) |
| `HF_API_TOKEN` | Optional | HuggingFace API token (free tier) |
| `ANTHROPIC_API_KEY` | Optional | Anthropic API key (paid) |
| `ENVIRONMENT` | No | `development` or `production` (default: development) |
| `CORS_ORIGINS` | No | Comma-separated allowed origins |
| `VITE_API_URL` | Yes | Backend URL for frontend |
| `VITE_SUPABASE_URL` | Yes | Supabase URL for frontend |
| `VITE_SUPABASE_ANON_KEY` | Yes | Supabase anon key for frontend |

## API Reference

The API is documented via FastAPI's auto-generated OpenAPI spec, available at `/docs` (Swagger UI) and `/redoc` (ReDoc) when the backend is running.

**Key endpoints:**

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health/live` | Liveness check |
| `GET` | `/health/ready` | Readiness check (DB + LLM) |
| `POST` | `/api/v1/auth/signup` | Create account |
| `POST` | `/api/v1/auth/signin` | Sign in |
| `POST` | `/api/v1/documents/upload` | Upload document (PDF/image) |
| `GET` | `/api/v1/documents` | List documents (paginated, filterable) |
| `POST` | `/api/v1/queries` | RAG query with citations |
| `GET` | `/api/v1/conversations` | List conversations |
| `GET` | `/api/v1/audit-logs` | Audit trail (admin only) |
| `POST` | `/api/v1/demo/session` | Create demo session (rate-limited) |
| `WS` | `/ws/processing` | Real-time processing updates |

## Design

The frontend follows a **Clinical Editorial** aesthetic:

- **Typography:** DM Serif Display (headings) + IBM Plex Sans (body) + IBM Plex Mono (code)
- **Palette:** Slate `#0f172a` (primary), Amber `#d97706` (accent), Cream `#faf7f2` (background)
- **Components:** Card-based layouts, subtle shadows, staggered fade-in animations

Pages include a marketing landing page, document dashboard with drag-and-drop upload, three-panel query interface (conversations / chat / citations), and a full admin panel (users, audit log, settings).

## Security & Compliance Notes

This is a portfolio demonstration project, not HIPAA-certified software. However, it implements several security-conscious patterns:

- **Tenant isolation** &mdash; PostgreSQL RLS enforces data boundaries at the database level
- **JWT authentication** &mdash; Supabase Auth with short-lived tokens
- **RBAC** &mdash; Permission-based access control (admin, doctor, nurse, staff)
- **Audit logging** &mdash; Append-only trail of all data access events
- **Rate limiting** &mdash; Per-tenant and per-IP rate limits on all endpoints
- **Input validation** &mdash; Pydantic v2 schemas, file type validation, size limits
- **Prompt injection defense** &mdash; System prompt isolation, input sanitization
- **No PHI in logs** &mdash; Structured logging with sensitive field masking
- **Error handling** &mdash; No stack traces in API responses, correlation IDs for debugging

## Deployment

### Backend (Render)

1. Create a new Web Service on [Render](https://render.com)
2. Connect your GitHub repo, set root directory to `backend`
3. Build command: `pip install uv && uv sync --frozen --no-dev`
4. Start command: `uv run uvicorn main:app --host 0.0.0.0 --port $PORT --workers 1`
5. Set environment variables from `.env.example`
6. Health check path: `/health/live`

### Frontend (Vercel)

1. Import your GitHub repo on [Vercel](https://vercel.com)
2. Set root directory to `frontend`
3. Framework preset: Vite
4. Set environment variables: `VITE_API_URL`, `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`

### Supabase

1. Create a project at [supabase.com](https://supabase.com)
2. Enable the `vector` extension: `CREATE EXTENSION IF NOT EXISTS vector;`
3. Run migrations: `uv run alembic upgrade head`
4. Configure Auth settings (enable email verification)

## License

MIT
