import os
import logging
from typing import Optional
from .base import LLMProvider, EmbeddingProvider, RerankerProvider
from .mock_provider import MockLLMProvider, MockEmbeddingProvider, MockRerankerProvider
from .gemini_provider import GeminiLLMProvider, GeminiEmbeddingProvider
from .openai_provider import OpenAILLMProvider, OpenAIEmbeddingProvider

logger = logging.getLogger(__name__)


def get_llm_provider(provider_type: Optional[str] = None, api_key: Optional[str] = None, model: Optional[str] = None) -> LLMProvider:
    """Factory returning configured LLMProvider."""
    p_type = (provider_type or os.getenv("LLM_PROVIDER", "gemini")).lower()

    if p_type == "mock":
        return MockLLMProvider(model_name=model or "mock-llm")

    if p_type == "gemini":
        key = api_key or os.getenv("GEMINI_API_KEY", "")
        if not key:
            logger.warning("GEMINI_API_KEY not set. Falling back to MockLLMProvider.")
            return MockLLMProvider(model_name="mock-gemini")
        return GeminiLLMProvider(api_key=key, model=model or os.getenv("GEMINI_LLM_MODEL", "gemini-1.5-flash"))

    if p_type == "openai":
        key = api_key or os.getenv("OPENAI_API_KEY", "")
        if not key:
            logger.warning("OPENAI_API_KEY not set. Falling back to MockLLMProvider.")
            return MockLLMProvider(model_name="mock-openai")
        return OpenAILLMProvider(api_key=key, model=model or os.getenv("OPENAI_LLM_MODEL", "gpt-4o-mini"))

    raise ValueError(f"Unknown LLM provider: '{p_type}'. Supported: gemini, openai, mock.")


def get_embedding_provider(provider_type: Optional[str] = None, api_key: Optional[str] = None, model: Optional[str] = None) -> EmbeddingProvider:
    """Factory returning configured EmbeddingProvider."""
    p_type = (provider_type or os.getenv("EMBEDDING_PROVIDER", "gemini")).lower()

    if p_type == "mock":
        return MockEmbeddingProvider()

    if p_type == "gemini":
        key = api_key or os.getenv("GEMINI_API_KEY", "")
        if not key:
            logger.warning("GEMINI_API_KEY not set. Falling back to MockEmbeddingProvider.")
            return MockEmbeddingProvider(dimension=768)
        return GeminiEmbeddingProvider(api_key=key, model=model or os.getenv("GEMINI_EMBEDDING_MODEL", "text-embedding-004"))

    if p_type == "openai":
        key = api_key or os.getenv("OPENAI_API_KEY", "")
        if not key:
            logger.warning("OPENAI_API_KEY not set. Falling back to MockEmbeddingProvider.")
            return MockEmbeddingProvider(dimension=1536)
        return OpenAIEmbeddingProvider(api_key=key, model=model or os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"))

    raise ValueError(f"Unknown Embedding provider: '{p_type}'. Supported: gemini, openai, mock.")


def get_reranker_provider(provider_type: Optional[str] = None) -> RerankerProvider:
    """Factory returning configured RerankerProvider."""
    p_type = (provider_type or os.getenv("RERANKER_PROVIDER", "mock")).lower()

    if p_type in ("mock", "cross-encoder", "sentence-transformers"):
        # For Milestone 1 foundation, MockRerankerProvider provides instant zero-dependency execution
        return MockRerankerProvider()

    raise ValueError(f"Unknown Reranker provider: '{p_type}'. Supported: mock.")


class AIProviderFactory:
    """Unified factory class for creating AI providers."""

    @staticmethod
    def create_llm_provider(provider_name: Optional[str] = None, api_key: Optional[str] = None, model_name: Optional[str] = None) -> LLMProvider:
        return get_llm_provider(provider_type=provider_name, api_key=api_key, model=model_name)

    @staticmethod
    def create_embedding_provider(provider_name: Optional[str] = None, api_key: Optional[str] = None, model_name: Optional[str] = None) -> EmbeddingProvider:
        return get_embedding_provider(provider_type=provider_name, api_key=api_key, model=model_name)

    @staticmethod
    def create_reranker_provider(provider_name: Optional[str] = None, api_key: Optional[str] = None, model_name: Optional[str] = None) -> RerankerProvider:
        return get_reranker_provider(provider_type=provider_name)
