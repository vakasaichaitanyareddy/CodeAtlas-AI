import os
import tempfile
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from workers.tasks.ingestion import run_ingestion_pipeline


@pytest.mark.asyncio
async def test_chat_api_end_to_end(client: AsyncClient, db_session: AsyncSession):
    # 1. Register User A and create Repository A
    reg_res = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "chat_user_a@codeatlas.dev",
            "password": "Password123!",
            "full_name": "Chat Alpha",
        },
    )
    assert reg_res.status_code == 201
    token_a = reg_res.json()["tokens"]["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    create_repo = await client.post(
        "/api/v1/repositories",
        json={
            "github_url": "https://github.com/codeatlas/rag-test-repo.git",
            "default_branch": "main",
        },
        headers=headers_a,
    )
    assert create_repo.status_code == 201
    repo_id = create_repo.json()["id"]

    # 2. Ingest sample repository code
    with tempfile.TemporaryDirectory() as temp_dir:
        auth_file = os.path.join(temp_dir, "auth_service.py")
        with open(auth_file, "w", encoding="utf-8") as f:
            f.write('''
import jwt

def verify_jwt_token(token: str) -> dict:
    """Validate bearer token and return payload claims."""
    if not token:
        raise ValueError("Token required")
    return {"user_id": 42, "role": "admin"}
''')
        await run_ingestion_pipeline(
            repository_id=repo_id,
            commit_sha="c1c2c3c4",
            source_directory=temp_dir,
            session=db_session,
        )

    # 3. Synchronous Chat Request
    chat_res = await client.post(
        f"/api/v1/repositories/{repo_id}/chat",
        json={
            "message": "Where is the verify_jwt_token function implemented?",
            "mode": "hybrid",
            "stream": False,
        },
        headers=headers_a,
    )
    assert chat_res.status_code == 200
    chat_data = chat_res.json()

    assert "id" in chat_data
    assert "conversation_id" in chat_data
    assert chat_data["role"] == "ASSISTANT"
    assert "content" in chat_data
    assert chat_data["grounding_status"] in ("VERIFIED", "PARTIALLY_VERIFIED", "UNSUPPORTED")
    assert chat_data["intent"] in ("FACTUAL_CODE", "DEPENDENCY", "ARCHITECTURE", "GENERAL_QA")
    assert "context_chunks" in chat_data
    assert "retrieval_evidence" in chat_data
    session_id = chat_data["conversation_id"]

    # 4. List Chat Sessions
    sessions_res = await client.get(
        f"/api/v1/repositories/{repo_id}/chat/sessions",
        headers=headers_a,
    )
    assert sessions_res.status_code == 200
    sessions = sessions_res.json()
    assert len(sessions) >= 1
    assert any(s["id"] == session_id for s in sessions)
    target_session = next(s for s in sessions if s["id"] == session_id)
    assert target_session["message_count"] >= 2  # user + assistant

    # 5. Get Session Details
    detail_res = await client.get(
        f"/api/v1/repositories/{repo_id}/chat/sessions/{session_id}",
        headers=headers_a,
    )
    assert detail_res.status_code == 200
    detail = detail_res.json()
    assert detail["id"] == session_id
    assert len(detail["messages"]) >= 2
    assert detail["messages"][0]["role"] == "USER"
    assert detail["messages"][1]["role"] == "ASSISTANT"

    # 6. Delete Session
    del_res = await client.delete(
        f"/api/v1/repositories/{repo_id}/chat/sessions/{session_id}",
        headers=headers_a,
    )
    assert del_res.status_code == 204

    # Verify session is deleted
    recheck_res = await client.get(
        f"/api/v1/repositories/{repo_id}/chat/sessions/{session_id}",
        headers=headers_a,
    )
    assert recheck_res.status_code == 404
