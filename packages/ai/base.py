from abc import ABC, abstractmethod
from typing import List, Dict, Any, AsyncIterator, Optional
from pydantic import BaseModel


class ProviderError(Exception):
    """Base exception for all AI model provider errors."""
    def __init__(self, message: str, provider: str, status_code: Optional[int] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.provider = provider
        self.status_code = status_code
        self.details = details or {}


class ProviderAuthenticationError(ProviderError):
    """Raised when provider API key is invalid or unauthorized."""
    pass


class ProviderRateLimitError(ProviderError):
    """Raised when provider quotas or rate limits are exceeded."""
    pass


class ProviderUnavailableError(ProviderError):
    """Raised when provider service is unreachable, timed out, or returning 5xx."""
    pass


class ProviderResponseError(ProviderError):
    """Raised when provider response format is malformed or empty."""
    pass


class LLMResponse(BaseModel):
    content: str
    prompt_tokens: Optional[int] = 0
    completion_tokens: Optional[int] = 0
    total_tokens: Optional[int] = 0
    model_name: str
    metadata: Dict[str, Any] = {}


class RerankResult(BaseModel):
    index: int
    score: float
    document: str
    metadata: Dict[str, Any] = {}


class LLMProvider(ABC):
    """Abstract interface for Large Language Model providers."""
    provider_name: str = "unknown"
    model_name: str = "unknown"
    is_mock: bool = False

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 4096,
        **kwargs: Any
    ) -> LLMResponse:
        """Generate a complete text response."""
        pass

    @abstractmethod
    async def stream(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 4096,
        **kwargs: Any
    ) -> AsyncIterator[str]:
        """Stream chunks of the text response."""
        pass


class EmbeddingProvider(ABC):
    """Abstract interface for dense vector embedding models."""

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Dimension size of the emitted vectors."""
        pass

    @abstractmethod
    async def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Compute embeddings for a batch of documents/chunks."""
        pass

    @abstractmethod
    async def embed_query(self, text: str) -> List[float]:
        """Compute embedding for a single search query."""
        pass


class RerankerProvider(ABC):
    """Abstract interface for document reranking models."""

    @abstractmethod
    async def rerank(
        self,
        query: str,
        documents: List[str],
        top_k: Optional[int] = None,
        metadata_list: Optional[List[Dict[str, Any]]] = None,
    ) -> List[RerankResult]:
        """Rerank candidates based on semantic relevance to query."""
        pass
