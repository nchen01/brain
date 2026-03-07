# Brain

Integrated monorepo combining **brain-mvp** (document ingestion + RAG pipeline) and **QueryReactor** (LangGraph-based QA pipeline).

## Repository Structure

```
brain/
├── brain-mvp/        # Document processing, chunking, embedding storage
└── query-reactor/    # LangGraph QA pipeline, M0–M12 modules, API
```

---

## brain-mvp

A production-ready document processing system that extracts text from PDF documents and prepares it for high-precision RAG (Retrieval-Augmented Generation).

**Key capabilities:**
- Multi-library PDF extraction: MinerU (primary), PyMuPDF, pdfplumber, pdfminer fallbacks
- Hybrid structure-aware chunking with summarization-enriched context
- Semantic search via `POST /api/v1/chunks/search`
- Web UI at port 8088 with Upload, Search, and Ask tabs
- SQLite (dev) and PostgreSQL (prod) storage

See [`brain-mvp/README.md`](brain-mvp/README.md) and [`brain-mvp/PROJECT_EXPLANATION.md`](brain-mvp/PROJECT_EXPLANATION.md) for full details.

---

## QueryReactor

A production-ready, modular smart QA system that routes user questions across multiple retrieval paths, aggregates evidence with provenance, and generates verifiable answers.

**Key capabilities:**
- LangGraph M0–M12 pipeline for deep multi-hop reasoning
- `POST /api/ask-direct` — fast direct RAG (brain-mvp search + single GPT call, ~2s)
- `POST /api/qa` — full M0–M12 pipeline with verification (~2min)
- brain-mvp integration: `BrainMVPRetriever` wires M3 (P1) and M6 (P3) to brain-mvp's chunk store
- Configurable via `config.md` and environment variables

See [`query-reactor/README.md`](query-reactor/README.md) and [`query-reactor/PROJECT.md`](query-reactor/PROJECT.md) for full details.

---

## How They Connect

```
User → POST /api/ask-direct or /api/qa  (QueryReactor :8000)
              ↓
    BrainMVPRetriever
              ↓
    POST /api/v1/chunks/search  (brain-mvp :8088)
              ↓
    brain-mvp SQLite chunk store
```

**Quick start:**
1. Start brain-mvp: `docker compose up` in `brain-mvp/`
2. Upload a PDF via `http://localhost:8088`
3. Start QueryReactor: `python main.py server` in `query-reactor/`
4. Ask a question via the Ask tab in the brain-mvp UI or directly at `http://localhost:8000/api/ask-direct`
