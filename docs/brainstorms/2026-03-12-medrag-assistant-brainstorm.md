---
date: 2026-03-12
topic: medrag-assistant
---

# MedRAG Assistant — AI Medical Document Assistant

## What We're Building

A production-grade, multi-tenant AI Medical Document Assistant that lets healthcare organizations upload medical documents (PDFs, scanned images) and query them using natural language. The system uses Retrieval-Augmented Generation (RAG) to return accurate, citation-backed answers grounded in the uploaded documents — not hallucinated responses.

This is a portfolio project targeting Upwork's highest-growth vertical intersection: **AI + Health Tech**. RAG is the #1 in-demand AI skill in 2026, and medical VA demand is up 44%. The project must impress clinic CTOs, health tech startup founders, and enterprise engineering teams equally.

## Why This Project

- **RAG is the #1 most in-demand AI engineering skill on Upwork in 2026**
- **Medical VAs growing at 44%** — health tech is the strongest hiring vertical
- **Multi-provider LLM architecture** demonstrates senior-level abstraction thinking
- **HIPAA-aware multi-tenancy** signals real domain expertise, not tutorial-level work
- **Zero-cost stack** proves you can build production systems without burning money

## Target Audience

All health tech client types on Upwork:
- Clinic/hospital CTOs hiring for internal tools
- Health tech startup founders building products
- Enterprise health tech companies scaling teams

## Architecture Decisions

### Tech Stack

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| **Frontend** | React (TypeScript) | Industry standard, polished UI capability, broad Upwork demand |
| **Backend** | Python FastAPI | Native AI/ML ecosystem (LangChain, sentence-transformers), production health tech standard |
| **Database** | PostgreSQL + pgvector (Supabase) | Combines relational + vector search in one DB, production-standard, free tier with pgvector enabled |
| **OCR** | Tesseract (open-source) | Free, battle-tested, handles scanned medical documents |
| **PDF Processing** | PyMuPDF / pdfplumber | Free, reliable PDF text extraction |
| **Embeddings** | sentence-transformers (all-MiniLM-L6-v2) or Hugging Face API | Free, runs locally or via free API |
| **Auth** | Custom JWT + RBAC | Multi-tenant role-based access (Admin, Doctor, Nurse, Staff) |

### LLM Provider Strategy — Multi-Provider (Abstracted)

| Provider | Tier | Role |
|----------|------|------|
| Google Gemini | Free (15 RPM) | Default provider |
| Groq | Free tier | Fast inference alternative |
| HuggingFace Inference API | Free tier | Fallback / community models |
| Claude API | User-provided key | Optional premium provider |

The LLM layer is abstracted behind a provider interface. Users configure their preferred provider via environment variables. Default is free-tier Gemini. This architecture demonstrates:
- Strategy pattern / dependency inversion
- Provider-agnostic design
- Graceful fallback chains

### Document Handling

| Format | Method |
|--------|--------|
| PDF (text-based) | PyMuPDF / pdfplumber direct text extraction |
| PDF (scanned) | Tesseract OCR pipeline |
| Images (JPG, PNG, TIFF) | Tesseract OCR pipeline |

### Authentication & Access Control

**Multi-tenant RBAC** with organization isolation:

| Role | Permissions |
|------|------------|
| Admin | Manage org, users, all documents, view audit logs |
| Doctor | Upload, query, view all org documents |
| Nurse | Upload, query assigned documents |
| Staff | Query only, no upload |

Each organization (tenant) is fully isolated — users in Org A cannot see or query documents belonging to Org B. This demonstrates HIPAA-aware data segregation.

### Hosting & Deployment (Zero Cost)

| Service | Platform | Free Tier |
|---------|----------|-----------|
| Frontend | Vercel | Unlimited for personal projects |
| Backend API | Render | Free web service (spins down on idle) |
| Database (Postgres + pgvector) | Supabase | 500MB database, pgvector enabled |
| File Storage | Supabase Storage | 1GB free |

### RAG Pipeline Architecture

```
Document Upload → Text Extraction (PDF/OCR) → Chunking → Embedding → Store in pgvector
                                                                           ↓
User Query → Embed Query → Similarity Search (pgvector) → Top-K Chunks → LLM Prompt → Citation-Backed Answer
```

Key RAG decisions:
- **Chunking strategy:** Recursive character splitting with overlap (512 tokens, 50 token overlap)
- **Retrieval:** Cosine similarity search via pgvector, top-5 chunks
- **Prompt engineering:** System prompt enforces citation format — every claim links back to source document + page
- **No hallucination guardrail:** If retrieved chunks don't contain the answer, the system says "I don't have enough information in the uploaded documents to answer this"

## Key Decisions

- **Multi-provider over single provider:** Demonstrates architectural maturity and avoids vendor lock-in. Most impressive to enterprise clients.
- **pgvector over dedicated vector DB:** Consolidates infrastructure, reduces complexity, production-standard. One fewer service to manage on free tier.
- **FastAPI over Node.js:** Python dominates AI/ML tooling. "Python + AI" Upwork searches vastly outnumber "Node + AI."
- **Render over Railway:** True zero-cost free tier (Railway's $5 credit can deplete). Render signals "production workloads" vs Railway's "prototypes" association.
- **OCR support:** Real clinics deal with scanned documents constantly. This signals domain understanding beyond tutorial-level RAG demos.
- **Multi-tenant over single-tenant:** Separates portfolio projects from production products. Health tech clients immediately recognize this as SaaS-ready architecture.

## Production-Grade Requirements (Non-Negotiable)

This is NOT an MVP. Every aspect must demonstrate senior-level engineering:

- [ ] **Structured logging** — JSON logs with request IDs, correlation across services
- [ ] **Error handling** — Graceful degradation, user-friendly error messages, no raw stack traces
- [ ] **Input validation** — Pydantic models for all API inputs, file type/size validation
- [ ] **Rate limiting** — Per-tenant API rate limiting
- [ ] **Audit trail** — Every document access and query logged with user, timestamp, action
- [ ] **Health checks** — `/health` endpoint with DB connectivity check
- [ ] **API documentation** — Auto-generated OpenAPI/Swagger docs via FastAPI
- [ ] **Environment configuration** — All secrets via env vars, no hardcoded values
- [ ] **Database migrations** — Alembic for schema versioning
- [ ] **CORS configuration** — Properly scoped, not wildcard
- [ ] **File upload security** — Virus scanning awareness, file type validation, size limits
- [ ] **Query result caching** — Avoid redundant LLM calls for identical queries
- [ ] **Responsive UI** — Mobile-friendly dashboard
- [ ] **Loading states & error boundaries** — No blank screens or hanging spinners
- [ ] **Accessibility** — WCAG 2.1 AA compliance on key flows

## Resolved Questions

### 1. Real-Time Processing Status → WebSockets
WebSocket connection for live document processing updates ("Extracting text...", "Running OCR...", "Generating embeddings...", "Done"). Demonstrates real-time architecture skills — significantly more impressive than polling to enterprise clients.

### 2. Pre-Loaded Sample Data → Yes, Real Dataset
Use the **MTSamples dataset** (5,026 medical transcription reports across 40 specialties) from [Kaggle](https://www.kaggle.com/datasets/tboyle10/medicaltranscriptions), licensed CC0 Public Domain. This includes:
- Discharge summaries
- Operative reports
- SOAP notes
- Progress notes
- Consultation notes

Pre-process a curated subset (~50-100 documents across 5-6 specialties) into the system so clients can immediately try queries like:
- "What were the findings in the cardiology reports?"
- "Summarize the discharge instructions for patient cases involving diabetes"
- "What medications were prescribed in the orthopedic consultation notes?"

Source: [MTSamples.com](https://www.mtsamples.com/) — original source, [Kaggle dataset](https://www.kaggle.com/datasets/tboyle10/medicaltranscriptions) — CC0 download.

### 3. Landing Page → Full Marketing Site + App
Both a polished landing page (explaining the product, features, tech stack, demo CTA) AND the full application behind login. The landing page itself is a portfolio piece — health tech startup founders evaluate design taste before they even log in.

## Frontend Design

Use the `/frontend-design` skill for all frontend implementation. The UI must be distinctive, production-grade, and avoid generic AI aesthetics. Key surfaces:
- **Landing page** — marketing site with feature highlights, tech stack showcase, live demo CTA
- **Dashboard** — document management, upload status, org overview
- **Query interface** — chat-like RAG query UI with citation panels
- **Admin panel** — user management, audit logs, org settings
- **Document viewer** — PDF/image preview with highlighted citation passages

## Next Steps

→ `/ce:plan` for detailed implementation plan with file-by-file breakdown
