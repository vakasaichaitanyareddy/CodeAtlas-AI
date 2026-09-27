# CodeAtlas Empirical Retrieval Benchmark

This directory contains the reproducible retrieval evaluation suite for CodeAtlas, assessing lexical, dense semantic, hybrid rank fusion, and reranking retrieval over indexed repository source code.

---

## 1. Directory Structure

```text
benchmarks/
├── README.md                      # Comprehensive benchmark documentation
├── dataset/
│   ├── queries.jsonl              # 60 structurally verified test queries with ground truth
│   └── README.md                  # Dataset schema, category counts, and hash
├── scripts/
│   └── run_retrieval_benchmark.py # Deterministic multi-mode evaluation harness
└── results/
    ├── raw_results.json           # Per-query hit ranks, latencies, and metric values
    ├── metrics.json               # Aggregated IR metrics across configurations
    ├── latency.json               # Latency percentiles (P50, P90, P95, P99, min, max, mean)
    ├── hard_queries.json          # Deep failure analysis of the 10 most challenging queries
    └── summary.csv                # Tabular summary for automated reporting
```

---

## 2. Evaluation Methodology & Metrics

### 2.1 Ground Truth Construction
Ground truth is created independently of retrieval outputs by directly inspecting the target repository source code (`3f5e9cbe-c565-4565-9cdb-600597d4207e` at `commit-after-failure`). Each query specifies:
- `relevant_files`: Target source file paths.
- `relevant_symbols`: Target functions, classes, or methods.

A retrieved chunk is scored as relevant ($rel = 1$) if its `file_path` matches the ground truth file AND its text content or symbol tag matches the expected symbol.

### 2.2 Metrics Computed
- **Recall@K (Hit@K)**: Proportion of queries where at least one relevant document is retrieved within the top $K$ candidates ($K \in \{1, 3, 5, 10\}$).
- **MRR (Mean Reciprocal Rank)**: $\frac{1}{|Q|} \sum_{i=1}^{|Q|} \frac{1}{\text{rank}_i}$, where $\text{rank}_i$ is the 1-based position of the first relevant chunk (0 if not in top $K$).
- **Precision@K**: Average proportion of retrieved documents in top $K$ that are relevant.
- **NDCG@K**: Normalized Discounted Cumulative Gain accounting for rank position of all relevant items.

---

## 3. Measured Empirical Results (v1.0.0)

Evaluated across **60 queries** against the live Docker microservices stack (Python 3.11, PostgreSQL 16, Qdrant HNSW vector store, Redis 7).

### 3.1 Retrieval Quality

| Configuration | Recall@1 | Recall@3 | Recall@5 | Recall@10 | MRR | Precision@5 | NDCG@10 |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **BM25 Only (Lexical)** | **0.7167** | **0.8167** | **0.8333** | **0.8333** | **0.7681** | **0.4067** | **0.7595** |
| **Dense Mock Baseline (Pipeline Validation)** | 0.0000 | 0.0000 | 0.0000 | 0.0333 | 0.0040 | 0.0000 | 0.0104 |
| **Hybrid RRF ($k=60$)** | 0.4167 | 0.7667 | 0.8167 | **0.8333** | 0.5752 | 0.2833 | 0.5993 |
| **Hybrid + Reranker** | 0.5333 | 0.8000 | **0.8333** | **0.8333** | 0.6611 | 0.3200 | 0.6643 |

*Critical Note on Dense Retrieval*:
**Semantic dense retrieval was not empirically benchmarked with a production semantic embedding model in this offline evaluation.**
The Dense Mock Baseline uses `MockEmbeddingProvider` (deterministic SHA-256 hash projections into 768-d space). This baseline verifies that the dense retrieval pipeline, Qdrant integration, payload filtering, and rank merging execute correctly and deterministically, but it does NOT measure the semantic retrieval quality of production embedding models (e.g. Gemini `text-embedding-004` or OpenAI `text-embedding-3-small`).

### 3.2 Latency Distribution (Measured HTTP Roundtrips via Port Forward)

| Configuration | Mean (ms) | P50 (ms) | P90 (ms) | P95 (ms) | P99 (ms) | Min (ms) | Max (ms) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **BM25 Only** | **207.54** | **186.30** | 300.18 | 344.99 | 424.68 | 143.94 | 424.68 |
| **Dense Mock Baseline** | 292.87 | 269.34 | 400.78 | 476.03 | 565.92 | 194.21 | 565.92 |
| **Hybrid RRF** | 310.77 | 289.89 | 401.93 | 459.84 | 549.39 | 212.19 | 549.39 |
| **Hybrid + Reranker** | 424.96 | 342.92 | 785.59 | 865.62 | 994.11 | 216.07 | 994.11 |

---

## 4. Key Engineering Insights

1. **Why Dense Vector Baseline Yields 0.0000 Recall@5**:
   In the offline testbed without live cloud API keys, `MockEmbeddingProvider` generates deterministic pseudo-random unit vectors from SHA-256 hashes. Because hash projections lack semantic topology, dense retrieval does not cluster related code concepts. This establishes that the evaluation harness honestly evaluates retrieval outputs rather than producing synthetic passes.
2. **The Discriminative Power of CodeTokenizer + BM25**:
   CodeAtlas's custom `CodeTokenizer` (which splits `camelCase`, `snake_case`, and compound terms while preserving language symbols) enables BM25 to achieve **Recall@5 = 0.8333** and **MRR = 0.7681** purely on lexical structure.
3. **RRF & Reranking Dynamics**:
   On this 60-query benchmark, adding cross-encoder reranking to Hybrid RRF candidates increased Top-1 Recall from 0.4167 to **0.5333** (a +28.0% relative improvement) and raised MRR from 0.5752 to **0.6611**.

---

## 5. Reproducing the Benchmark

To execute the benchmark against the running stack:

```bash
# Full benchmark over all 4 modes
python benchmarks/scripts/run_retrieval_benchmark.py

# Evaluate a specific mode
python benchmarks/scripts/run_retrieval_benchmark.py --mode bm25
```
