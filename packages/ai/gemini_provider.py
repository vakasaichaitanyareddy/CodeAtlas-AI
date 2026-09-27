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


def _handle_httpx_error(e: Exception, provider: str = "gemini") -> None:
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


class GeminiLLMProvider(LLMProvider):
    """Google Gemini LLM provider using asynchronous HTTP calls."""
    provider_name: str = "gemini"
    is_mock: bool = False

    def __init__(self, api_key: str, model: str = "gemini-1.5-flash"):
        self.api_key = api_key
        self.model = model
        self.model_name = model
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models"

    async def generate(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 4096,
        **kwargs: Any
    ) -> LLMResponse:
        url = f"{self.base_url}/{self.model}:generateContent?key={self.api_key}"
        payload: Dict[str, Any] = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            }
        }
        if system_instruction:
            payload["systemInstruction"] = {"parts": [{"text": system_instruction}]}

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
                data = resp.json()

            candidate = data.get("candidates", [{}])[0]
            content_parts = candidate.get("content", {}).get("parts", [])
            text = "".join(p.get("text", "") for p in content_parts)
            usage = data.get("usageMetadata", {})

            return LLMResponse(
                content=text,
                prompt_tokens=usage.get("promptTokenCount", 0),
                completion_tokens=usage.get("candidatesTokenCount", 0),
                total_tokens=usage.get("totalTokenCount", 0),
                model_name=self.model,
                metadata={"finish_reason": candidate.get("finishReason")},
            )
        except Exception as e:
            _handle_httpx_error(e, provider="gemini")
            raise

    async def stream(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 4096,
        **kwargs: Any
    ) -> AsyncIterator[str]:
        url = f"{self.base_url}/{self.model}:streamGenerateContent?key={self.api_key}&alt=sse"
        payload: Dict[str, Any] = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            }
        }
        if system_instruction:
            payload["systemInstruction"] = {"parts": [{"text": system_instruction}]}

        try:
            async with httpx.AsyncClient(timeout=90.0) as client:
                async with client.stream("POST", url, json=payload) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data_str = line[6:].strip()
                            if not data_str:
                                continue
                            try:
                                parsed = json.loads(data_str)
                                parts = parsed.get("candidates", [{}])[0].get("content", {}).get("parts", [])
                                for p in parts:
                                    if "text" in p:
                                        yield p["text"]
                            except Exception:
                                continue
        except Exception as e:
            _handle_httpx_error(e, provider="gemini")
            raise


class GeminiEmbeddingProvider(EmbeddingProvider):
    """Google Gemini Embedding provider."""

    def __init__(self, api_key: str, model: str = "text-embedding-004", dimension: int = 768):
        self.api_key = api_key
        self.model = model
        self._dim = dimension
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models"

    @property
    def dimension(self) -> int:
        return self._dim

    async def embed_documents(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        url = f"{self.base_url}/{self.model}:batchEmbedContents?key={self.api_key}"
        requests = [
            {
                "model": f"models/{self.model}",
                "content": {"parts": [{"text": t}]},
                "outputDimensionality": self._dim,
            }
            for t in texts
        ]
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(url, json={"requests": requests})
                resp.raise_for_status()
                data = resp.json()
            embeddings = data.get("embeddings", [])
            return [e.get("values", []) for e in embeddings]
        except Exception as e:
            _handle_httpx_error(e, provider="gemini")
            raise

    async def embed_query(self, text: str) -> List[float]:
        results = await self.embed_documents([text])
        return results[0] if results else []
