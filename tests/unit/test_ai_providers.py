import pytest
from packages.ai.base import LLMResponse, RerankResult
from packages.ai.mock_provider import MockLLMProvider, MockEmbeddingProvider, MockRerankerProvider
from packages.ai.factory import get_llm_provider, get_embedding_provider, get_reranker_provider


@pytest.mark.asyncio
async def test_mock_llm_provider_generate():
    provider = MockLLMProvider()
    resp = await provider.generate("How does auth work?", system_instruction="Be concise")
    assert isinstance(resp, LLMResponse)
    assert "Mock response" in resp.content
    assert resp.model_name == "mock-llm"


@pytest.mark.asyncio
async def test_mock_llm_provider_stream():
    provider = MockLLMProvider()
    chunks = []
    async for chunk in provider.stream("How does auth work?"):
        chunks.append(chunk)
    full_text = "".join(chunks)
    assert len(chunks) > 1
    assert "Mock" in full_text


@pytest.mark.asyncio
async def test_mock_embedding_provider():
    provider = MockEmbeddingProvider(dimension=128)
    assert provider.dimension == 128

    query_vec = await provider.embed_query("auth service")
    assert len(query_vec) == 128

    doc_vecs = await provider.embed_documents(["auth service", "payment controller"])
    assert len(doc_vecs) == 2
    assert len(doc_vecs[0]) == 128


@pytest.mark.asyncio
async def test_mock_reranker_provider():
    provider = MockRerankerProvider()
    docs = ["payment processor logic", "auth token validation", "user profile view"]
    results = await provider.rerank(query="auth token", documents=docs, top_k=2)
    assert len(results) == 2
    assert isinstance(results[0], RerankResult)
    # The document with "auth" and "token" should rank highest
    assert results[0].document == "auth token validation"


def test_ai_provider_factory():
    llm = get_llm_provider(provider_type="mock")
    assert isinstance(llm, MockLLMProvider)
    assert llm.provider_name == "mock"
    assert llm.is_mock is True

    embedder = get_embedding_provider(provider_type="mock")
    assert isinstance(embedder, MockEmbeddingProvider)

    reranker = get_reranker_provider(provider_type="mock")
    assert isinstance(reranker, MockRerankerProvider)


def test_ai_provider_factory_real_providers():
    from packages.ai.gemini_provider import GeminiLLMProvider
    from packages.ai.openai_provider import OpenAILLMProvider

    # When API key is provided, instantiate real providers
    gemini_llm = get_llm_provider(provider_type="gemini", api_key="fake-test-key")
    assert isinstance(gemini_llm, GeminiLLMProvider)
    assert gemini_llm.provider_name == "gemini"
    assert gemini_llm.is_mock is False

    openai_llm = get_llm_provider(provider_type="openai", api_key="fake-test-key")
    assert isinstance(openai_llm, OpenAILLMProvider)
    assert openai_llm.provider_name == "openai"
    assert openai_llm.is_mock is False

    # When API key is missing/empty, safely fall back to MockLLMProvider
    fallback_gemini = get_llm_provider(provider_type="gemini", api_key="")
    assert isinstance(fallback_gemini, MockLLMProvider)
    assert fallback_gemini.is_mock is True

    fallback_openai = get_llm_provider(provider_type="openai", api_key="")
    assert isinstance(fallback_openai, MockLLMProvider)
    assert fallback_openai.is_mock is True


@pytest.mark.asyncio
async def test_mock_llm_provider_grounded_synthesis():
    """Verify that MockLLMProvider extracts code snippets and synthesizes verified citations."""
    provider = MockLLMProvider(model_name="mock-llm")
    prompt = (
        "User Question: How does request context work in Flask?\n\n"
        "=== Codebase Context Snippets ===\n"
        "### [Source 1] File: src/flask/ctx.py (Lines 154-206, Symbol: RequestContext [CLASS])\n"
        "```python\n"
        "class RequestContext:\n"
        "    def __init__(self, app, environ, request=None, session=None):\n"
        "        self.app = app\n"
        "```\n\n"
        "### [Source 2] File: docs/design.rst (Lines 136-229, Symbol: Context Design [SECTION])\n"
        "```rst\n"
        "The Request Context\n"
        "-------------------\n"
        "```\n\n"
        "Provide a clear, grounded answer with exact [filepath:Lstart-Lend] citations."
    )

    resp = await provider.generate(prompt)
    assert isinstance(resp, LLMResponse)
    # Must contain citations referencing the provided snippets
    assert "[src/flask/ctx.py:L154-L206]" in resp.content
    assert "[docs/design.rst:L136-L229]" in resp.content
    # Must disclose offline baseline mode
    assert "Offline Baseline Mode" in resp.content
