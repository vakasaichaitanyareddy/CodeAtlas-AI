import time
import logging
from typing import List, Dict, Any, Optional, AsyncIterator, Tuple
from .models import (
    QueryIntent,
    QueryAnalysis,
    ContextPack,
    GroundedAnswer,
    GroundingStatus,
    CitationValidationResult,
)
from .classifier import QueryClassifier
from .context import ContextAssembler
from .citations import CitationVerifier
from packages.ai.base import LLMProvider
from packages.retrieval.hybrid_service import HybridSearchService
from packages.retrieval.models import SearchMode, SearchRequestDTO, ScoredChunkDTO

logger = logging.getLogger("codeatlas.rag.engine")


INSUFFICIENT_EVIDENCE_MESSAGE = "I couldn't find enough evidence in the indexed repository to answer this reliably."


GROUNDED_SYSTEM_INSTRUCTION = """You are CodeAtlas, an expert AI software architect and codebase intelligence assistant.

CRITICAL GROUNDING RULES:
1. Ground every claim strictly in the provided codebase context snippets below.
2. DO NOT fabricate APIs, functions, classes, file names, or behaviors that are not present in the evidence.
3. Every time you reference code, a function, a class, an endpoint, or an implementation, you MUST cite the source file and line range in the exact bracketed format: [filepath:Lstart-Lend] (e.g. [apps/api/app/main.py:L15-L35]).
4. If the provided code snippets do not contain enough information to answer the question, state clearly: "I couldn't find enough evidence in the indexed repository to answer this reliably."
5. Be concise, technically precise, and directly address the user's intent.
"""


class RAGEngine:
    """End-to-end Grounded Retrieval-Augmented Generation engine for codebases."""

    def __init__(
        self,
        llm_provider: LLMProvider,
        hybrid_search_service: HybridSearchService,
        classifier: Optional[QueryClassifier] = None,
        context_assembler: Optional[ContextAssembler] = None,
        citation_verifier: Optional[CitationVerifier] = None,
        insufficient_evidence_message: str = INSUFFICIENT_EVIDENCE_MESSAGE,
    ):
        self.llm_provider = llm_provider
        self.hybrid_search = hybrid_search_service
        self.classifier = classifier or QueryClassifier()
        self.assembler = context_assembler or ContextAssembler()
        self.citation_verifier = citation_verifier or CitationVerifier()
        self.insufficient_evidence_message = insufficient_evidence_message

    def _get_provider_metadata(self) -> Tuple[str, str, bool]:
        """Safely extract provider metadata, handling mocks gracefully."""
        p_name = getattr(self.llm_provider, "provider_name", None)
        if not isinstance(p_name, str):
            p_name = "mock"

        m_name = getattr(self.llm_provider, "model_name", None)
        if not isinstance(m_name, str):
            m_name = "mock-llm"

        is_mock_prov = getattr(self.llm_provider, "is_mock", None)
        if not isinstance(is_mock_prov, bool):
            is_mock_prov = True

        return p_name, m_name, is_mock_prov

    async def prepare_context(
        self,
        query: str,
        repository_id: str,
        commit_sha: Optional[str] = None,
        search_mode: SearchMode = SearchMode.HYBRID,
        top_k: int = 10,
        rerank: bool = True,
        graph_context: Optional[List[Dict[str, Any]]] = None,
    ) -> ContextPack:
        """Analyze query, retrieve candidates via hybrid search, and assemble token-budgeted context."""
        analysis = self.classifier.analyze_query(query)

        # Build retrieval request
        req = SearchRequestDTO(
            query=query,
            mode=search_mode,
            top_k=top_k,
            rerank=rerank,
            file_pattern=analysis.file_patterns[0] if analysis.file_patterns else None,
            symbol_type=None,
        )

        search_result = await self.hybrid_search.search(
            repository_id=repository_id,
            request=req,
            commit_sha=commit_sha,
        )

        candidates = list(search_result.results)

        # Graph Context Post-Retrieval Expansion for ARCHITECTURE / PROCESS / DEPENDENCY queries
        if graph_context and analysis.intent in (QueryIntent.ARCHITECTURE, QueryIntent.DEPENDENCY):
            adj = getattr(graph_context, "adjacency", None)
            if adj is None and isinstance(graph_context, dict):
                adj = graph_context.get("adjacency", {})

            if adj:
                seed_symbols = [
                    c.symbol_name for c in candidates
                    if c.symbol_name and not (c.file_path.startswith("tests/") or "changes" in c.file_path.lower())
                ][:4]

                neighbor_pairs = set()
                for sym in seed_symbols:
                    for rel in adj.get(sym, []):
                        n_sym = rel.get("neighbor_symbol")
                        n_file = rel.get("neighbor_file")
                        if n_sym and n_file and not (n_file.startswith("tests/") or n_sym.endswith(".py") or len(n_sym) < 3):
                            neighbor_pairs.add((n_sym, n_file))

                # Match neighbor symbols against indexed chunks in bm25_index
                existing_ids = {c.chunk_id for c in candidates}
                for n_sym, n_file in neighbor_pairs:
                    for chunk in getattr(self.hybrid_search.bm25_index, "chunks", []):
                        if (
                            chunk.get("id") not in existing_ids
                            and chunk.get("file_path") == n_file
                            and chunk.get("symbol_name") == n_sym
                        ):
                            candidates.append(
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
                                    score=0.5,
                                    metadata={"source": "graph", "is_graph_neighbor": True},
                                )
                            )
                            existing_ids.add(chunk["id"])

                # Rerank the expanded candidate pool
                if rerank and self.hybrid_search.reranker and candidates:
                    candidates = await self.hybrid_search.reranker.rerank(
                        query=query,
                        candidates=candidates,
                        top_k=max(top_k, 5),
                    )

        raw_graph_list = (
            graph_context
            if isinstance(graph_context, list)
            else (graph_context.get("edges", []) if isinstance(graph_context, dict) else [])
        )

        return self.assembler.assemble_context(
            analysis=analysis,
            scored_candidates=candidates,
            graph_context=raw_graph_list,
        )

    async def generate_answer(
        self,
        query: str,
        repository_id: str,
        commit_sha: Optional[str] = None,
        search_mode: SearchMode = SearchMode.HYBRID,
        top_k: int = 10,
        rerank: bool = True,
        graph_context: Optional[List[Dict[str, Any]]] = None,
        file_records: Optional[Dict[str, Dict[str, Any]]] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> GroundedAnswer:
        """Synchronously generate a grounded answer with verified citations."""
        start_time = time.perf_counter()

        # Step 1 & 2: Analyze & Assemble Context
        context_pack = await self.prepare_context(
            query=query,
            repository_id=repository_id,
            commit_sha=commit_sha,
            search_mode=search_mode,
            top_k=top_k,
            rerank=rerank,
            graph_context=graph_context,
        )

        p_name, m_name, is_mock_prov = self._get_provider_metadata()

        # Step 3: Hard Insufficient-Evidence Fallback Gate
        if not context_pack.evidence.evidence_threshold_met:
            latency_ms = int((time.perf_counter() - start_time) * 1000)
            return GroundedAnswer(
                answer=self.insufficient_evidence_message,
                grounding_status=GroundingStatus.UNSUPPORTED,
                intent=context_pack.analysis.intent,
                citations=[],
                context_chunks=context_pack.chunks,
                retrieval_evidence=context_pack.evidence,
                provider=p_name,
                model_name=m_name,
                is_mock=is_mock_prov,
                prompt_tokens=0,
                completion_tokens=len(self.insufficient_evidence_message) // 4,
                latency_ms=latency_ms,
            )

        # Step 4: Construct Grounded Prompt
        context_block = ContextAssembler.format_context_for_prompt(context_pack)
        user_prompt = f"User Question: {query}\n\n=== Codebase Context Snippets ===\n{context_block}\n\nProvide a clear, grounded answer with exact [filepath:Lstart-Lend] citations."

        # Include recent conversation turns if provided
        if conversation_history:
            history_blocks = []
            for msg in conversation_history[-4:]:  # last 2 turns
                history_blocks.append(f"{msg.get('role', 'user').upper()}: {msg.get('content', '')}")
            if history_blocks:
                user_prompt = "=== Conversation History ===\n" + "\n".join(history_blocks) + "\n\n" + user_prompt

        # Step 5: LLM Generation
        llm_resp = await self.llm_provider.generate(
            prompt=user_prompt,
            system_instruction=GROUNDED_SYSTEM_INSTRUCTION,
            temperature=0.2,
        )

        answer_text = llm_resp.content

        # Step 6: Multi-Stage Citation Validation
        file_map = file_records or {}
        raw_citations = self.citation_verifier.extract_citations(answer_text)
        validated_citations = self.citation_verifier.validate_citations(
            citations=raw_citations,
            context_pack=context_pack,
            file_records=file_map,
        )

        grounding_status = self.citation_verifier.compute_grounding_status(
            validation_results=validated_citations,
            context_pack=context_pack,
            answer_text=answer_text,
        )

        latency_ms = int((time.perf_counter() - start_time) * 1000)

        return GroundedAnswer(
            answer=answer_text,
            grounding_status=grounding_status,
            intent=context_pack.analysis.intent,
            citations=validated_citations,
            context_chunks=context_pack.chunks,
            retrieval_evidence=context_pack.evidence,
            provider=p_name,
            model_name=m_name,
            is_mock=is_mock_prov,
            prompt_tokens=llm_resp.prompt_tokens or context_pack.total_tokens,
            completion_tokens=llm_resp.completion_tokens or len(answer_text) // 4,
            latency_ms=latency_ms,
        )

    async def stream_answer(
        self,
        query: str,
        repository_id: str,
        commit_sha: Optional[str] = None,
        search_mode: SearchMode = SearchMode.HYBRID,
        top_k: int = 10,
        rerank: bool = True,
        graph_context: Optional[List[Dict[str, Any]]] = None,
        file_records: Optional[Dict[str, Dict[str, Any]]] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> AsyncIterator[Tuple[str, Optional[GroundedAnswer]]]:
        """Stream token deltas, yielding (token_delta, final_grounded_answer)."""
        start_time = time.perf_counter()

        context_pack = await self.prepare_context(
            query=query,
            repository_id=repository_id,
            commit_sha=commit_sha,
            search_mode=search_mode,
            top_k=top_k,
            rerank=rerank,
            graph_context=graph_context,
        )

        p_name, m_name, is_mock_prov = self._get_provider_metadata()

        # Check Insufficient Evidence Fallback
        if not context_pack.evidence.evidence_threshold_met:
            latency_ms = int((time.perf_counter() - start_time) * 1000)
            final_answer = GroundedAnswer(
                answer=self.insufficient_evidence_message,
                grounding_status=GroundingStatus.UNSUPPORTED,
                intent=context_pack.analysis.intent,
                citations=[],
                context_chunks=context_pack.chunks,
                retrieval_evidence=context_pack.evidence,
                provider=p_name,
                model_name=m_name,
                is_mock=is_mock_prov,
                prompt_tokens=0,
                completion_tokens=len(self.insufficient_evidence_message) // 4,
                latency_ms=latency_ms,
            )
            yield self.insufficient_evidence_message, final_answer
            return

        context_block = ContextAssembler.format_context_for_prompt(context_pack)
        user_prompt = f"User Question: {query}\n\n=== Codebase Context Snippets ===\n{context_block}\n\nProvide a clear, grounded answer with exact [filepath:Lstart-Lend] citations."

        if conversation_history:
            history_blocks = []
            for msg in conversation_history[-4:]:
                history_blocks.append(f"{msg.get('role', 'user').upper()}: {msg.get('content', '')}")
            if history_blocks:
                user_prompt = "=== Conversation History ===\n" + "\n".join(history_blocks) + "\n\n" + user_prompt

        accumulated_tokens: List[str] = []
        async for chunk in self.llm_provider.stream(
            prompt=user_prompt,
            system_instruction=GROUNDED_SYSTEM_INSTRUCTION,
            temperature=0.2,
        ):
            accumulated_tokens.append(chunk)
            yield chunk, None

        full_answer = "".join(accumulated_tokens)

        # Post-stream validation
        file_map = file_records or {}
        raw_citations = self.citation_verifier.extract_citations(full_answer)
        validated_citations = self.citation_verifier.validate_citations(
            citations=raw_citations,
            context_pack=context_pack,
            file_records=file_map,
        )

        grounding_status = self.citation_verifier.compute_grounding_status(
            validation_results=validated_citations,
            context_pack=context_pack,
            answer_text=full_answer,
        )

        latency_ms = int((time.perf_counter() - start_time) * 1000)

        final_answer = GroundedAnswer(
            answer=full_answer,
            grounding_status=grounding_status,
            intent=context_pack.analysis.intent,
            citations=validated_citations,
            context_chunks=context_pack.chunks,
            retrieval_evidence=context_pack.evidence,
            provider=p_name,
            model_name=m_name,
            is_mock=is_mock_prov,
            prompt_tokens=context_pack.total_tokens,
            completion_tokens=len(full_answer) // 4,
            latency_ms=latency_ms,
        )

        yield "", final_answer
