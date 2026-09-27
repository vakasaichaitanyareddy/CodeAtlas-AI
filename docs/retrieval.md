# Hybrid Retrieval & Reranking Architecture

## Overview
Code retrieval requires both exact keyword matching (for identifiers, method signatures, error constants) and semantic understanding (for conceptual or architectural queries). CodeAtlas uses a hybrid pipeline combining BM25 and dense vector search with Reciprocal Rank Fusion (RRF) and Cross-Encoder reranking.

---

## 1. Dual Retrieval Engines

### 1.1 Lexical Index (BM25)
- Uses `rank_bm25` with custom code-aware tokenization:
  - Splitting camelCase (`getUserById` -> `get`, `user`, `by`, `id`).
  - Splitting snake_case (`process_order_event` -> `process`, `order`, `event`).
  - Preserving raw compound symbols (`getUserById`, `process_order_event`).
  - Tokenizing language keywords and operator syntax.

### 1.2 Dense Vector Index (Qdrant)
- Embeddings generated via `EmbeddingProvider` (Google `text-embedding-004` or OpenAI `text-embedding-3-small`).
- Ingestion points are tagged with rich payloads:
  ```json
  {
    "repository_id": "uuid",
    "commit_sha": "git-sha",
    "file_path": "src/services/auth.py",
    "language": "python",
    "symbol_name": "AuthService.validate_token",
    "symbol_type": "METHOD",
    "start_line": 45,
    "end_line": 78,
    "content_hash": "sha256"
  }
  ```
- Queries enforce exact repository isolation using Qdrant filter clauses:
  ```json
  {
    "filter": {
      "must": [
        {"key": "repository_id", "match": {"value": "repo_id"}},
        {"key": "commit_sha", "match": {"value": "commit_sha"}}
      ]
    }
  }
  ```

---

## 2. Reciprocal Rank Fusion (RRF)
Given rankings from BM25 ($R_{BM25}$) and Vector Search ($R_{Vector}$), CodeAtlas fuses results using RRF with constant $k=60$:

$$RRF(d) = \sum_{m \in \{BM25, Vector\}} \frac{1}{k + r_m(d)}$$

Where $r_m(d)$ is the 1-based rank of chunk $d$ in system $m$.

---

## 3. Cross-Encoder Reranking
Top-50 fused candidates are fed into a cross-encoder model:
$$\text{Score} = \text{CrossEncoder}(\text{Query}, \text{ChunkContent})$$
The top-10 chunks by reranker score are passed to the context selection stage.
