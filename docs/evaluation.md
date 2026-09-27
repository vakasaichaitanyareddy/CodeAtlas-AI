# Retrieval & RAG Evaluation Framework

## Overview
CodeAtlas treats empirical benchmarking as a mandatory engineering component. Retrieval pipelines are evaluated against ground-truth repository question sets to scientifically justify retrieval and reranking parameters.

---

## 1. Metrics & Formulas

### Recall@K
Fraction of relevant code chunks retrieved within top-K positions:
$$\text{Recall@K} = \frac{|\text{Retrieved@K} \cap \text{Relevant}|}{|\text{Relevant}|}$$

### Mean Reciprocal Rank (MRR)
Average of the reciprocal ranks of the first relevant chunk:
$$\text{MRR} = \frac{1}{|Q|} \sum_{i=1}^{|Q|} \frac{1}{\text{rank}_i}$$

### Normalized Discounted Cumulative Gain (NDCG@K)
Measures ranking quality accounting for the position of relevant chunks:
$$\text{DCG@K} = \sum_{i=1}^K \frac{2^{\text{rel}_i} - 1}{\log_2(i + 1)}, \quad \text{NDCG@K} = \frac{\text{DCG@K}}{\text{IDCG@K}}$$

---

## 2. Benchmark Dataset Structure
The dataset in `benchmarks/dataset/` contains 500+ realistic codebase queries categorized by intent:
```json
{
  "id": "q_042",
  "query": "Where is the JWT token expiration validated?",
  "intent": "FACTUAL_CODE_QUERY",
  "expected_files": ["src/auth/jwt.py"],
  "expected_symbols": ["JWTValidator.validate_token"],
  "expected_lines": [[45, 62]],
  "ground_truth_context": "..."
}
```
