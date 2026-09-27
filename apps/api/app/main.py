from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

from .config import settings
from .core.logging import setup_logging
from .core.errors import register_error_handlers
from .core.middleware import ObservabilityMiddleware
from .api.v1 import v1_router
from .api.v1.health import router as health_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle events: startup and shutdown."""
    setup_logging(settings.LOG_LEVEL)
    logger.info(f"Starting CodeAtlas API Gateway [{settings.ENVIRONMENT}]")
    logger.info(f"Database target: {settings.DATABASE_URL.split('@')[-1] if '@' in settings.DATABASE_URL else 'configured'}")
    logger.info(f"Active LLM provider: {settings.LLM_PROVIDER} | Embedding: {settings.EMBEDDING_PROVIDER}")

    # Ensure all tables are created
    from .database import async_engine, async_session_factory, Base
    from .models import User  # Ensure models are imported
    from .services.auth_service import AuthService
    from sqlalchemy import select

    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Seed default admin user if not present
    async with async_session_factory() as session:
        result = await session.execute(select(User).where(User.email == "admin@codeatlas.dev"))
        if not result.scalar_one_or_none():
            try:
                await AuthService.register_user(
                    session=session,
                    email="admin@codeatlas.dev",
                    password="admin123456",
                    full_name="Enterprise Admin",
                    role="ADMIN",
                )
                await session.commit()
                logger.info("Initialized default administrator account: admin@codeatlas.dev")
            except Exception as e:
                logger.warning(f"Admin auto-seed skipped or failed: {e}")

    yield

    logger.info("Shutting down CodeAtlas API Gateway")


def create_application() -> FastAPI:
    """FastAPI Application Factory."""
    app = FastAPI(
        title="CodeAtlas API",
        description="Enterprise AI-powered Code Intelligence & Software Engineering Platform",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # 1. Observability & Correlation Middleware
    app.add_middleware(ObservabilityMiddleware)

    # 2. Cross-Origin Resource Sharing (CORS)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )

    # 3. Standardized RFC 7807 Error Handlers
    register_error_handlers(app)

    # 4. Prometheus Metrics Endpoint
    @app.get("/metrics", tags=["Observability"], include_in_schema=False)
    def metrics():
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

    # 5. Root Liveness Probe (for container orchestration)
    app.include_router(health_router)

    # 6. API v1 Routers
    app.include_router(v1_router)

    return app


app = create_application()
