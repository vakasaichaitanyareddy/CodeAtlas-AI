import argparse
import json
import math
import os
import sys
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
import httpx
from jose import jwt

# Insert root to sys.path to access settings
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from apps.api.app.config import settings

def make_auth_token(user_id: str = "e45413c8-3d43-42a6-a9ad-72d06e94e6a5") -> str:
    now = datetime.now(timezone.utc)
    claims = {
        "sub": user_id,
        "role": "USER",
        "type": "access",
        "exp": now + datetime.timedelta(hours=4) if hasattr(datetime, "timedelta") else now,
        "iat": now,
    }
    import datetime as dt
    claims["exp"] = now + dt.timedelta(hours=4)
    return jwt.encode(claims, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

def is_chunk_relevant(chunk: Dict[str, Any], query_gt: Dict[str, Any]) -> bool:
    """Check if retrieved chunk matches ground truth files and symbols."""
    file_path = chunk.get("file_path", "")
    content = chunk.get("content", "").lower()
    symbol_name = (chunk.get("symbol_name") or "").lower()

    rel_files = [f.lower() for f in query_gt.get("relevant_files", [])]
    rel_symbols = [s.lower() for s in query_gt.get("relevant_symbols", [])]

    # File must match
    if not any(rf in file_path.lower() or file_path.lower() in rf for rf in rel_files):
        return False

    # If symbols are specified, either symbol_name or content must contain one of them
    if rel_symbols:
        symbol_matched = False
        if symbol_name and any(rs in symbol_name for rs in rel_symbols):
            symbol_matched = True
        elif any(rs in content for rs in rel_symbols):
            symbol_matched = True
        return symbol_matched

    return True

def compute_dcg(relevances: List[int], k: int) -> float:
    dcg = 0.0
    for i in range(min(k, len(relevances))):
        if relevances[i] > 0:
            dcg += relevances[i] / math.log2(i + 2)
    return dcg

def compute_ndcg(relevances: List[int], k: int) -> float:
    dcg = compute_dcg(relevances, k)
    ideal = sorted(relevances, reverse=True)
    idcg = compute_dcg(ideal, k)
    return (dcg / idcg) if idcg > 0.0 else 0.0

def evaluate_retrieval(
    client: httpx.Client,
    repo_id: str,
    query_obj: Dict[str, Any],
    mode: str,
    rerank: bool,
    top_k: int = 10,
) -> Tuple[Dict[str, Any], float]:
    """Execute search query and return performance metrics and latency."""
    t0 = time.perf_counter()
    r = client.post(
        f"/repositories/{repo_id}/search",
        json={
            "query": query_obj["query"],
            "mode": mode,
            "top_k": top_k,
            "rerank": rerank,
        },
    )
    latency_ms = (time.perf_counter() - t0) * 1000.0

    if r.status_code != 200:
        raise RuntimeError(f"Search API returned {r.status_code}: {r.text}")

    data = r.json()
    results = data.get("results", [])

    relevances = []
    first_rel_rank = 0

    for idx, c in enumerate(results, start=1):
        rel = 1 if is_chunk_relevant(c, query_obj) else 0
        relevances.append(rel)
        if rel == 1 and first_rel_rank == 0:
            first_rel_rank = idx

    # Compute metrics
    mrr = (1.0 / first_rel_rank) if first_rel_rank > 0 else 0.0

    def recall_at(k: int) -> float:
        return 1.0 if any(r > 0 for r in relevances[:k]) else 0.0

    def precision_at(k: int) -> float:
        sub = relevances[:k]
        return (sum(sub) / k) if k > 0 else 0.0

    record = {
        "query_id": query_obj["id"],
        "query": query_obj["query"],
        "category": query_obj["category"],
        "difficulty": query_obj["difficulty"],
        "first_relevant_rank": first_rel_rank,
        "mrr": mrr,
        "recall_1": recall_at(1),
        "recall_3": recall_at(3),
        "recall_5": recall_at(5),
        "recall_10": recall_at(10),
        "precision_1": precision_at(1),
        "precision_5": precision_at(5),
        "precision_10": precision_at(10),
        "ndcg_5": compute_ndcg(relevances, 5),
        "ndcg_10": compute_ndcg(relevances, 10),
        "latency_ms": latency_ms,
        "top_result_file": results[0]["file_path"] if results else None,
        "top_result_score": results[0]["score"] if results else 0.0,
    }
    return record, latency_ms

def percentile(data: List[float], p: float) -> float:
    if not data:
        return 0.0
    sorted_d = sorted(data)
    idx = int(len(sorted_d) * (p / 100.0))
    idx = min(idx, len(sorted_d) - 1)
    return sorted_d[idx]

def run_benchmark(
    base_url: str = "http://localhost:8000/api/v1",
    dataset_path: str = "benchmarks/dataset/queries.jsonl",
    output_dir: str = "benchmarks/results",
    warmup: int = 3,
    top_k: int = 10,
    selected_modes: Optional[List[str]] = None,
):
    os.makedirs(output_dir, exist_ok=True)
    with open(dataset_path, "r", encoding="utf-8") as f:
        queries = [json.loads(line) for line in f if line.strip()]

    print(f"Loaded {len(queries)} queries from {dataset_path}")
    token = make_auth_token()
    headers = {"Authorization": f"Bearer {token}"}
    client = httpx.Client(base_url=base_url, headers=headers, timeout=60.0)

    configs = [
        {"name": "BM25", "mode": "lexical", "rerank": False},
        {"name": "Dense", "mode": "semantic", "rerank": False},
        {"name": "Hybrid", "mode": "hybrid", "rerank": False},
        {"name": "Hybrid+Reranker", "mode": "hybrid", "rerank": True},
    ]

    if selected_modes and "all" not in selected_modes:
        configs = [c for c in configs if c["name"].lower() in [m.lower() for m in selected_modes]]

    repo_id = queries[0]["repository"]

    # Warmup
    if warmup > 0:
        print(f"Executing {warmup} warmup queries...")
        for q in queries[:warmup]:
            for cfg in configs:
                try:
                    evaluate_retrieval(client, repo_id, q, cfg["mode"], cfg["rerank"], top_k=top_k)
                except Exception as e:
                    print(f"Warmup warning: {e}")

    raw_results = {}
    aggregated_metrics = {}
    latency_stats = {}
    category_breakdowns = {}

    for cfg in configs:
        cfg_name = cfg["name"]
        print(f"\n--- Benchmarking Configuration: {cfg_name} ---")
        cfg_records = []
        latencies = []

        for idx, q in enumerate(queries, start=1):
            rec, lat = evaluate_retrieval(client, repo_id, q, cfg["mode"], cfg["rerank"], top_k=top_k)
            cfg_records.append(rec)
            latencies.append(lat)
            if idx % 15 == 0 or idx == len(queries):
                print(f"  [{idx}/{len(queries)}] Completed. Latest latency: {lat:.1f}ms")

        raw_results[cfg_name] = cfg_records

        # Calculate averages across all queries
        n = len(cfg_records)
        avg_rec1 = sum(r["recall_1"] for r in cfg_records) / n
        avg_rec3 = sum(r["recall_3"] for r in cfg_records) / n
        avg_rec5 = sum(r["recall_5"] for r in cfg_records) / n
        avg_rec10 = sum(r["recall_10"] for r in cfg_records) / n
        avg_mrr = sum(r["mrr"] for r in cfg_records) / n
        avg_p1 = sum(r["precision_1"] for r in cfg_records) / n
        avg_p5 = sum(r["precision_5"] for r in cfg_records) / n
        avg_p10 = sum(r["precision_10"] for r in cfg_records) / n
        avg_ndcg5 = sum(r["ndcg_5"] for r in cfg_records) / n
        avg_ndcg10 = sum(r["ndcg_10"] for r in cfg_records) / n

        aggregated_metrics[cfg_name] = {
            "Recall@1": round(avg_rec1, 4),
            "Recall@3": round(avg_rec3, 4),
            "Recall@5": round(avg_rec5, 4),
            "Recall@10": round(avg_rec10, 4),
            "MRR": round(avg_mrr, 4),
            "Precision@1": round(avg_p1, 4),
            "Precision@5": round(avg_p5, 4),
            "Precision@10": round(avg_p10, 4),
            "NDCG@5": round(avg_ndcg5, 4),
            "NDCG@10": round(avg_ndcg10, 4),
        }

        # Latency statistics
        mean_lat = sum(latencies) / len(latencies)
        variance = sum((x - mean_lat) ** 2 for x in latencies) / (len(latencies) - 1 or 1)
        std_lat = math.sqrt(variance)

        latency_stats[cfg_name] = {
            "mean_ms": round(mean_lat, 2),
            "std_ms": round(std_lat, 2),
            "min_ms": round(min(latencies), 2),
            "max_ms": round(max(latencies), 2),
            "P50_ms": round(percentile(latencies, 50), 2),
            "P90_ms": round(percentile(latencies, 90), 2),
            "P95_ms": round(percentile(latencies, 95), 2),
            "P99_ms": round(percentile(latencies, 99), 2),
        }

        # Breakdown by category
        cat_map = {}
        for r in cfg_records:
            cat = r["category"]
            if cat not in cat_map:
                cat_map[cat] = []
            cat_map[cat].append(r)

        cat_summary = {}
        for cat, recs in cat_map.items():
            cat_summary[cat] = {
                "count": len(recs),
                "Recall@5": round(sum(x["recall_5"] for x in recs) / len(recs), 4),
                "MRR": round(sum(x["mrr"] for x in recs) / len(recs), 4),
                "NDCG@10": round(sum(x["ndcg_10"] for x in recs) / len(recs), 4),
            }
        category_breakdowns[cfg_name] = cat_summary

    # Save results to disk
    raw_path = os.path.join(output_dir, "raw_results.json")
    with open(raw_path, "w", encoding="utf-8") as f:
        json.dump(raw_results, f, indent=2)

    metrics_path = os.path.join(output_dir, "metrics.json")
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(aggregated_metrics, f, indent=2)

    latency_path = os.path.join(output_dir, "latency.json")
    with open(latency_path, "w", encoding="utf-8") as f:
        json.dump(latency_stats, f, indent=2)

    # Save summary CSV
    csv_path = os.path.join(output_dir, "summary.csv")
    with open(csv_path, "w", encoding="utf-8") as f:
        f.write("Configuration,Recall@1,Recall@3,Recall@5,Recall@10,MRR,Precision@5,NDCG@5,NDCG@10,Mean_Latency_ms,P50_ms,P95_ms,P99_ms\n")
        for cfg_name in aggregated_metrics:
            m = aggregated_metrics[cfg_name]
            l = latency_stats[cfg_name]
            f.write(f"{cfg_name},{m['Recall@1']},{m['Recall@3']},{m['Recall@5']},{m['Recall@10']},{m['MRR']},{m['Precision@5']},{m['NDCG@5']},{m['NDCG@10']},{l['mean_ms']},{l['P50_ms']},{l['P95_ms']},{l['P99_ms']}\n")

    # Hard query analysis (lowest combined scores)
    hardest_queries = []
    first_cfg = list(raw_results.keys())[0]
    for q_idx in range(len(queries)):
        q_obj = queries[q_idx]
        hybrid_rec = raw_results.get("Hybrid", raw_results[first_cfg])[q_idx]
        bm25_rec = raw_results.get("BM25", raw_results[first_cfg])[q_idx]
        dense_rec = raw_results.get("Dense", raw_results[first_cfg])[q_idx]
        rerank_rec = raw_results.get("Hybrid+Reranker", raw_results[first_cfg])[q_idx]

        combined_score = bm25_rec["mrr"] + dense_rec["mrr"] + hybrid_rec["mrr"] + rerank_rec["mrr"]
        hardest_queries.append({
            "query_id": q_obj["id"],
            "query": q_obj["query"],
            "category": q_obj["category"],
            "difficulty": q_obj["difficulty"],
            "relevant_files": q_obj["relevant_files"],
            "bm25_rank": bm25_rec["first_relevant_rank"],
            "dense_rank": dense_rec["first_relevant_rank"],
            "hybrid_rank": hybrid_rec["first_relevant_rank"],
            "rerank_rank": rerank_rec["first_relevant_rank"],
            "combined_mrr": combined_score,
        })

    hardest_queries.sort(key=lambda x: x["combined_mrr"])
    hard_path = os.path.join(output_dir, "hard_queries.json")
    with open(hard_path, "w", encoding="utf-8") as f:
        json.dump(hardest_queries[:10], f, indent=2)

    # Print summary tables
    print("\n" + "=" * 90)
    print("FINAL MEASURED RETRIEVAL QUALITY SUMMARY")
    print("=" * 90)
    print(f"{'Configuration':<18} | {'Recall@1':<8} | {'Recall@5':<8} | {'Recall@10':<9} | {'MRR':<6} | {'NDCG@10':<8} | {'Mean Latency':<12}")
    print("-" * 90)
    for name in aggregated_metrics:
        m = aggregated_metrics[name]
        l = latency_stats[name]
        print(f"{name:<18} | {m['Recall@1']:<8.4f} | {m['Recall@5']:<8.4f} | {m['Recall@10']:<9.4f} | {m['MRR']:<6.4f} | {m['NDCG@10']:<8.4f} | {l['mean_ms']:>8.2f} ms")
    print("=" * 90)

    print("\n" + "=" * 90)
    print("LATENCY DISTRIBUTION (ms)")
    print("=" * 90)
    print(f"{'Configuration':<18} | {'P50':<8} | {'P90':<8} | {'P95':<8} | {'P99':<8} | {'Min':<8} | {'Max':<8}")
    print("-" * 90)
    for name in latency_stats:
        l = latency_stats[name]
        print(f"{name:<18} | {l['P50_ms']:<8.2f} | {l['P90_ms']:<8.2f} | {l['P95_ms']:<8.2f} | {l['P99_ms']:<8.2f} | {l['min_ms']:<8.2f} | {l['max_ms']:<8.2f}")
    print("=" * 90)

    return aggregated_metrics, latency_stats, category_breakdowns

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run CodeAtlas Retrieval Benchmark")
    parser.add_argument("--dataset", default="benchmarks/dataset/queries.jsonl")
    parser.add_argument("--output", default="benchmarks/results")
    parser.add_argument("--warmup", type=int, default=3)
    parser.add_argument("--top-k", type=int, default=10)
    parser.add_argument("--mode", nargs="+", default=["all"])
    args = parser.parse_args()

    run_benchmark(
        dataset_path=args.dataset,
        output_dir=args.output,
        warmup=args.warmup,
        top_k=args.top_k,
        selected_modes=args.mode,
    )
