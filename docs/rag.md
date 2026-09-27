# Grounded Repository RAG Pipeline & Chat Engine

## Overview
CodeAtlas implements a multi-stage, grounded Retrieval-Augmented Generation (RAG) pipeline designed specifically for codebases. It prevents hallucinations by relying on verified AST evidence, strict token budgeting, 5-point citation verification, and explicit grounding status scoring.

```
                    +-----------------------------+
                    |         User Query          |
                    +--------------+--------------+
                                   |
                                   v
                    +-----------------------------+
                    |    Query Classification     |
                    | (Factual, Arch, Dep, etc.)  |
                    +--------------+--------------+
                                   |
                                   v
                    +-----------------------------+
                    |  Query Entity / Symbol Ext  |
                    +--------------+--------------+
                                   |
            +----------------------+----------------------+
            |                                             |
            v                                             v
+-----------------------+                     +-----------------------+
|  BM25 Lexical Search  |                     |  Dense Vector Search  |
|   (Exact token/sym)   |                     |   (Qdrant Similarity) |
+-----------+-----------+                     +-----------+-----------+
            |                                             |
            +----------------------+----------------------+
                                   |
                                   v
                    +-----------------------------+
                    | Reciprocal Rank Fusion(RRF) |
                    +--------------+--------------+
                                   |
                                   v
                    +-----------------------------+
                    |    Cross-Encoder Rerank     |
                    +--------------+--------------+
                                   |
                                   v
                    +-----------------------------+
                    |   Evidence Threshold Gate   |
                    |  (min_relevance_score check)|
                    +--------------+--------------+
                       /                        \
           [Sufficient Evidence]        [Insufficient Evidence]
                     /                            \
                    v                              v
+-------------------------------+   +------------------------------------+
|  Context Assembler & Pruning  |   | Hard Controlled Fallback           |
|  (Line Dedup, 4k Token Cap,   |   | "I couldn't find enough evidence   |
|   AST Symbol & Graph Enrich)  |   | in the indexed repository to       |
+---------------+---------------+   | answer this reliably."             |
                |                   +------------------------------------+
                v
+-------------------------------+
|     Grounded LLM Prompting    |
|   (SSE Streaming / Direct)    |
+---------------+---------------+
                |
                v
+-------------------------------+
|  5-Point Citation Verification|
| (Physical Bounds, Context Over|
|  lap, Symbol Match, Confidence|
+---------------+---------------+
                |
                v
+-------------------------------+
|  Grounding Status Evaluation  |
| (VERIFIED / PARTIAL / UNSUPP) |
+---------------+---------------+
                |
                v
+-------------------------------+
| GroundedAnswer + Verification |
| Metadata & Preserved Evidence |
+-------------------------------+
```

---

## 1. Intent Classification & Entity Extraction
Queries are classified by `QueryClassifier` into domain intents:
- `FACTUAL_CODE`: "Where is the JWT validation logic?" -> Prioritizes lexical + semantic chunk search on functions and methods.
- `ARCHITECTURE`: "Explain the system authentication architecture." -> Prioritizes high-level module overviews, entrypoints, and cross-file interfaces.
- `DEPENDENCY`: "What services depend on `UserService`?" -> Traverses graph nodes and call edges.
- `IMPACT`: "What breaks if I change `calculate_tax`?" -> Traverses downstream graph dependencies and highlights affected components/tests.
- `DOCUMENTATION`: "How do I run the test suite locally?" -> Focuses on `README.md`, setup scripts, and docstrings.
- `GENERAL_QA`: General programming queries evaluated with repository grounding.

Entities are extracted automatically (CamelCase symbols, snake_case functions, file paths with extensions) to bias hybrid search toward exact identifier matches.

---

## 2. Hard Evidence Threshold Gate & Controlled Fallback
To eliminate hallucinations when the query asks about files or concepts not present in the indexed codebase:
- The `ContextAssembler` evaluates the retrieved chunks against configurable thresholds (`min_relevance_score = 0.35`, `min_supporting_chunks = 1`).
- If no retrieved chunk meets the threshold, or if the retrieval result is completely empty, the pipeline executes a **hard fallback**.
- **Controlled Fallback Behavior**:
  - The pipeline immediately short-circuits.
  - Returns: `"I couldn't find enough evidence in the indexed repository to answer this reliably."`
  - The LLM is **never invoked**, guaranteeing zero hallucinated answers or fabricated citations.
  - Grounding status is set directly to `GroundingStatus.UNSUPPORTED`.

---

## 3. Context Selection, Deduplication & Token Budgeting
`ContextAssembler` builds a consolidated, token-budgeted `ContextPack`:
1. **Overlap & Line Deduplication**: Chunks from the same file with overlapping or contiguous line ranges `[start_line, end_line]` are merged into unified code blocks.
2. **Token Budget Enforcement**: Context is strictly capped at `4,000 tokens` (reserving headroom for system prompts, history, and generation).
3. **Graph Enrichment**: For `DEPENDENCY` and `IMPACT` intents, AST dependency graph edges (callers, callees, imports) are formatted into the prompt context.
4. **Evidence Preservation**: Every chunk retains its `chunk_id`, `file_id`, `file_path`, `symbol_name`, and retrieval score throughout the pipeline.

---

## 4. 5-Point Citation Verification Pipeline
`CitationVerifier` extracts all emitted markdown and tag citations (e.g. `[src/auth.py:10-25]`, `src/auth.py#L10-L25`, `[1]`) from the LLM answer and runs them through a 5-point verification pipeline:

```text
Emitted Citation
  |
  +---> 1. File Exists?
  |        Verifies that file_path exists in the repository/indexed file set.
  |
  +---> 2. Physical Bounds Valid?
  |        Verifies 1 <= start_line <= end_line <= total_lines_in_file.
  |
  +---> 3. Context Overlap Verified?
  |        Verifies that [start_line, end_line] overlaps at least one chunk
  |        actually provided to the LLM in the ContextPack.
  |
  +---> 4. Symbol Match Verified?
  |        If a symbol is claimed, checks whether the symbol name exists
  |        in the AST symbol table for that line range.
  |
  +---> 5. Grounding Confidence Calculation
           Calculates validation confidence score in [0.0, 1.0].
```

### Citation Statuses:
- **`VALID`**: File exists, lines within physical bounds, overlaps retrieved context chunk, symbol matches.
- **`INVALID_BOUNDS`**: Line numbers exceed file length or `start_line > end_line`.
- **`INVALID_FILE`**: Referenced file path does not exist in the repository.
- **`NO_CONTEXT_OVERLAP`**: The cited lines were never supplied to the LLM in the context prompt.
- **`SYMBOL_MISMATCH`**: The claimed symbol name does not match the AST symbols at those coordinates.

---

## 5. Grounding Status Semantics
Answers are classified into three strict, unambiguous grounding categories:

| Status | Semantics | Criteria |
| :--- | :--- | :--- |
| `VERIFIED` | Fully grounded with solid evidence | All citations are valid (`valid_ratio == 1.0`), context evidence is present, confidence $\ge 0.70$. |
| `PARTIALLY_VERIFIED` | Mixed or partially supported answer | Some valid citations present ($0 < valid\_ratio < 1.0$), or valid citations with confidence $< 0.70$. |
| `UNSUPPORTED` | Insufficient evidence or ungrounded | Zero valid citations, insufficient evidence fallback triggered, or all citations failed validation. |

---

## 6. End-to-End Evidence Lineage Preservation
The pipeline preserves end-to-end evidence lineage without loss of metadata:
```text
QueryAnalysis (intent, entities, query_type)
  |
  v
RetrievalResult (chunks, rrf_scores, dense_scores, bm25_scores)
  |
  v
ContextPack (formatted_context, total_tokens, chunks_used, graph_context)
  |
  v
GenerationResult (raw_answer, prompt_tokens, completion_tokens, finish_reason)
  |
  v
CitationValidationResult (citations, valid_citations, confidence_score, status)
  |
  v
GroundedAnswer (answer, citations, grounding_status, evidence_metadata)
```

---

## 7. Multi-Tenant Security & Access Control
- **Cross-Tenant Repository Isolation**: Every chat request strictly validates that the requesting user belongs to the organization owning the repository. Requests targeting foreign repositories return HTTP `403 Forbidden`.
- **Session Isolation**: Chat sessions (`GET /api/v1/chat/sessions`, `GET /api/v1/chat/sessions/{id}`, `DELETE /api/v1/chat/sessions/{id}`) enforce user ownership. A user cannot read, stream into, or delete another user's session.
- **Vector Space Partitioning**: Dense vector searches in Qdrant apply a mandatory filter on `repository_id`, preventing cross-repository context leakage.

---

## 8. SSE Streaming & Client Disconnect Safety
- Endpoint `POST /api/v1/chat` supports Server-Sent Events (`stream=true`).
- Emits structured event types:
  - `event: intent`: Query classification and entity analysis.
  - `event: context`: Retrieval evidence, chunk count, and token budget.
  - `event: token`: Incremental generated text tokens.
  - `event: complete`: Final answer with validated citations, confidence score, and grounding status.
  - `event: error`: Controlled error event if generation or validation fails.
- **Persistence Guarantee**: If the client aborts or cancels the SSE connection midway, partially received text and completed messages are safely finalized in the database without dangling lock states.
