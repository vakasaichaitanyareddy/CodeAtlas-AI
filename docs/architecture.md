# CodeAtlas System Architecture

```
                                      +---------------------------------------------+
                                      |                Web Client                   |
                                      |    (Next.js 14, React, Monaco, React Flow)  |
                                      +----------------------+----------------------+
                                                             | HTTP / SSE / WS
                                                             v
+-------------------------------------------------------------------------------------------------------------------+
|                                                 FastAPI Gateway                                                   |
|                                                                                                                   |
|  +---------------------+  +---------------------+  +---------------------+  +----------------------------------+  |
|  | Auth & Multi-tenant |  | Query Router & RAG  |  | Graph & Impact API  |  | Ingestion, PR & Security Manager |  |
|  +----------+----------+  +----------+----------+  +----------+----------+  +----------------+-----------------+  |
+-------------|------------------------|------------------------|--------------------------|------------------------+
              |                        |                        |                          |
              |                        |                        |                          v
              |                        |                        |                +-------------------+
              |                        |                        |                | Redis Task Queue  |
              |                        |                        |                +---------+---------+
              |                        |                        |                          |
              |                        v                        v                          v
              |             +---------------------+  +---------------------+     +-------------------+
              |             | BM25 Lexical Search |  | Code Graph Engine   |     |  Celery Workers   |
              |             |  (Inverted Index)   |  | (DFS/BFS Traversals)|     | (Clone, AST, Embed|
              |             +----------+----------+  +----------+----------+     |  Security, Scan)  |
              |                        |                        |                +---------+---------+
              |                        v                        v                          |
              |             +---------------------+  +---------------------+               |
              |             | Qdrant Vector Store |  | PostgreSQL 16 (Rel) | <-------------+
              |             | (Dense Embeddings)  |  | (18 Tabular Models) |
              |             +----------+----------+  +----------+----------+
              |                        |                        |
              v                        v                        v
+-------------------------------------------------------------------------------------------------------------------+
|                                            packages/ai Abstraction                                                |
|                                                                                                                   |
|        [LLMProvider]                        [EmbeddingProvider]                      [RerankerProvider]           |
|   Gemini / OpenAI / Mock                 Gemini / OpenAI / Mock                 CrossEncoder / Cohere / Mock      |
+-------------------------------------------------------------------------------------------------------------------+
```

## 1. Monolith & Worker Topology
CodeAtlas avoids microservice sprawl by structuring core execution into:
- **`apps/api` (Web & API Core)**: Stateless async FastAPI process handling authentication, routing, retrieval orchestration, graph querying, and SSE streaming.
- **`workers` (Asynchronous Task Processors)**: Celery workers dedicated to IO- and CPU-intensive operations: Git cloning, language parsing via Python AST & JS/TS scanners, symbol extraction, AST chunking, vector embedding generation, Qdrant index synchronization, and security AST scanning.
- **`packages/*` (Shared Engine Libraries)**: Pure, reusable Python libraries (`parser`, `retrieval`, `graph`, `ai`, `shared`) decoupled from web frameworks for independent unit testing.

## 2. Ingestion & Version Lifecycle
1. **Validation & Clone**: Validates GitHub URL and git reference. Shallow/sparse clones repository into worker temporary workspace.
2. **Language & File Classification**: Detects file types, filters out lockfiles, minified bundles, vendor directories (`node_modules`, `venv`), and binary assets.
3. **AST Symbol Extraction**: Dispatches source files to language parsers (`PythonParser`, `JavaScriptParser`, `TypeScriptParser`) to generate normalized `File`, `Symbol`, `Import`, and `Call` entities.
4. **Hierarchical Code Chunking**: Deconstructs classes and functions into AST chunks with line numbers, parent symbols, dependencies, and content hashes.
5. **Delta & Hash Comparison**: Compares chunk hashes against the prior indexed commit. Only modified and newly created chunks trigger vector embeddings.
6. **Dual Indexing**:
   - Dense representations pushed to Qdrant collection with payload filters (`repository_id`, `commit_sha`).
   - Tokenized text indexed in BM25 index.
7. **Graph Synthesis**: Resolves local and cross-file imports/calls to persist nodes and directed edges in PostgreSQL.
8. **Automated Security Scan**: Scans AST chunks and raw source for secrets and vulnerable coding patterns.

## 3. Grounded Hybrid RAG Pipeline
1. **Query Normalization & Intent Routing**: Classifies queries into categories (`FACTUAL_CODE_QUERY`, `ARCHITECTURE_QUERY`, `DEPENDENCY_QUERY`, `IMPACT_QUERY`, etc.).
2. **Parallel Hybrid Retrieval**:
   - BM25 returns top-K lexical matches.
   - Vector retriever queries Qdrant with dense embeddings.
3. **Reciprocal Rank Fusion (RRF)**: Combines ranked lists into a normalized relevance score.
4. **Cross-Encoder Reranking**: Re-scores top candidates using a cross-encoder model to capture fine-grained semantic alignment.
5. **Graph Context Enrichment**: For architectural or dependency queries, traverses upstream and downstream callers/dependencies to inject contextual structural facts.
6. **Token-Budgeted Context Selection**: Deduplicates overlapping AST ranges, orders by priority, and ensures prompt size stays within LLM token budget.
7. **Grounded Generation & Citation Validation**: Directs LLM with strict instructions to distinguish evidence from assumptions. Validates that every citation matches a verified repository file and line range before emission.
