from typing import Callable, Optional
from fastapi import Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from .database import get_db_session
from .core.security import decode_token
from .core.errors import APIError
from .models.user import User
from .services.auth_service import AuthService

security_bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer),
    session: AsyncSession = Depends(get_db_session),
) -> User:
    """Extract and validate JWT access token from Authorization header."""
    if not credentials:
        raise APIError(
            message="Authentication credentials were not provided.",
            code="AUTHENTICATION_REQUIRED",
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    token = credentials.credentials
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            raise ValueError("Token is not an access token")
        user_id = payload.get("sub")
        if not user_id:
            raise ValueError("Missing subject in token payload")
    except Exception as e:
        raise APIError(
            message="Invalid or expired access token.",
            code="INVALID_TOKEN",
            status_code=status.HTTP_401_UNAUTHORIZED,
            details={"error": str(e)},
        )

    user = await AuthService.get_user_by_id(session, user_id)
    if not user:
        raise APIError(
            message="User account no longer exists.",
            code="USER_NOT_FOUND",
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    if not user.is_active:
        raise APIError(
            message="User account is deactivated.",
            code="ACCOUNT_INACTIVE",
            status_code=status.HTTP_403_FORBIDDEN,
        )

    return user


def require_role(required_role: str) -> Callable:
    """Factory dependency enforcing RBAC role checks (e.g. ADMIN)."""
    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role != required_role:
            raise APIError(
                message=f"Access denied. Requires '{required_role}' privileges.",
                code="FORBIDDEN_INSUFFICIENT_ROLE",
                status_code=status.HTTP_403_FORBIDDEN,
            )
        return current_user

    return role_checker
