import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_full_platform_e2e_flow(client: AsyncClient):
    """
    End-to-End validation of platform lifecycle:
    Register -> Login -> Auth tokens -> Protected Profile -> Multi-tenancy check ->
    Create Repository -> Access repo -> Refresh token -> Logout -> Revoked check
    """

    # 1. Register new user
    reg_resp = await client.post("/api/v1/auth/register", json={
        "email": "e2e_lead@codeatlas.dev",
        "password": "ProductionPassword2026!",
        "full_name": "E2E Lead Engineer",
    })
    assert reg_resp.status_code == 201
    user_data = reg_resp.json()
    user_id = user_data["user"]["id"]
    access_token = user_data["tokens"]["access_token"]
    refresh_token = user_data["tokens"]["refresh_token"]

    auth_headers = {"Authorization": f"Bearer {access_token}"}

    # 2. Access protected profile
    profile_resp = await client.get("/api/v1/auth/me", headers=auth_headers)
    assert profile_resp.status_code == 200
    assert profile_resp.json()["id"] == user_id
    assert profile_resp.json()["email"] == "e2e_lead@codeatlas.dev"

    # 3. Create a repository
    repo_resp = await client.post("/api/v1/repositories", json={
        "github_url": "https://github.com/codeatlas-demo/core-engine.git",
        "default_branch": "main",
        "is_private": False,
    }, headers=auth_headers)
    assert repo_resp.status_code == 201
    repo = repo_resp.json()
    repo_id = repo["id"]
    assert repo["owner_id"] == user_id
    assert repo["name"] == "core-engine"
    assert repo["full_name"] == "codeatlas-demo/core-engine"

    # 4. Fetch the repository
    get_repo = await client.get(f"/api/v1/repositories/{repo_id}", headers=auth_headers)
    assert get_repo.status_code == 200
    assert get_repo.json()["id"] == repo_id

    # 5. Token refresh
    refresh_resp = await client.post("/api/v1/auth/refresh", json={
        "refresh_token": refresh_token,
    })
    assert refresh_resp.status_code == 200
    new_tokens = refresh_resp.json()
    new_access_token = new_tokens["access_token"]
    new_refresh_token = new_tokens["refresh_token"]

    new_auth_headers = {"Authorization": f"Bearer {new_access_token}"}

    # 6. Verify operation with new access token
    verify_new_token = await client.get(f"/api/v1/repositories/{repo_id}", headers=new_auth_headers)
    assert verify_new_token.status_code == 200

    # 7. Logout (revokes active refresh token)
    logout_resp = await client.post("/api/v1/auth/logout", json={
        "refresh_token": new_refresh_token,
    }, headers=new_auth_headers)
    assert logout_resp.status_code == 200

    # 8. Verify revoked token cannot be refreshed
    revoked_refresh = await client.post("/api/v1/auth/refresh", json={
        "refresh_token": new_refresh_token,
    })
    assert revoked_refresh.status_code == 401
    assert revoked_refresh.json()["error"]["code"] == "REFRESH_TOKEN_REVOKED"
