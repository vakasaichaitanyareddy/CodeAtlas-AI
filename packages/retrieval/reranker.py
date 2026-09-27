from typing import List
from packages.ai.base import RerankerProvider
from .models import ScoredChunkDTO


class CrossEncoderReranker:
    """Reranks retrieved candidate chunks using a deep cross-encoder model."""

    def __init__(self, provider: RerankerProvider):
        self.provider = provider

    async def rerank(
        self,
        query: str,
        candidates: List[ScoredChunkDTO],
        top_k: int = 10,
    ) -> List[ScoredChunkDTO]:
        """Score each candidate against the query and re-order the top-k results."""
        if not candidates or not query.strip():
            return candidates[:top_k]

        docs = [c.content for c in candidates]
        meta_list = [
            {
                "file_path": c.file_path,
                "symbol_name": c.symbol_name,
                "symbol_type": c.symbol_type,
                "start_line": c.start_line,
                "end_line": c.end_line,
            }
            for c in candidates
        ]
        results = await self.provider.rerank(
            query=query,
            documents=docs,
            top_k=top_k,
            metadata_list=meta_list,
        )

        reranked: List[ScoredChunkDTO] = []
        for res in results:
            if res.index < len(candidates):
                candidate = candidates[res.index]
                candidate.rerank_score = round(res.score, 4)
                candidate.score = round(res.score, 4)
                reranked.append(candidate)

        return reranked
