import httpx
from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from ...database import ping_db
from ...config import settings
import redis.asyncio as aioredis

router = APIRouter(tags=["Health"])


@router.get("/health", status_code=status.HTTP_200_OK)
async def liveness():
    """Liveness probe: verifies process is alive and responsive."""
    return {"status": "ok", "service": "codeatlas-api"}


async def check_redis_health() -> str:
    try:
        r = aioredis.from_url(settings.REDIS_URL, socket_timeout=2.0)
        await r.ping()
        await r.aclose()
        return "healthy"
    except Exception:
        return "unreachable"


async def check_qdrant_health() -> str:
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.get(f"{settings.QDRANT_URL}/readyz")
            return "healthy" if resp.status_code == 200 else f"status_{resp.status_code}"
    except Exception:
        return "unreachable"


@router.get("/health/ready")
async def readiness():
    """Readiness probe: validates connectivity to PostgreSQL, Redis, and Qdrant."""
    checks = {
        "postgres": "healthy" if await ping_db() else "unreachable",
        "redis": await check_redis_health(),
        "qdrant": await check_qdrant_health(),
    }

    all_healthy = all(status == "healthy" for status in checks.values())
    http_status = status.HTTP_200_OK if all_healthy else status.HTTP_503_SERVICE_UNAVAILABLE

    return JSONResponse(
        status_code=http_status,
        content={
            "status": "ready" if all_healthy else "degraded",
            "dependencies": checks,
        },
    )
