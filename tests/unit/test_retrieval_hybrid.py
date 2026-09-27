import pytest
from packages.ai.mock_provider import MockEmbeddingProvider, MockRerankerProvider
from packages.retrieval.bm25 import BM25Index
from packages.retrieval.vector import VectorIndex
from packages.retrieval.reranker import CrossEncoderReranker
from packages.retrieval.hybrid_service import HybridSearchService
from packages.retrieval.models import SearchMode, SearchRequestDTO


@pytest.mark.asyncio
async def test_hybrid_search_orchestration():
    embedding_provider = MockEmbeddingProvider(dimension=64)
    reranker_provider = MockRerankerProvider()

    chunks = [
        {
            "id": "chunk-1",
            "repository_id": "repo-alpha",
            "file_id": "file-1",
            "file_path": "auth/service.py",
            "symbol_name": "login_user",
            "symbol_type": "FUNCTION",
            "content": "def login_user(email: str, password: str):\n    return auth_tokens",
            "start_line": 1,
            "end_line": 5,
        },
        {
            "id": "chunk-2",
            "repository_id": "repo-alpha",
            "file_id": "file-2",
            "file_path": "billing/payment.py",
            "symbol_name": "charge_card",
            "symbol_type": "FUNCTION",
            "content": "def charge_card(card_token: str, amount: int):\n    return stripe.charge",
            "start_line": 10,
            "end_line": 15,
        },
    ]

    bm25 = BM25Index(chunks)
    vector = VectorIndex(embedding_provider=embedding_provider, prefer_memory_fallback=True)
    await vector.upsert_chunks("repo-alpha", "commit-123", chunks)
    reranker = CrossEncoderReranker(reranker_provider)

    service = HybridSearchService(
        bm25_index=bm25,
        vector_index=vector,
        reranker=reranker,
    )

    # 1. Test HYBRID search with reranking
    req_hybrid = SearchRequestDTO(query="login_user auth_tokens", mode=SearchMode.HYBRID, top_k=5, rerank=True)
    res_hybrid = await service.search("repo-alpha", req_hybrid)
    assert res_hybrid.mode == "hybrid"
    assert len(res_hybrid.results) > 0
    assert res_hybrid.results[0].chunk_id == "chunk-1"
    assert res_hybrid.results[0].rerank_score is not None

    # 2. Test LEXICAL search
    req_lexical = SearchRequestDTO(query="charge_card", mode=SearchMode.LEXICAL, top_k=5, rerank=False)
    res_lexical = await service.search("repo-alpha", req_lexical)
    assert res_lexical.mode == "lexical"
    assert len(res_lexical.results) > 0
    assert res_lexical.results[0].chunk_id == "chunk-2"

    # 3. Test SEMANTIC search
    req_semantic = SearchRequestDTO(query="payment billing stripe", mode=SearchMode.SEMANTIC, top_k=5, rerank=False)
    res_semantic = await service.search("repo-alpha", req_semantic)
    assert res_semantic.mode == "semantic"
    assert len(res_semantic.results) > 0

    # 4. Test Filtering by symbol_type
    req_filter = SearchRequestDTO(query="login", mode=SearchMode.HYBRID, symbol_type="CLASS", rerank=False)
    res_filter = await service.search("repo-alpha", req_filter)
    # Neither chunk is a CLASS (both are FUNCTION)
    assert len(res_filter.results) == 0
