import pytest
from httpx import AsyncClient
from apps.api.app.core.security import create_access_token
from apps.api.app.models.user import User
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends
from apps.api.app.dependencies import require_role
from apps.api.app.main import app

# Admin route for RBAC testing
admin_rbac_router = APIRouter(prefix="/api/v1/test-admin", tags=["Testing"])


@admin_rbac_router.get("/admin-only")
async def admin_only_endpoint(current_admin: User = Depends(require_role("ADMIN"))):
    return {"message": "Welcome Admin", "admin_id": current_admin.id}

app.include_router(admin_rbac_router)


@pytest.mark.asyncio
async def test_rbac_authorization(client: AsyncClient, db_session: AsyncSession):
    # 1. Create a regular user and an admin user
    user = User(
        email="regular@codeatlas.dev",
        hashed_password="pw",
        role="USER",
        is_active=True,
    )
    admin = User(
        email="admin@codeatlas.dev",
        hashed_password="pw",
        role="ADMIN",
        is_active=True,
    )
    db_session.add_all([user, admin])
    await db_session.commit()

    user_token = create_access_token(subject=user.id, role="USER")
    admin_token = create_access_token(subject=admin.id, role="ADMIN")

    # Regular user attempting admin endpoint should get 403 Forbidden
    resp_user = await client.get(
        "/api/v1/test-admin/admin-only",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert resp_user.status_code == 403
    assert resp_user.json()["error"]["code"] == "FORBIDDEN_INSUFFICIENT_ROLE"

    # Admin accessing admin endpoint should succeed with 200 OK
    resp_admin = await client.get(
        "/api/v1/test-admin/admin-only",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp_admin.status_code == 200
    assert resp_admin.json()["message"] == "Welcome Admin"
    assert resp_admin.json()["admin_id"] == admin.id
