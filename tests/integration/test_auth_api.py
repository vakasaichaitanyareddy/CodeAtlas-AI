import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_and_login_flow(client: AsyncClient):
    # 1. Register a new user
    register_payload = {
        "email": "developer@codeatlas.dev",
        "password": "SecurePassword123!",
        "full_name": "Atlas Developer",
    }
    resp = await client.post("/api/v1/auth/register", json=register_payload)
    assert resp.status_code == 201
    data = resp.json()

    assert "user" in data
    assert data["user"]["email"] == "developer@codeatlas.dev"
    assert data["user"]["role"] == "USER"
    assert "tokens" in data
    assert "access_token" in data["tokens"]
    assert "refresh_token" in data["tokens"]

    access_token = data["tokens"]["access_token"]
    refresh_token = data["tokens"]["refresh_token"]

    # 2. Duplicate registration should be rejected with 409
    dup_resp = await client.post("/api/v1/auth/register", json=register_payload)
    assert dup_resp.status_code == 409
    assert dup_resp.json()["error"]["code"] == "USER_ALREADY_EXISTS"

    # 3. Login with credentials
    login_payload = {
        "email": "developer@codeatlas.dev",
        "password": "SecurePassword123!",
    }
    login_resp = await client.post("/api/v1/auth/login", json=login_payload)
    assert login_resp.status_code == 200
    login_data = login_resp.json()
    assert login_data["user"]["email"] == "developer@codeatlas.dev"

    # 4. Login with invalid password
    bad_login = await client.post("/api/v1/auth/login", json={
        "email": "developer@codeatlas.dev",
        "password": "WrongPassword!",
    })
    assert bad_login.status_code == 401
    assert bad_login.json()["error"]["code"] == "INVALID_CREDENTIALS"

    # 5. Access protected /me endpoint
    headers = {"Authorization": f"Bearer {access_token}"}
    me_resp = await client.get("/api/v1/auth/me", headers=headers)
    assert me_resp.status_code == 200
    assert me_resp.json()["email"] == "developer@codeatlas.dev"

    # 6. Access without token should fail with 401
    no_token_resp = await client.get("/api/v1/auth/me")
    assert no_token_resp.status_code == 401

    # 7. Refresh access token
    refresh_resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert refresh_resp.status_code == 200
    new_tokens = refresh_resp.json()
    assert "access_token" in new_tokens
    assert "refresh_token" in new_tokens

    # 8. Reusing old rotated refresh token should fail with 401
    stale_refresh = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert stale_refresh.status_code == 401
    assert stale_refresh.json()["error"]["code"] == "REFRESH_TOKEN_REVOKED"

    new_access_token = new_tokens["access_token"]
    new_refresh_token = new_tokens["refresh_token"]
    new_headers = {"Authorization": f"Bearer {new_access_token}"}

    # 9. Perform Logout with valid active token
    logout_resp = await client.post("/api/v1/auth/logout", json={"refresh_token": new_refresh_token}, headers=new_headers)
    assert logout_resp.status_code == 200
    assert logout_resp.json()["message"] == "Logged out successfully."

    # 10. Attempting refresh after logout must fail with 401
    revoked_refresh = await client.post("/api/v1/auth/refresh", json={"refresh_token": new_refresh_token})
    assert revoked_refresh.status_code == 401
    assert revoked_refresh.json()["error"]["code"] == "REFRESH_TOKEN_REVOKED"

    # 11. Malformed / tampered JWT token should fail with 401
    bad_token_resp = await client.get("/api/v1/auth/me", headers={"Authorization": "Bearer invalid.jwt.signature"})
    assert bad_token_resp.status_code == 401

    # 12. Token with expired timestamp should fail with 401
    from apps.api.app.core.security import create_access_token
    from datetime import timedelta
    expired_token = create_access_token(subject=data["user"]["id"], expires_delta=timedelta(seconds=-10))
    expired_resp = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {expired_token}"})
    assert expired_resp.status_code == 401
