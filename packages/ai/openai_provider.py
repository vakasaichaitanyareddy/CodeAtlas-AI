import json
import logging
from typing import List, Dict, Any, AsyncIterator, Optional
import httpx
from .base import (
    LLMProvider,
    EmbeddingProvider,
    LLMResponse,
    ProviderAuthenticationError,
    ProviderRateLimitError,
    ProviderUnavailableError,
    ProviderResponseError,
)

logger = logging.getLogger(__name__)


def _handle_openai_error(e: Exception, provider: str = "openai") -> None:
    """Translate HTTPX transport or status errors into standard ProviderErrors."""
    if isinstance(e, httpx.HTTPStatusError):
        code = e.response.status_code
        msg = f"{provider.capitalize()} API returned HTTP {code}: {e.response.text}"
        if code in (401, 403):
            raise ProviderAuthenticationError(msg, provider=provider, status_code=code) from e
        elif code == 429:
            raise ProviderRateLimitError(msg, provider=provider, status_code=code) from e
        elif code >= 500:
            raise ProviderUnavailableError(msg, provider=provider, status_code=code) from e
        else:
            raise ProviderResponseError(msg, provider=provider, status_code=code) from e
    elif isinstance(e, (httpx.TimeoutException, httpx.NetworkError, httpx.ConnectError)):
        raise ProviderUnavailableError(f"{provider.capitalize()} service unreachable or timed out: {e}", provider=provider) from e
    elif isinstance(e, (KeyError, IndexError, json.JSONDecodeError)):
        raise ProviderResponseError(f"Failed to parse {provider.capitalize()} response: {e}", provider=provider) from e
    raise e


class OpenAILLMProvider(LLMProvider):
    """OpenAI-compatible LLM provider."""
    provider_name: str = "openai"
    is_mock: bool = False

    def __init__(self, api_key: str, model: str = "gpt-4o-mini", base_url: str = "https://api.openai.com/v1"):
        self.api_key = api_key
        self.model = model
        self.model_name = model
        self.base_url = base_url.rstrip("/")

    async def generate(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 4096,
        **kwargs: Any
    ) -> LLMResponse:
        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": prompt})

        headers = {"Authorization": f"Bearer {self.api_key}"}
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(f"{self.base_url}/chat/completions", headers=headers, json=payload)
                resp.raise_for_status()
                data = resp.json()

            choice = data.get("choices", [{}])[0]
            text = choice.get("message", {}).get("content", "")
            usage = data.get("usage", {})

            return LLMResponse(
                content=text,
                prompt_tokens=usage.get("prompt_tokens", 0),
                completion_tokens=usage.get("completion_tokens", 0),
                total_tokens=usage.get("total_tokens", 0),
                model_name=self.model,
                metadata={"finish_reason": choice.get("finish_reason")},
            )
        except Exception as e:
            _handle_openai_error(e, provider="openai")
            raise

    async def stream(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 4096,
        **kwargs: Any
    ) -> AsyncIterator[str]:
        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": prompt})

        headers = {"Authorization": f"Bearer {self.api_key}"}
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }

        try:
            async with httpx.AsyncClient(timeout=90.0) as client:
                async with client.stream("POST", f"{self.base_url}/chat/completions", headers=headers, json=payload) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data_str = line[6:].strip()
                            if data_str == "[DONE]":
                                break
                            if not data_str:
                                continue
                            try:
                                parsed = json.loads(data_str)
                                delta = parsed.get("choices", [{}])[0].get("delta", {})
                                chunk = delta.get("content", "")
                                if chunk:
                                    yield chunk
                            except Exception:
                                continue
        except Exception as e:
            _handle_openai_error(e, provider="openai")
            raise


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """OpenAI-compatible Embedding provider."""

    def __init__(self, api_key: str, model: str = "text-embedding-3-small", dimension: int = 1536, base_url: str = "https://api.openai.com/v1"):
        self.api_key = api_key
        self.model = model
        self._dim = dimension
        self.base_url = base_url.rstrip("/")

    @property
    def dimension(self) -> int:
        return self._dim

    async def embed_documents(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        headers = {"Authorization": f"Bearer {self.api_key}"}
        payload = {
            "model": self.model,
            "input": texts,
        }
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(f"{self.base_url}/embeddings", headers=headers, json=payload)
                resp.raise_for_status()
                data = resp.json()
            items = sorted(data.get("data", []), key=lambda x: x["index"])
            return [item["embedding"] for item in items]
        except Exception as e:
            _handle_openai_error(e, provider="openai")
            raise

    async def embed_query(self, text: str) -> List[float]:
        results = await self.embed_documents([text])
        return results[0] if results else []
