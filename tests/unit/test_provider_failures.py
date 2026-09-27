import pytest
import httpx
from packages.ai.gemini_provider import GeminiLLMProvider
from packages.ai.openai_provider import OpenAILLMProvider
from packages.ai.base import (
    ProviderAuthenticationError,
    ProviderRateLimitError,
    ProviderUnavailableError,
    ProviderResponseError,
)


@pytest.mark.asyncio
async def test_gemini_provider_auth_error(monkeypatch):
    async def mock_post(*args, **kwargs):
        req = httpx.Request("POST", "http://test")
        return httpx.Response(401, text="API key not valid", request=req)

    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)

    provider = GeminiLLMProvider(api_key="bad_key")
    with pytest.raises(ProviderAuthenticationError) as exc_info:
        await provider.generate("test prompt")
    assert "API returned HTTP 401" in str(exc_info.value)


@pytest.mark.asyncio
async def test_openai_provider_rate_limit(monkeypatch):
    async def mock_post(*args, **kwargs):
        req = httpx.Request("POST", "http://test")
        return httpx.Response(429, text="Rate limit exceeded", request=req)

    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)

    provider = OpenAILLMProvider(api_key="key")
    with pytest.raises(ProviderRateLimitError) as exc_info:
        await provider.generate("test prompt")
    assert "API returned HTTP 429" in str(exc_info.value)


@pytest.mark.asyncio
async def test_provider_timeout(monkeypatch):
    async def mock_post(*args, **kwargs):
        raise httpx.TimeoutException("Connection timed out")

    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)

    provider = GeminiLLMProvider(api_key="key")
    with pytest.raises(ProviderUnavailableError) as exc_info:
        await provider.generate("test prompt")
    assert "timed out" in str(exc_info.value)
