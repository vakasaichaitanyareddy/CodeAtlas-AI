import logging
from typing import List, Dict, Any, Optional, Set
from .models import (
    QueryAnalysis,
    ContextChunk,
    ContextPack,
    RetrievalEvidence,
    QueryIntent,
)
from packages.retrieval.models import ScoredChunkDTO

logger = logging.getLogger("codeatlas.rag.context")


class ContextAssembler:
    """Assembles, deduplicates, filters, and token-budgets retrieval evidence."""

    def __init__(
        self,
        token_budget: int = 4000,
        min_relevance_score: float = 0.015,
        min_supporting_chunks: int = 1,
    ):
        self.token_budget = token_budget
        self.min_relevance_score = min_relevance_score
        self.min_supporting_chunks = min_supporting_chunks

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """Heuristic token estimator (approx. 4 characters per token)."""
        return max(1, len(text) // 4)

    def assemble_context(
        self,
        analysis: QueryAnalysis,
        scored_candidates: List[ScoredChunkDTO],
        graph_context: Optional[List[Dict[str, Any]]] = None,
    ) -> ContextPack:
        """Assemble scored chunks and graph data into a token-budgeted ContextPack."""
        evidence = RetrievalEvidence(
            candidate_count=len(scored_candidates),
            selected_count=0,
            discarded_count=0,
            bm25_scores=[],
            vector_scores=[],
            rrf_scores=[],
            reranker_scores=[],
            context_tokens=0,
            evidence_threshold_met=True,
            threshold_reason="sufficient_evidence",
        )

        for c in scored_candidates:
            if c.lexical_score is not None:
                evidence.bm25_scores.append(round(c.lexical_score, 4))
            if c.vector_score is not None:
                evidence.vector_scores.append(round(c.vector_score, 4))
            if c.rrf_score is not None:
                evidence.rrf_scores.append(round(c.rrf_score, 6))
            if c.rerank_score is not None:
                evidence.reranker_scores.append(round(c.rerank_score, 4))

        # Check for empty candidates
        if not scored_candidates:
            evidence.evidence_threshold_met = False
            evidence.threshold_reason = "no_candidates_retrieved"
            return ContextPack(
                query=analysis.raw_query,
                analysis=analysis,
                chunks=[],
                total_tokens=0,
                token_budget=self.token_budget,
                evidence=evidence,
            )

        # Check minimum relevance score threshold
        top_score = scored_candidates[0].score
        if top_score < self.min_relevance_score:
            evidence.evidence_threshold_met = False
            evidence.threshold_reason = (
                f"top_score_{top_score:.4f}_below_minimum_{self.min_relevance_score:.4f}"
            )
            evidence.discarded_count = len(scored_candidates)
            return ContextPack(
                query=analysis.raw_query,
                analysis=analysis,
                chunks=[],
                total_tokens=0,
                token_budget=self.token_budget,
                evidence=evidence,
            )

        # 1. Deduplicate overlapping chunks in the same file
        deduped_chunks: List[ScoredChunkDTO] = []
        seen_intervals: Dict[str, List[tuple]] = {}  # file_path -> [(start, end)]

        for c in scored_candidates:
            path = c.file_path
            start, end = c.start_line, c.end_line

            # Check overlap with existing intervals in same file
            overlaps = False
            if path in seen_intervals:
                for s_start, s_end in seen_intervals[path]:
                    # Check significant overlap (more than 50% overlap of smaller range)
                    overlap_len = max(0, min(end, s_end) - max(start, s_start))
                    min_len = min(end - start, s_end - s_start)
                    if min_len > 0 and (overlap_len / min_len) > 0.5:
                        overlaps = True
                        break

            if not overlaps:
                deduped_chunks.append(c)
                if path not in seen_intervals:
                    seen_intervals[path] = []
                seen_intervals[path].append((start, end))
            else:
                evidence.discarded_count += 1

        # 2. Token Budgeting: Select chunks until budget is filled
        selected_chunks: List[ContextChunk] = []
        current_tokens = 0

        # Inject graph context if relevant (DEPENDENCY or IMPACT)
        if graph_context and analysis.intent in (QueryIntent.DEPENDENCY, QueryIntent.IMPACT):
            for g_item in graph_context:
                graph_text = g_item.get("description", "")
                t_count = self.estimate_tokens(graph_text)
                if current_tokens + t_count <= self.token_budget:
                    selected_chunks.append(
                        ContextChunk(
                            chunk_id=g_item.get("id", "graph-node"),
                            file_path=g_item.get("file_path", "dependency-graph"),
                            symbol_name=g_item.get("symbol_name"),
                            symbol_type="GRAPH_RELATION",
                            start_line=g_item.get("start_line", 1),
                            end_line=g_item.get("end_line", 1),
                            content=graph_text,
                            score=1.0,
                            source="graph",
                            metadata=g_item.get("metadata", {}),
                        )
                    )
                    current_tokens += t_count

        for c in deduped_chunks:
            chunk_tokens = self.estimate_tokens(c.content)
            if current_tokens + chunk_tokens <= self.token_budget:
                selected_chunks.append(
                    ContextChunk(
                        chunk_id=c.chunk_id,
                        file_path=c.file_path,
                        symbol_name=c.symbol_name,
                        symbol_type=c.symbol_type,
                        start_line=c.start_line,
                        end_line=c.end_line,
                        content=c.content,
                        score=c.score,
                        source="hybrid",
                        metadata=c.metadata,
                    )
                )
                current_tokens += chunk_tokens
            else:
                evidence.discarded_count += 1

        evidence.selected_count = len(selected_chunks)
        evidence.context_tokens = current_tokens

        # Check minimum supporting chunks
        if len(selected_chunks) < self.min_supporting_chunks:
            evidence.evidence_threshold_met = False
            evidence.threshold_reason = (
                f"supporting_chunks_{len(selected_chunks)}_below_minimum_{self.min_supporting_chunks}"
            )

        return ContextPack(
            query=analysis.raw_query,
            analysis=analysis,
            chunks=selected_chunks,
            total_tokens=current_tokens,
            token_budget=self.token_budget,
            evidence=evidence,
        )

    @staticmethod
    def format_context_for_prompt(context_pack: ContextPack) -> str:
        """Format the selected chunks into a clean, markdown-delimited prompt block."""
        if not context_pack.chunks:
            return "No verified code snippets available."

        blocks = []
        for idx, ch in enumerate(context_pack.chunks, 1):
            sym_info = f", Symbol: {ch.symbol_name}" if ch.symbol_name else ""
            type_info = f" [{ch.symbol_type}]" if ch.symbol_type else ""
            header = f"### [Source {idx}] File: {ch.file_path} (Lines {ch.start_line}-{ch.end_line}{sym_info}{type_info})"
            
            # Determine language syntax hint from extension
            ext = ch.file_path.split(".")[-1] if "." in ch.file_path else ""
            lang = {
                "py": "python",
                "ts": "typescript",
                "tsx": "typescript",
                "js": "javascript",
                "jsx": "javascript",
                "go": "go",
                "rs": "rust",
                "java": "java",
            }.get(ext, "")

            block = f"{header}\n```{lang}\n{ch.content}\n```"
            blocks.append(block)

        return "\n\n".join(blocks)
