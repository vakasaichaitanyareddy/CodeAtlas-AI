from fastapi import APIRouter
from .auth import router as auth_router
from .repositories import router as repositories_router
from .health import router as health_router
from .chat import router as chat_router

v1_router = APIRouter(prefix="/api/v1")
v1_router.include_router(auth_router)
v1_router.include_router(repositories_router)
v1_router.include_router(chat_router)
v1_router.include_router(health_router)

__all__ = ["v1_router"]
