from datetime import datetime, timezone, timedelta
from typing import Tuple, Optional
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from ..models.user import User, RefreshToken
from ..core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_token,
)
from ..core.errors import APIError
from ..config import settings


class AuthService:
    """Enterprise authentication service managing credentials and token lifecycles."""

    @staticmethod
    async def register_user(
        session: AsyncSession,
        email: str,
        password: str,
        full_name: Optional[str] = None,
        role: str = "USER",
    ) -> User:
        # Check if email is already registered
        stmt = select(User).where(User.email == email.lower())
        result = await session.execute(stmt)
        if result.scalar_one_or_none():
            raise APIError(
                message=f"An account with email '{email}' already exists.",
                code="USER_ALREADY_EXISTS",
                status_code=409,
            )

        hashed = hash_password(password)
        user = User(
            email=email.lower(),
            hashed_password=hashed,
            full_name=full_name,
            role=role,
            is_active=True,
        )
        session.add(user)
        await session.flush()
        return user

    @staticmethod
    async def authenticate_user(
        session: AsyncSession,
        email: str,
        password: str,
    ) -> User:
        stmt = select(User).where(User.email == email.lower())
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

        if not user or not verify_password(password, user.hashed_password):
            raise APIError(
                message="Invalid email or password.",
                code="INVALID_CREDENTIALS",
                status_code=401,
            )

        if not user.is_active:
            raise APIError(
                message="This account has been deactivated.",
                code="ACCOUNT_INACTIVE",
                status_code=403,
            )

        return user

    @staticmethod
    async def create_tokens_for_user(
        session: AsyncSession,
        user: User,
    ) -> Tuple[str, str, int]:
        access_token = create_access_token(subject=user.id, role=user.role)
        refresh_token = create_refresh_token(subject=user.id)

        token_h = hash_token(refresh_token)
        expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

        db_refresh = RefreshToken(
            user_id=user.id,
            token_hash=token_h,
            expires_at=expires_at,
            revoked=False,
        )
        session.add(db_refresh)
        await session.flush()

        expires_in = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        return access_token, refresh_token, expires_in

    @staticmethod
    async def refresh_access_token(
        session: AsyncSession,
        refresh_token: str,
    ) -> Tuple[str, str, int]:
        try:
            payload = decode_token(refresh_token)
            if payload.get("type") != "refresh":
                raise ValueError("Token is not a refresh token")
            user_id = payload.get("sub")
        except Exception:
            raise APIError(
                message="Invalid or expired refresh token.",
                code="INVALID_REFRESH_TOKEN",
                status_code=401,
            )

        token_h = hash_token(refresh_token)
        stmt = select(RefreshToken).where(
            RefreshToken.token_hash == token_h,
            RefreshToken.user_id == user_id,
            RefreshToken.revoked == False,
        )
        res = await session.execute(stmt)
        token_record = res.scalar_one_or_none()

        if not token_record:
            raise APIError(
                message="Refresh token has been revoked or expired.",
                code="REFRESH_TOKEN_REVOKED",
                status_code=401,
            )

        # Ensure datetime comparison handles both naive (SQLite) and aware (Postgres) datetimes
        token_expires = token_record.expires_at
        if token_expires.tzinfo is None:
            token_expires = token_expires.replace(tzinfo=timezone.utc)

        if token_expires < datetime.now(timezone.utc):
            raise APIError(
                message="Refresh token has been revoked or expired.",
                code="REFRESH_TOKEN_REVOKED",
                status_code=401,
            )

        # Token rotation: revoke old token and issue new pair
        token_record.revoked = True

        user_stmt = select(User).where(User.id == user_id)
        user_res = await session.execute(user_stmt)
        user = user_res.scalar_one_or_none()
        if not user or not user.is_active:
            raise APIError(
                message="User associated with token no longer active.",
                code="USER_INACTIVE",
                status_code=401,
            )

        return await AuthService.create_tokens_for_user(session, user)

    @staticmethod
    async def revoke_refresh_token(session: AsyncSession, refresh_token: str) -> None:
        token_h = hash_token(refresh_token)
        stmt = update(RefreshToken).where(RefreshToken.token_hash == token_h).values(revoked=True)
        await session.execute(stmt)

    @staticmethod
    async def get_user_by_id(session: AsyncSession, user_id: str) -> Optional[User]:
        stmt = select(User).where(User.id == user_id)
        res = await session.execute(stmt)
        return res.scalar_one_or_none()
