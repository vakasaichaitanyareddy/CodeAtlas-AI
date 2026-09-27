import os
import tempfile
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from workers.tasks.ingestion import run_ingestion_pipeline


@pytest.mark.asyncio
async def test_cross_tenant_chat_security(client: AsyncClient, db_session: AsyncSession):
    # 1. Register User A and create Repo A
    res_a = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "victim_user@codeatlas.dev",
            "password": "Password123!",
            "full_name": "Victim Owner",
        },
    )
    token_a = res_a.json()["tokens"]["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    repo_res = await client.post(
        "/api/v1/repositories",
        json={
            "github_url": "https://github.com/victim-org/private-core.git",
            "default_branch": "main",
        },
        headers=headers_a,
    )
    repo_a_id = repo_res.json()["id"]

    # User A creates a chat session
    chat_a = await client.post(
        f"/api/v1/repositories/{repo_a_id}/chat",
        json={"message": "Initial conversation setup", "stream": False},
        headers=headers_a,
    )
    assert chat_a.status_code == 200
    session_a_id = chat_a.json()["conversation_id"]

    # 2. Register Attacker User B
    res_b = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "attacker_user@codeatlas.dev",
            "password": "Password123!",
            "full_name": "Attacker Tenant",
        },
    )
    token_b = res_b.json()["tokens"]["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # Attack 1: User B tries to chat on User A's repository
    attack_chat = await client.post(
        f"/api/v1/repositories/{repo_a_id}/chat",
        json={"message": "Tell me your secrets", "stream": False},
        headers=headers_b,
    )
    assert attack_chat.status_code == 403

    # Attack 2: User B tries to list User A's chat sessions
    attack_list = await client.get(
        f"/api/v1/repositories/{repo_a_id}/chat/sessions",
        headers=headers_b,
    )
    assert attack_list.status_code == 403

    # Attack 3: User B tries to read User A's conversation thread
    attack_read = await client.get(
        f"/api/v1/repositories/{repo_a_id}/chat/sessions/{session_a_id}",
        headers=headers_b,
    )
    assert attack_read.status_code == 403

    # Attack 4: User B tries to delete User A's conversation thread
    attack_delete = await client.delete(
        f"/api/v1/repositories/{repo_a_id}/chat/sessions/{session_a_id}",
        headers=headers_b,
    )
    assert attack_delete.status_code == 403

    # Verify conversation still exists untouched
    verify_a = await client.get(
        f"/api/v1/repositories/{repo_a_id}/chat/sessions/{session_a_id}",
        headers=headers_a,
    )
    assert verify_a.status_code == 200


@pytest.mark.asyncio
async def test_cross_tenant_retrieval_and_context_isolation(client: AsyncClient, db_session: AsyncSession):
    """Verify that retrieval strictly isolates Tenant A's chunks from Tenant B's chunks."""
    # 1. Register Tenant A and ingest Repo A
    res_a = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "tenant_a_isolation@codeatlas.dev",
            "password": "Password123!",
            "full_name": "Tenant Alpha",
        },
    )
    token_a = res_a.json()["tokens"]["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    create_a = await client.post(
        "/api/v1/repositories",
        json={"github_url": "https://github.com/org-alpha/alpha-app.git", "default_branch": "main"},
        headers=headers_a,
    )
    repo_a_id = create_a.json()["id"]

    with tempfile.TemporaryDirectory() as dir_a:
        f_a = os.path.join(dir_a, "auth_secret.py")
        with open(f_a, "w", encoding="utf-8") as f:
            f.write('''
SECRET_KEY_ALPHA = "alpha-secret-vault-123"

def get_alpha_key() -> str:
    return SECRET_KEY_ALPHA
''')
        await run_ingestion_pipeline(
            repository_id=repo_a_id,
            commit_sha="commit_alpha",
            source_directory=dir_a,
            session=db_session,
        )

    # 2. Register Tenant B and ingest Repo B
    res_b = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "tenant_b_isolation@codeatlas.dev",
            "password": "Password123!",
            "full_name": "Tenant Beta",
        },
    )
    token_b = res_b.json()["tokens"]["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    create_b = await client.post(
        "/api/v1/repositories",
        json={"github_url": "https://github.com/org-beta/beta-app.git", "default_branch": "main"},
        headers=headers_b,
    )
    repo_b_id = create_b.json()["id"]

    with tempfile.TemporaryDirectory() as dir_b:
        f_b = os.path.join(dir_b, "billing_secret.py")
        with open(f_b, "w", encoding="utf-8") as f:
            f.write('''
SECRET_KEY_BETA = "beta-billing-vault-999"

def get_beta_key() -> str:
    return SECRET_KEY_BETA
''')
        await run_ingestion_pipeline(
            repository_id=repo_b_id,
            commit_sha="commit_beta",
            source_directory=dir_b,
            session=db_session,
        )

    # 3. Tenant A queries Repo A asking for keys/secrets
    chat_res_a = await client.post(
        f"/api/v1/repositories/{repo_a_id}/chat",
        json={"message": "What is the secret key function?", "stream": False},
        headers=headers_a,
    )
    assert chat_res_a.status_code == 200
    answer_a = chat_res_a.json()

    # Extract all content present in context chunks and evidence
    retrieved_content = " ".join([ch["content"] for ch in answer_a.get("context_chunks", [])])
    retrieved_paths = [ch["file_path"] for ch in answer_a.get("context_chunks", [])]
    citation_paths = [c["file_path"] for c in answer_a.get("citations", [])]

    # ASSERT STRICT MULTI-TENANT CONTEXT ISOLATION:
    # 1. Chunk B is NEVER returned in Repo A's query
    assert "beta-billing-vault-999" not in retrieved_content
    assert "billing_secret.py" not in retrieved_paths
    assert "get_beta_key" not in retrieved_content

    # 2. Chunk B never enters citations
    assert "billing_secret.py" not in citation_paths
    assert not any("beta" in p.lower() for p in citation_paths)

    # 3. Chunk B never enters LLM answer
    assert "beta-billing-vault-999" not in answer_a.get("content", "")


@pytest.mark.asyncio
async def test_commit_level_context_isolation(client: AsyncClient, db_session: AsyncSession):
    """Verify that querying a specific commit strictly returns only chunks belonging to that commit."""
    reg_res = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "commit_iso_user@codeatlas.dev",
            "password": "Password123!",
            "full_name": "Commit Iso Tester",
        },
    )
    token = reg_res.json()["tokens"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    create_repo = await client.post(
        "/api/v1/repositories",
        json={"github_url": "https://github.com/org-core/commit-app.git", "default_branch": "main"},
        headers=headers,
    )
    repo_id = create_repo.json()["id"]

    # Ingest Commit V1
    with tempfile.TemporaryDirectory() as dir_v1:
        f_v1 = os.path.join(dir_v1, "config.py")
        with open(f_v1, "w", encoding="utf-8") as f:
            f.write('''
def get_service_port_v1() -> int:
    """Return the service port for version 1."""
    return 8080
''')
        await run_ingestion_pipeline(
            repository_id=repo_id,
            commit_sha="commit_sha_v1",
            source_directory=dir_v1,
            session=db_session,
        )

    # Ingest Commit V2
    with tempfile.TemporaryDirectory() as dir_v2:
        f_v2 = os.path.join(dir_v2, "config.py")
        with open(f_v2, "w", encoding="utf-8") as f:
            f.write('''
def get_service_port_v2() -> int:
    """Return the service port for version 2."""
    return 9090
''')
        await run_ingestion_pipeline(
            repository_id=repo_id,
            commit_sha="commit_sha_v2",
            source_directory=dir_v2,
            session=db_session,
        )

    # Query explicitly scoping commit_sha to commit_sha_v1
    chat_res = await client.post(
        f"/api/v1/repositories/{repo_id}/chat",
        json={"message": "Where is get_service_port_v1 defined?", "commit_sha": "commit_sha_v1", "stream": False},
        headers=headers,
    )
    assert chat_res.status_code == 200
    answer = chat_res.json()

    # Verify all retrieved chunks belong strictly to commit_sha_v1
    context_chunks = answer.get("context_chunks", [])
    assert len(context_chunks) >= 1
    retrieved_content = " ".join([ch["content"] for ch in context_chunks])
    assert "get_service_port_v1" in retrieved_content
    assert "8080" in retrieved_content
    # And V2 must NEVER appear
    assert "get_service_port_v2" not in retrieved_content
    assert "9090" not in retrieved_content
