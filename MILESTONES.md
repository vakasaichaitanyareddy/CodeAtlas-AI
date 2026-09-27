# CodeAtlas — Milestones & Engineering Progress Tracker

This document tracks the incremental implementation of CodeAtlas, milestone by milestone, enforcing that no milestone is considered complete without passing automated tests, static checks, and runtime verification.

---

## Milestone Status Overview

| Milestone | Title | Status | Tests | Notes |
|---|---|---|---|---|
| **M1** | Enterprise Foundation | **COMPLETED** | 28/28 Passed | Monorepo, FastAPI, 18 Postgres Models, Alembic, JWT/RBAC, AI Provider Abstractions, Next.js UI Shell, Docker, CI |
| **M2** | Repository Ingestion & Code Intelligence | **COMPLETED** | 36/36 Passed | Git operations, Python stdlib AST & JS/TS syntactic parsing, Symbol extraction, Dependency graph builder, Blast radius, Chunking |
| **M3** | Hybrid Retrieval Engine & Semantic Search | **COMPLETED** | 45/45 Passed | BM25 lexical index, CodeTokenizer, Qdrant vector index, RRF rank fusion (k=60), Cross-encoder reranker, /dashboard/search UI |
| **M4** | Grounded RAG & Codebase Chat Engine | **COMPLETED** | 63/63 Passed (0 skipped) | 5-point citation verification, GroundingStatus enum, hard insufficient evidence fallback, SSE streaming, multi-tenant security, Next.js Chat Console. Verified on real 8-container Docker runtime, Redis broker, Celery worker, Qdrant, and Postgres. |
| **M5** | Code Dependency Graph & Impact Analysis | **COMPLETED** | 72/72 Passed | Directed CPG synthesis, Tarjan's SCC cycle classification, normalized blast radius formula (0.0-1.0), neighborhood subgraphs, 5 REST endpoints, multi-tenant isolation, Next.js interactive console |
| **M6** | GitHub Intelligence & PR Review | QUEUED | - | Webhook verification, incremental diff parsing, automated PR risk review |
| **M7** | System Hardening & Observability | QUEUED | - | Version-aware caching, distributed rate limiting, Prometheus & Grafana |
| **M8** | Static Security Analysis | QUEUED | - | Multi-pattern vulnerability & secret scanning with masking |
| **M9** | Benchmark & Evaluation Framework | **COMPLETED** | 60-Query Suite | 60-query empirical evaluation dataset, Recall@K, MRR, NDCG, latency benchmarks across BM25, Dense, Hybrid, and Hybrid+Reranker |
| **M10** | Production Hardening & Deployment | QUEUED | - | Multi-stage Docker, health probes, zero-downtime migrations |
| **M11** | Recruiter Demo & Documentation Polish | QUEUED | - | Seeded demo repository, comprehensive documentation, architectural diagrams |

---

## Milestone 1 Verification Report
- [x] Monorepo structure fully scaffolded with `apps/`, `packages/`, `workers/`, `infrastructure/`, `docs/`, `tests/`.
- [x] FastAPI backend running with Pydantic v2 settings and RFC 7807 problem details error handling.
- [x] Async SQLAlchemy 2.0 with all 18 normalized database models mapped and verified.
- [x] Alembic initialized with migration files generated for clean database instantiation (`001_initial_schema.py` verified via offline SQL compilation).
- [x] Authentication system functional:
  - User registration (`POST /api/v1/auth/register`)
  - Login (`POST /api/v1/auth/login`) returning Access & Refresh JWTs
  - Token refresh (`POST /api/v1/auth/refresh`) with cryptographic rotation
  - User profile (`GET /api/v1/auth/me`)
  - Role-Based Access Control (`ADMIN` vs `USER` verified)
- [x] Provider abstractions implemented in `packages/ai`:
  - `LLMProvider` interface + Gemini & Mock implementations
  - `EmbeddingProvider` interface + Gemini & Mock implementations
  - `RerankerProvider` interface + CrossEncoder & Mock implementations
- [x] Next.js 14 frontend setup:
  - TypeScript, Tailwind CSS, dark developer aesthetic
  - Responsive App Router shell with main navigation items
  - Login & Register views with client API communication
  - Production build compiled successfully (`npm run build`)
- [x] Docker Compose orchestration configured (`docker-compose.yml`):
  - PostgreSQL 16, Redis 7, Qdrant, Prometheus, Grafana, API, Web, Worker
- [x] CI/CD pipeline defined in `.github/workflows/ci.yml`.
- [x] Automated tests passing.

---

## Milestone 2 Verification Report
- [x] Git service operations (`clone`, `pull`, `diff`, `commit_history`).
- [x] Multi-language parser (Python standard library `ast`, JavaScript/TypeScript syntactic scanning) with symbol extraction (functions, classes, methods, signatures, docstrings).
- [x] AST chunking preserving symbol integrity and hierarchy with line-precise coordinate metadata.
- [x] Dependency graph builder synthesizing callers, callees, and import relationships.
- [x] Blast radius calculation via graph traversal.
- [x] Repository scanner and Celery ingestion pipeline with database synchronization.

---

## Milestone 3 Verification Report
- [x] BM25 lexical search index with custom code tokenization (camelCase, snake_case splitting, syntax keywords).
- [x] Dense vector search in Qdrant with tenant/repository isolation filters.
- [x] Reciprocal Rank Fusion (RRF with $k=60$) combining lexical and dense retrieval signals.
- [x] Cross-Encoder reranker model reranking top-k candidate chunks.
- [x] Interactive Search Console UI at `/dashboard/search` with hybrid scoring filters and syntax highlighting.

---

## Milestone 4 Verification Report
- **Functional Implementation**: **PASS**
- **Automated Tests**: **PASS** (63 passed, 0 skipped, 0 failed in 24.86s)
- **Runtime Verification**: **PASS** (8 Docker containers running & healthy: PostgreSQL, Redis, Qdrant, API, Worker, Web, Prometheus, Grafana)
- **Celery Broker & Worker**: **PASS** (Real Redis broker dispatch, async container worker execution, Qdrant vector upsert, PostgreSQL persistence, failure resilience)
- **Frontend Verification**: **PASS** (TypeScript 0 errors, Next.js production build 18/18 static pages generated)
- **Final M4 Acceptance**: **MILESTONE 4 — VERIFIED / COMPLETE**

- [x] **5-Point Citation Verification Pipeline**:
  - File existence check against indexed repository commit.
  - Line boundary validation within physical file bounds ($1 \le start \le end \le total\_lines$).
  - Context overlap validation ensuring cited lines were supplied in the retrieval context pack.
  - AST symbol match validation ensuring claimed symbols match the code coordinate symbols.
  - Confidence score calculation in range $[0.0, 1.0]$.
- [x] **Explicit Grounding Status Categorization**:
  - `VERIFIED`: 100% valid citations, verified context evidence, confidence $\ge 0.70$.
  - `PARTIALLY_VERIFIED`: Mixed citation validity ($0 < valid\_ratio < 1.0$) or lower confidence.
  - `UNSUPPORTED`: Zero valid citations, insufficient context evidence, or fallback triggered.
- [x] **Controlled Hard Fallback**:
  - Deterministic fallback message *"I couldn't find enough evidence in the indexed repository to answer this reliably."*
  - LLM invocation is skipped completely when retrieval evidence falls below threshold ($0.35$).
- [x] **Evidence Lineage Preservation**:
  - End-to-end propagation: `QueryAnalysis` $\to$ `RetrievalResult` $\to$ `ContextPack` $\to$ `GenerationResult` $\to$ `CitationValidationResult` $\to$ `GroundedAnswer`.
- [x] **SSE Streaming & Multi-Tenant Security**:
  - Server-Sent Events streaming with `intent`, `context`, `token`, and `complete` lifecycle events.
  - Client disconnect safety with transaction rollbacks and session persistence.
  - Cross-tenant repository access barrier (HTTP 403 on foreign repository chat/sessions).
- [x] **Next.js 14 Interactive Chat Console**:
  - Real-time SSE streaming reader at `/dashboard/chat`.
  - Visual Grounding badge (`VERIFIED`, `PARTIALLY_VERIFIED`, `UNSUPPORTED`).
  - Slide-over Citation Drawer with line-precise code snippet highlighting.
  - Context Inspector drawer exposing retrieved chunks, RRF scores, and token budgeting.
  - Session history drawer with CRUD operations.
  - Production build compiled successfully (`npm run build`).

---

## Milestone 5 Verification Report
- **Functional Implementation**: **PASS**
- **Automated Tests**: **PASS** (72 passed, 0 skipped, 0 failed in 27.48s)
- **Unit Tests Added**: `tests/unit/test_graph_algorithms.py` (8 test functions covering SCC no-cycle, self-loop, import cycle, mixed cycle, traversals, normalized impact, Dijkstra path, and neighborhood extraction).
- **Integration Tests Added**: `tests/integration/test_graph_api.py` (complete end-to-end integration covering 5 REST endpoints, query filters, cycles, node inspector, multi-tenant 403 isolation, and commit scoping).
- **Runtime Verification**: **PASS** (8 Docker containers running & healthy: PostgreSQL, Redis, Qdrant, API, Worker, Web, Prometheus, Grafana; API `/repositories/{id}/graph` & `/cycles` live verified).
- **Frontend Verification**: **PASS** (TypeScript 0 errors, Next.js production build 18/18 static pages generated).
- **Final M5 Acceptance**: **MILESTONE 5 — VERIFIED / COMPLETE**

- [x] **Directed Code Property Graph Engine (`packages/graph`)**:
  - Node taxonomy: `FILE`, `MODULE`, `CLASS`, `FUNCTION`, `METHOD`, `ENDPOINT`, `MODEL`.
  - Edge taxonomy: `IMPORTS`, `CALLS`, `INHERITS`, `IMPLEMENTS`, `DEPENDS_ON`, `EXPOSES`, `QUERIES`.
  - Upstream reverse BFS and downstream forward BFS traversals.
- [x] **Tarjan's Strongly Connected Components (SCC) Cycle Engine**:
  - $O(V+E)$ strongly connected component cycle detection.
  - Cycle classification: `IMPORT_CYCLE`, `CALL_CYCLE`, `MIXED_CYCLE`.
  - Loop closure validation, cycle path tracing, and participating file attribution.
- [x] **Normalized Impact Score & Severity Mapping**:
  - Deterministic formula bounded in $[0.0, 1.0]$: $\text{score} = \min(1.0, 0.35 \times \text{endpoints} + 0.30 \times \text{files} + 0.20 \times \text{callers} + 0.15 \times \text{depth})$.
  - Severity mapping: `CRITICAL` ($\ge 0.75$ or $\ge 2$ endpoints), `HIGH` ($\ge 0.50$ or $\ge 1$ endpoint), `MEDIUM` ($\ge 0.25$), `LOW` ($< 0.25$).
  - Full factor breakdown dictionary (`score_breakdown`) and affected HTTP endpoint metadata.
- [x] **Bounded Neighborhood Extraction & Dijkstra Shortest Path**:
  - Depth-bounded neighborhood subgraphs ($d \le 2, N \le 500$).
  - Shortest directed call chain search with hop sequences and node detail.
- [x] **Production REST Endpoints (`apps/api`)**:
  - `GET /api/v1/repositories/{id}/graph` (with filters: `node_type`, `file_path`, `max_nodes`, `focus_symbol`, `commit_sha`).
  - `GET /api/v1/repositories/{id}/graph/cycles`.
  - `GET /api/v1/repositories/{id}/graph/nodes/{node_key}`.
  - `GET /api/v1/repositories/{id}/graph/impact`.
  - `GET /api/v1/repositories/{id}/graph/path`.
- [x] **Multi-Tenant Security & Tenant Isolation**:
  - Strict ownership checks: User B cross-tenant requests to all 5 graph routes return `HTTP 403 Forbidden`.
  - Scoped database queries by repository and commit SHA.
- [x] **Next.js 14 Interactive Dependency Console (`apps/web`)**:
  - Located at `/dashboard/graph`.
  - Tab 1: Blast Radius Impact Analysis with severity badges, factor breakdown, and affected endpoints.
  - Tab 2: Shortest Call Path finder with hop counts and step cards.
  - Tab 3: Graph Topology Matrix with node type pills, file search, and interactive Symbol Inspector panel (in/out degrees, caller/callee explorers).
  - Tab 4: Architectural Health & Cycles console detailing detected circular dependencies and affected files.

