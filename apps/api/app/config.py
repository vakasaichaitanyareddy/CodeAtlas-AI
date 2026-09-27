from typing import List, Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """CodeAtlas Enterprise Configuration via Pydantic Settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Core
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"
    SECRET_KEY: str = Field(
        default="codeatlas-insecure-secret-key-change-in-production-min-32-chars",
        description="Cryptographic secret key for signing JWTs",
    )
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    # PostgreSQL 16
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://codeatlas:codeatlas_secret@localhost:5432/codeatlas_db",
        description="Async SQLAlchemy database URL (e.g. postgresql+asyncpg://...)",
    )
    DATABASE_SYNC_URL: Optional[str] = Field(
        default="postgresql://codeatlas:codeatlas_secret@localhost:5432/codeatlas_db",
        description="Synchronous database URL used by Alembic migrations",
    )
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_TIMEOUT: int = 30
    DB_ECHO: bool = False

    # Redis 7
    REDIS_URL: str = "redis://localhost:6379/0"

    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    # Qdrant
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_API_KEY: Optional[str] = None
    QDRANT_COLLECTION_NAME: str = "codeatlas_chunks"

    # JWT Authentication
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # AI Model Providers
    LLM_PROVIDER: str = "gemini"
    EMBEDDING_PROVIDER: str = "gemini"
    RERANKER_PROVIDER: str = "mock"
    RERANKER_MODEL: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"

    # Gemini
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_LLM_MODEL: str = "gemini-1.5-flash"
    GEMINI_EMBEDDING_MODEL: str = "text-embedding-004"

    # OpenAI
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_LLM_MODEL: str = "gpt-4o-mini"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"

    # GitHub
    GITHUB_CLIENT_ID: Optional[str] = None
    GITHUB_CLIENT_SECRET: Optional[str] = None
    GITHUB_WEBHOOK_SECRET: Optional[str] = None
    GITHUB_PERSONAL_ACCESS_TOKEN: Optional[str] = None

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v):
        if isinstance(v, str):
            return [i.strip() for i in v.split(",") if i.strip()]
        return v

    def validate_production_security(self) -> "Settings":
        if self.ENVIRONMENT.lower() == "production":
            if "change-in-production" in self.SECRET_KEY or len(self.SECRET_KEY) < 32:
                raise ValueError("In production, SECRET_KEY must be a cryptographically secure random string with at least 32 characters.")
            if "*" in self.ALLOWED_ORIGINS:
                raise ValueError("In production, ALLOWED_ORIGINS cannot contain wildcard '*' when allow_credentials is enabled.")
        return self


settings = Settings().validate_production_security()
