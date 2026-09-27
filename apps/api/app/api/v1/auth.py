from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from ...database import get_db_session
from ...schemas.auth import (
    UserRegisterRequest,
    UserLoginRequest,
    RefreshTokenRequest,
    TokenResponse,
    UserResponse,
    AuthResponse,
)
from ...services.auth_service import AuthService
from ...dependencies import get_current_user
from ...models.user import User

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: UserRegisterRequest,
    session: AsyncSession = Depends(get_db_session),
):
    """Register a new user account and return JWT credentials."""
    user = await AuthService.register_user(
        session=session,
        email=request.email,
        password=request.password,
        full_name=request.full_name,
    )
    access_token, refresh_token, expires_in = await AuthService.create_tokens_for_user(session, user)
    await session.commit()

    return AuthResponse(
        user=UserResponse.model_validate(user),
        tokens=TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=expires_in,
        ),
    )


@router.post("/login", response_model=AuthResponse)
async def login(
    request: UserLoginRequest,
    session: AsyncSession = Depends(get_db_session),
):
    """Authenticate user with email/password and issue JWT tokens."""
    user = await AuthService.authenticate_user(
        session=session,
        email=request.email,
        password=request.password,
    )
    access_token, refresh_token, expires_in = await AuthService.create_tokens_for_user(session, user)

    return AuthResponse(
        user=UserResponse.model_validate(user),
        tokens=TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=expires_in,
        ),
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_tokens(
    request: RefreshTokenRequest,
    session: AsyncSession = Depends(get_db_session),
):
    """Rotate refresh token and issue new access & refresh tokens."""
    access_token, refresh_token, expires_in = await AuthService.refresh_access_token(
        session=session,
        refresh_token=request.refresh_token,
    )
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=expires_in,
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user),
):
    """Fetch profile of currently authenticated user."""
    return UserResponse.model_validate(current_user)


@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(
    request: RefreshTokenRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    """Revoke refresh token on logout."""
    await AuthService.revoke_refresh_token(session, request.refresh_token)
    return {"message": "Logged out successfully."}
