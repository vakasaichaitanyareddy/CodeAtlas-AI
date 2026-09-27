import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_cross_tenant_attack_scenarios(client: AsyncClient):
    """
    Comprehensive attack simulation testing server-side multi-tenancy boundaries.
    User A attempts unauthorized access across all endpoints of Repository B.
    """
    # 1. Register User A (Attacker)
    res_a = await client.post("/api/v1/auth/register", json={
        "email": "attacker_a@codeatlas.dev",
        "password": "Password123!",
        "full_name": "Attacker Alpha",
    })
    token_a = res_a.json()["tokens"]["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # 2. Register User B (Victim)
    res_b = await client.post("/api/v1/auth/register", json={
        "email": "victim_b@codeatlas.dev",
        "password": "Password123!",
        "full_name": "Victim Beta",
    })
    token_b = res_b.json()["tokens"]["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # 3. User B creates private Repository B
    res_repo_b = await client.post("/api/v1/repositories", json={
        "github_url": "https://github.com/internal-org/confidential-service.git",
        "default_branch": "main",
        "is_private": True,
    }, headers=headers_b)
    assert res_repo_b.status_code == 201
    repo_b_id = res_repo_b.json()["id"]

    # 4. Attack 1: User A attempts direct GET /repositories/{repo_b_id}
    atk1 = await client.get(f"/api/v1/repositories/{repo_b_id}", headers=headers_a)
    assert atk1.status_code == 403
    assert atk1.json()["error"]["code"] == "FORBIDDEN_REPOSITORY_ACCESS"

    # 5. Attack 2: User A attempts unauthorized DELETE /repositories/{repo_b_id}
    atk2 = await client.delete(f"/api/v1/repositories/{repo_b_id}", headers=headers_a)
    assert atk2.status_code == 403
    assert atk2.json()["error"]["code"] == "FORBIDDEN_REPOSITORY_ACCESS"

    # 6. Attack 3: User A attempts unauthorized file access /repositories/{repo_b_id}/files
    atk3 = await client.get(f"/api/v1/repositories/{repo_b_id}/files", headers=headers_a)
    assert atk3.status_code == 403
    assert atk3.json()["error"]["code"] == "FORBIDDEN_REPOSITORY_ACCESS"

    # 7. Attack 4: User A attempts unauthorized conversation access /repositories/{repo_b_id}/conversations
    atk4 = await client.get(f"/api/v1/repositories/{repo_b_id}/conversations", headers=headers_a)
    assert atk4.status_code == 403
    assert atk4.json()["error"]["code"] == "FORBIDDEN_REPOSITORY_ACCESS"

    # 8. Attack 5: User A attempts unauthorized dependency graph access /repositories/{repo_b_id}/graph
    atk5 = await client.get(f"/api/v1/repositories/{repo_b_id}/graph", headers=headers_a)
    assert atk5.status_code == 403
    assert atk5.json()["error"]["code"] == "FORBIDDEN_REPOSITORY_ACCESS"

    # 9. Verify Repository B is still intact and accessible by legitimate owner User B
    legit_get = await client.get(f"/api/v1/repositories/{repo_b_id}", headers=headers_b)
    assert legit_get.status_code == 200
    assert legit_get.json()["id"] == repo_b_id
