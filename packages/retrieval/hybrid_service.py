import asyncio
import re
import time
from typing import List, Optional, Tuple
from .models import SearchMode, SearchRequestDTO, SearchResultDTO, ScoredChunkDTO
from .bm25 import BM25Index
from .vector import VectorIndex
from .fusion import ReciprocalRankFusion
from .reranker import CrossEncoderReranker

LOCALE_PATTERN = re.compile(
    r"^(docs|documentation|doc|i18n|locales?)/([a-z]{2,3}(?:-[a-z0-9]+)?)/(?:docs/)?(.*)$",
    re.IGNORECASE,
)


def canonicalize_doc_path(file_path: str) -> Tuple[str, bool, str]:
    """Return (canonical_doc_key, is_english_or_source, locale_code)."""
    if not file_path:
        return ("", True, "en")
    clean_path = file_path.replace("\\", "/").strip("/")
    m = LOCALE_PATTERN.match(clean_path)
    if m:
        prefix, locale, subpath = m.group(1).lower(), m.group(2).lower(), m.group(3)
        canonical = f"{prefix}/{subpath}"
        is_english = locale in ("en", "en-us", "en-gb", "source", "default")
        return (canonical, is_english, locale)
    return (clean_path, True, "en")


class HybridSearchService:
    """Unified service orchestrating lexical, dense vector, fusion, and reranking retrieval."""

    def __init__(
        self,
        bm25_index: BM25Index,
        vector_index: VectorIndex,
        reranker: Optional[CrossEncoderReranker] = None,
        rrf_constant: int = 60,
    ):
        self.bm25_index = bm25_index
        self.vector_index = vector_index
        self.reranker = reranker
        self.fusion = ReciprocalRankFusion(k=rrf_constant)

    async def search(
        self,
        repository_id: str,
        request: SearchRequestDTO,
        commit_sha: Optional[str] = None,
    ) -> SearchResultDTO:
        """Execute code retrieval according to requested mode with optional reranking and filters."""
        start_time = time.perf_counter()
        query = request.query.strip()
        top_k = request.top_k
        mode = request.mode

        if not query:
            return SearchResultDTO(
                query=query,
                mode=mode.value,
                total_candidates=0,
                results=[],
                execution_time_ms=0.0,
            )

        fetch_k = min(50, max(top_k * 3, 25))

        if mode == SearchMode.LEXICAL:
            # 1. Lexical BM25 only
            candidates = self.bm25_index.search(query=query, top_k=fetch_k)

        elif mode == SearchMode.SEMANTIC:
            # 2. Dense Vector only
            candidates = await self.vector_index.search(
                repository_id=repository_id,
                query=query,
                top_k=fetch_k,
                commit_sha=commit_sha,
            )

        else:
            # 3. Hybrid: Lexical + Vector via RRF
            lexical_task = asyncio.to_thread(self.bm25_index.search, query=query, top_k=fetch_k)
            vector_task = self.vector_index.search(
                repository_id=repository_id,
                query=query,
                top_k=fetch_k,
                commit_sha=commit_sha,
            )

            lexical_results, vector_results = await asyncio.gather(lexical_task, vector_task)
            candidates = self.fusion.fuse(
                lexical_results=lexical_results,
                vector_results=vector_results,
                top_k=fetch_k,
            )

        # Apply metadata filters
        filtered_candidates = self._apply_filters(
            candidates,
            symbol_type=request.symbol_type,
            file_pattern=request.file_pattern,
        )

        # Deduplicate multilingual documentation before reranker to prevent translated mirrors crowding out code
        deduped_candidates = self._deduplicate_multilingual_docs(filtered_candidates)

        # Rerank if enabled and provider is configured
        if request.rerank and self.reranker and deduped_candidates:
            rerank_k = min(len(deduped_candidates), max(top_k * 3, 20))
            reranked_results = await self.reranker.rerank(
                query=query,
                candidates=deduped_candidates,
                top_k=rerank_k,
            )
            final_results = self._diversify_results(reranked_results, top_k=top_k)
        else:
            final_results = self._diversify_results(deduped_candidates, top_k=top_k)

        elapsed_ms = round((time.perf_counter() - start_time) * 1000.0, 2)

        return SearchResultDTO(
            query=query,
            mode=mode.value,
            total_candidates=len(candidates),
            results=final_results,
            execution_time_ms=elapsed_ms,
        )

    @classmethod
    def _deduplicate_multilingual_docs(
        cls,
        candidates: List[ScoredChunkDTO],
    ) -> List[ScoredChunkDTO]:
        """Collapse translated copies of the same documentation page into a single logical result, preferring English/source."""
        if not candidates:
            return []

        doc_groups: dict = {}  # key -> list of candidates
        non_docs: List[ScoredChunkDTO] = []
        item_order: List[Tuple[str, str]] = []  # ('doc', key) or ('code', chunk_id)

        for c in candidates:
            fpath = c.file_path or ""
            canon_key, is_en, _ = canonicalize_doc_path(fpath)
            is_doc = "docs/" in fpath or "docs\\" in fpath or canon_key.startswith("docs/")

            if is_doc:
                # Group by canonical doc path and relative chunk line span
                group_key = f"{canon_key}:{c.start_line}-{c.end_line}"
                if group_key not in doc_groups:
                    doc_groups[group_key] = []
                    item_order.append(("doc", group_key))
                doc_groups[group_key].append(c)
            else:
                non_docs.append(c)
                item_order.append(("code", c.chunk_id))

        # For each doc group, select the single best logical representation, preferring English
        chosen_docs: dict = {}
        for group_key, group in doc_groups.items():
            en_candidates = [c for c in group if canonicalize_doc_path(c.file_path or "")[1]]
            max_group_score = max(c.score for c in group)
            if en_candidates:
                # Pick the highest-scoring English candidate and assign max group score
                chosen = max(en_candidates, key=lambda x: x.score)
            else:
                chosen = max(group, key=lambda x: x.score)

            chosen.score = max_group_score
            chosen_docs[group_key] = chosen

        # Rebuild deduplicated candidate list in original ranking order
        code_map = {c.chunk_id: c for c in non_docs}
        deduped: List[ScoredChunkDTO] = []
        seen_keys: set = set()

        for itype, ikey in item_order:
            if ikey in seen_keys:
                continue
            seen_keys.add(ikey)
            if itype == "doc" and ikey in chosen_docs:
                deduped.append(chosen_docs[ikey])
            elif itype == "code" and ikey in code_map:
                deduped.append(code_map[ikey])

        return deduped

    @classmethod
    def _diversify_results(
        cls,
        candidates: List[ScoredChunkDTO],
        top_k: int = 10,
    ) -> List[ScoredChunkDTO]:
        """Apply soft MMR diversity to suppress same-file/sibling symbol clustering while preserving relevance."""
        if len(candidates) <= 1:
            return candidates[:top_k]

        selected: List[ScoredChunkDTO] = []
        file_counts: dict = {}
        symbol_counts: dict = {}
        seen_canonical_docs: set = set()
        doc_count = 0

        remaining = list(candidates)

        while remaining and len(selected) < top_k:
            best_idx = -1
            best_score = -float("inf")

            for idx, item in enumerate(remaining):
                base_score = item.score
                fpath = item.file_path or ""
                sym = item.symbol_name or ""
                canon_key, is_en, _ = canonicalize_doc_path(fpath)
                is_doc = "docs/" in fpath or "docs\\" in fpath or canon_key.startswith("docs/")

                # 1. Strict duplicate elimination for translated documentation copies
                if is_doc and canon_key in seen_canonical_docs:
                    continue

                # 2. Progressive file saturation penalty (prevents single file monopoly)
                f_count = file_counts.get(fpath, 0)
                file_factor = 1.0 if f_count == 0 else (0.65 if f_count == 1 else 0.35 / (f_count ** 0.5))

                # 3. Sibling / duplicate symbol penalty
                sym_count = symbol_counts.get(sym, 0) if sym else 0
                sym_factor = 1.0 if sym_count == 0 else (0.30 if sym_count == 1 else 0.10)

                # 4. Documentation balance and English preference
                doc_factor = 1.0
                if is_doc:
                    doc_factor = 0.75 if doc_count < 2 else 0.25
                    if not is_en:
                        doc_factor *= 0.50

                adjusted_score = base_score * file_factor * sym_factor * doc_factor
                if adjusted_score > best_score:
                    best_score = adjusted_score
                    best_idx = idx

            if best_idx >= 0:
                chosen = remaining.pop(best_idx)
                selected.append(chosen)
                fpath = chosen.file_path or ""
                sym = chosen.symbol_name or ""
                canon_key, is_en, _ = canonicalize_doc_path(fpath)
                is_doc = "docs/" in fpath or "docs\\" in fpath or canon_key.startswith("docs/")

                file_counts[fpath] = file_counts.get(fpath, 0) + 1
                if sym:
                    symbol_counts[sym] = symbol_counts.get(sym, 0) + 1
                if is_doc:
                    doc_count += 1
                    seen_canonical_docs.add(canon_key)
            else:
                break

        return selected

    @staticmethod
    def _apply_filters(
        candidates: List[ScoredChunkDTO],
        symbol_type: Optional[str] = None,
        file_pattern: Optional[str] = None,
    ) -> List[ScoredChunkDTO]:
        """Filter retrieved candidates based on symbol type and file path substring."""
        if not symbol_type and not file_pattern:
            return candidates

        filtered: List[ScoredChunkDTO] = []
        for c in candidates:
            if symbol_type and (not c.symbol_type or c.symbol_type.upper() != symbol_type.upper()):
                continue
            if file_pattern and file_pattern.lower() not in c.file_path.lower():
                continue
            filtered.append(c)

        return filtered

