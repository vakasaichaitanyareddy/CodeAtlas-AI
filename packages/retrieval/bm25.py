from typing import List, Dict, Any, Optional
from rank_bm25 import BM25Okapi
from .tokenizer import CodeTokenizer
from .models import ScoredChunkDTO


class BM25Index:
    """In-memory BM25 lexical index with code-aware tokenization."""

    def __init__(self, chunks: Optional[List[Dict[str, Any]]] = None):
        self.chunks: List[Dict[str, Any]] = chunks or []
        self.corpus_tokens: List[List[str]] = []
        self.bm25: Optional[BM25Okapi] = None
        if self.chunks:
            self._build_index()

    def _build_index(self) -> None:
        """Tokenize all chunk contents along with file paths and symbols for inverted indexing."""
        self.corpus_tokens = []
        for c in self.chunks:
            f_path = c.get("file_path", "")
            sym_name = c.get("symbol_name") or ""
            prefix = f"{f_path} {sym_name}"
            full_text = f"{prefix} {prefix} {c.get('content', '')}"
            self.corpus_tokens.append(CodeTokenizer.tokenize(full_text))

        if self.corpus_tokens and any(len(doc) > 0 for doc in self.corpus_tokens):
            self.bm25 = BM25Okapi(self.corpus_tokens)
        else:
            self.bm25 = None

    def add_chunks(self, new_chunks: List[Dict[str, Any]]) -> None:
        """Add new chunks to the index and rebuild."""
        self.chunks.extend(new_chunks)
        self._build_index()

    def search(self, query: str, top_k: int = 20) -> List[ScoredChunkDTO]:
        """Perform lexical BM25 search for the query, returning top-k scored chunks."""
        if not self.bm25 or not query.strip() or not self.chunks:
            return []

        query_tokens = CodeTokenizer.expand_query_tokens(query)
        if not query_tokens:
            return []

        # Calculate BM25 scores
        scores = self.bm25.get_scores(query_tokens)

        # Pair chunks with scores (with token overlap fallback for small-corpus zero-IDF)
        query_set = set(t.lower() for t in query_tokens)
        scored_pairs = []
        for idx, score in enumerate(scores):
            chunk = self.chunks[idx]
            doc_tokens = self.corpus_tokens[idx]
            overlap_count = sum(1 for t in query_tokens if t in doc_tokens)
            if score > 0.0 or overlap_count > 0:
                effective_score = float(score) if score > 0.0 else float(overlap_count * 0.5)

                f_path = chunk.get("file_path", "").lower()
                sym = (chunk.get("symbol_name") or "").lower()

                # Prioritize symbol and file path matches
                if sym and (sym in query_set or any(q in sym for q in query_set)):
                    effective_score *= 1.35
                if any(q in f_path for q in query_set):
                    effective_score *= 1.15

                sym_type = (chunk.get("symbol_type") or "").upper()
                # Prioritize granular executable symbols (METHOD, FUNCTION, ENDPOINT) over coarse class or module containers
                if sym_type in ("METHOD", "FUNCTION", "ENDPOINT"):
                    effective_score *= 1.30
                elif sym_type in ("CLASS", "MODULE_OVERVIEW", "INTERFACE"):
                    effective_score *= 0.80

                # Demote changelogs and tests; boost source tree implementations
                if "changes" in f_path or "changelog" in f_path:
                    effective_score *= 0.25
                elif f_path.startswith("tests/"):
                    effective_score *= 0.75
                elif f_path.startswith(("src/", "flask/", "fastapi/")):
                    effective_score *= 1.25

                # Detect multilingual documentation translations and prioritize English/source
                if "docs/" in f_path or "docs\\" in f_path:
                    # Check if non-English translation
                    is_en = True
                    for loc in ("/ru/", "/zh/", "/ja/", "/es/", "/pt/", "/de/", "/fr/", "/hi/", "/tr/", "/ko/", "/it/", "/pl/", "/uk/", "/vi/", "/nl/", "/ar/", "/id/", "/sv/", "/cs/", "/fa/", "/he/"):
                        if loc in f_path.replace("\\", "/"):
                            is_en = False
                            break
                    if not is_en:
                        effective_score *= 0.65

                scored_pairs.append((chunk, round(effective_score, 4)))

        # Sort descending by score
        scored_pairs.sort(key=lambda x: x[1], reverse=True)

        # Deduplicate multilingual documentation chunks: keep single logical doc representation (prefer English)
        deduped_pairs = []
        doc_group_map = {}
        for chunk, score in scored_pairs:
            f_path = chunk.get("file_path", "").replace("\\", "/")
            if "docs/" in f_path:
                # Extract canonical subpath (e.g. docs/tutorial/dependencies/index.md)
                parts = f_path.split("docs/")
                canon_subpath = parts[-1]
                group_key = f"{canon_subpath}:{chunk.get('start_line', 1)}-{chunk.get('end_line', 1)}"
                is_en = "/en/" in f_path or f_path.startswith("docs/") and not any(f"/{l}/" in f_path for l in ("ru", "zh", "ja", "es", "pt", "de", "fr", "hi", "tr", "ko", "it", "pl", "uk", "vi", "nl", "ar", "id", "sv", "cs", "fa", "he"))
                if group_key not in doc_group_map:
                    idx = len(deduped_pairs)
                    deduped_pairs.append((chunk, score))
                    doc_group_map[group_key] = (idx, is_en, score)
                else:
                    # If existing is non-en but current is English, replace with English
                    prev_idx, prev_is_en, prev_score = doc_group_map[group_key]
                    best_score = max(prev_score, score)
                    if not prev_is_en and is_en:
                        deduped_pairs[prev_idx] = (chunk, best_score)
                        doc_group_map[group_key] = (prev_idx, True, best_score)
                    elif score > prev_score:
                        deduped_pairs[prev_idx] = (deduped_pairs[prev_idx][0], best_score)
                        doc_group_map[group_key] = (prev_idx, prev_is_en, best_score)
            else:
                deduped_pairs.append((chunk, score))

        top_pairs = deduped_pairs[:top_k]

        results: List[ScoredChunkDTO] = []
        for chunk, score in top_pairs:
            results.append(
                ScoredChunkDTO(
                    chunk_id=chunk["id"],
                    repository_id=chunk.get("repository_id", ""),
                    file_id=chunk.get("file_id", ""),
                    file_path=chunk.get("file_path", ""),
                    start_line=chunk.get("start_line", 1),
                    end_line=chunk.get("end_line", 1),
                    symbol_name=chunk.get("symbol_name"),
                    symbol_type=chunk.get("symbol_type"),
                    content=chunk.get("content", ""),
                    score=score,
                    lexical_score=score,
                    metadata=chunk.get("metadata", {}),
                )
            )

        return results

