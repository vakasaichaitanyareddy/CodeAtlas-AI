import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_repository_lifecycle_and_multitenancy(client: AsyncClient):
    # 1. Register User A
    res_a = await client.post("/api/v1/auth/register", json={
        "email": "user_a@codeatlas.dev",
        "password": "Password123!",
        "full_name": "User Alpha",
    })
    token_a = res_a.json()["tokens"]["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # 2. Register User B
    res_b = await client.post("/api/v1/auth/register", json={
        "email": "user_b@codeatlas.dev",
        "password": "Password123!",
        "full_name": "User Beta",
    })
    token_b = res_b.json()["tokens"]["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # 3. User A creates Repository A
    repo_a_payload = {
        "github_url": "https://github.com/organization/repo-alpha.git",
        "default_branch": "main",
        "is_private": True,
    }
    create_a = await client.post("/api/v1/repositories", json=repo_a_payload, headers=headers_a)
    assert create_a.status_code == 201
    repo_a = create_a.json()
    assert repo_a["name"] == "repo-alpha"
    assert repo_a["full_name"] == "organization/repo-alpha"
    repo_a_id = repo_a["id"]

    # 4. User B creates Repository B
    repo_b_payload = {
        "github_url": "https://github.com/organization/repo-beta.git",
        "default_branch": "main",
    }
    create_b = await client.post("/api/v1/repositories", json=repo_b_payload, headers=headers_b)
    assert create_b.status_code == 201
    repo_b = create_b.json()
    repo_b_id = repo_b["id"]

    # 5. Multi-tenancy check: User A lists repositories -> only receives Repo A
    list_a = await client.get("/api/v1/repositories", headers=headers_a)
    assert list_a.status_code == 200
    user_a_repos = list_a.json()
    assert len(user_a_repos) == 1
    assert user_a_repos[0]["id"] == repo_a_id

    # 6. Multi-tenancy check: User B lists repositories -> only receives Repo B
    list_b = await client.get("/api/v1/repositories", headers=headers_b)
    assert list_b.status_code == 200
    user_b_repos = list_b.json()
    assert len(user_b_repos) == 1
    assert user_b_repos[0]["id"] == repo_b_id

    # 7. Cross-tenant isolation check: User A attempts to view Repo B -> 403 Forbidden
    cross_view = await client.get(f"/api/v1/repositories/{repo_b_id}", headers=headers_a)
    assert cross_view.status_code == 403
    assert cross_view.json()["error"]["code"] == "FORBIDDEN_REPOSITORY_ACCESS"

    # 8. Cross-tenant isolation check: User A attempts to delete Repo B -> 403 Forbidden
    cross_delete = await client.delete(f"/api/v1/repositories/{repo_b_id}", headers=headers_a)
    assert cross_delete.status_code == 403
    assert cross_delete.json()["error"]["code"] == "FORBIDDEN_REPOSITORY_ACCESS"

    # 9. Duplicate repository registration check for the same owner -> 409 Conflict
    dup_create = await client.post("/api/v1/repositories", json=repo_a_payload, headers=headers_a)
    assert dup_create.status_code == 409
    assert dup_create.json()["error"]["code"] == "REPOSITORY_ALREADY_EXISTS"

    # 10. User A successfully deletes Repo A
    del_resp = await client.delete(f"/api/v1/repositories/{repo_a_id}", headers=headers_a)
    assert del_resp.status_code == 200

    # 11. Subsequent get for deleted repo -> 404 Not Found
    get_deleted = await client.get(f"/api/v1/repositories/{repo_a_id}", headers=headers_a)
    assert get_deleted.status_code == 404
    assert get_deleted.json()["error"]["code"] == "REPOSITORY_NOT_FOUND"
