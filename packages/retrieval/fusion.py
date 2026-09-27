import re
from typing import List, Dict, Tuple
from .models import ScoredChunkDTO

LOCALE_PATTERN = re.compile(
    r"^(docs|documentation|doc|i18n|locales?)/([a-z]{2,3}(?:-[a-z0-9]+)?)/(?:docs/)?(.*)$",
    re.IGNORECASE,
)


def _canonical_doc_key(file_path: str) -> Tuple[str, bool]:
    if not file_path:
        return ("", True)
    clean_path = file_path.replace("\\", "/").strip("/")
    m = LOCALE_PATTERN.match(clean_path)
    if m:
        prefix, locale, subpath = m.group(1).lower(), m.group(2).lower(), m.group(3)
        canonical = f"{prefix}/{subpath}"
        is_english = locale in ("en", "en-us", "en-gb", "source", "default")
        return (canonical, is_english)
    return (clean_path, True)


class ReciprocalRankFusion:
    """Combines multiple ranked retrieval lists using Reciprocal Rank Fusion (RRF)."""

    def __init__(self, k: int = 60):
        self.k = k

    def fuse(
        self,
        lexical_results: List[ScoredChunkDTO],
        vector_results: List[ScoredChunkDTO],
        top_k: int = 20,
    ) -> List[ScoredChunkDTO]:
        """Fuse BM25 lexical rankings and dense vector rankings via RRF with multilingual doc canonicalization."""
        chunk_map: Dict[str, ScoredChunkDTO] = {}
        rrf_scores: Dict[str, float] = {}

        # 1. Process Lexical (BM25) rankings (1-based rank)
        for rank, item in enumerate(lexical_results, start=1):
            cid = item.chunk_id
            chunk_map[cid] = item
            rrf_score = 1.0 / (self.k + rank)
            rrf_scores[cid] = rrf_scores.get(cid, 0.0) + rrf_score
            item.lexical_score = item.score

        # 2. Process Vector rankings (1-based rank)
        for rank, item in enumerate(vector_results, start=1):
            cid = item.chunk_id
            if cid not in chunk_map:
                chunk_map[cid] = item
            else:
                # Merge vector score into existing candidate
                chunk_map[cid].vector_score = item.score

            rrf_score = 1.0 / (self.k + rank)
            rrf_scores[cid] = rrf_scores.get(cid, 0.0) + rrf_score

        # 3. Canonicalize multilingual documentation chunks into single logical entries (preferring English)
        doc_group_best: Dict[str, Tuple[str, bool, float]] = {}  # group_key -> (best_cid, is_en, total_score)
        non_doc_cids = set()

        for cid, score in list(rrf_scores.items()):
            chunk = chunk_map[cid]
            fpath = chunk.file_path or ""
            if "docs/" in fpath.replace("\\", "/"):
                canon_path, is_en = _canonical_doc_key(fpath)
                group_key = f"{canon_path}:{chunk.start_line}-{chunk.end_line}"
                if group_key not in doc_group_best:
                    doc_group_best[group_key] = (cid, is_en, score)
                else:
                    prev_cid, prev_is_en, prev_score = doc_group_best[group_key]
                    merged_score = prev_score + score
                    # Prefer English candidate if available
                    if not prev_is_en and is_en:
                        doc_group_best[group_key] = (cid, True, merged_score)
                        del rrf_scores[prev_cid]
                        rrf_scores[cid] = merged_score
                    else:
                        doc_group_best[group_key] = (prev_cid, prev_is_en, merged_score)
                        del rrf_scores[cid]
                        rrf_scores[prev_cid] = merged_score
            else:
                non_doc_cids.add(cid)

        # 4. Sort by fused RRF score descending with symbol granularity weighting
        def _fused_key(item_pair: Tuple[str, float]) -> float:
            cid, base_score = item_pair
            chunk = chunk_map.get(cid)
            sym_type = (chunk.symbol_type or "").upper() if chunk else ""
            if sym_type in ("METHOD", "FUNCTION", "ENDPOINT"):
                return base_score * 1.15
            elif sym_type in ("CLASS", "MODULE_OVERVIEW", "INTERFACE"):
                return base_score * 0.90
            return base_score

        sorted_pairs = sorted(rrf_scores.items(), key=_fused_key, reverse=True)
        top_pairs = sorted_pairs[:top_k]

        fused_results: List[ScoredChunkDTO] = []
        for cid, score in top_pairs:
            chunk = chunk_map[cid]
            final_fused_score = _fused_key((cid, score))
            chunk.score = round(final_fused_score, 6)
            chunk.rrf_score = round(final_fused_score, 6)
            fused_results.append(chunk)

        return fused_results

