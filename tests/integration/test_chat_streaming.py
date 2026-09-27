import os
import json
import tempfile
import unittest.mock
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from workers.tasks.ingestion import run_ingestion_pipeline
from apps.api.app.schemas.chat import ChatRequest
from apps.api.app.services.chat_service import ChatService
from apps.api.app.models.user import User


@pytest.mark.asyncio
async def test_chat_sse_streaming_lifecycle(client: AsyncClient, db_session: AsyncSession):
    # 1. Register User & Repository
    reg_res = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "stream_user@codeatlas.dev",
            "password": "Password123!",
            "full_name": "Stream Tester",
        },
    )
    token = reg_res.json()["tokens"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    create_repo = await client.post(
        "/api/v1/repositories",
        json={
            "github_url": "https://github.com/codeatlas/streaming-test.git",
            "default_branch": "main",
        },
        headers=headers,
    )
    repo_id = create_repo.json()["id"]

    with tempfile.TemporaryDirectory() as temp_dir:
        fpath = os.path.join(temp_dir, "calc.py")
        with open(fpath, "w", encoding="utf-8") as f:
            f.write('''
def add(a: int, b: int) -> int:
    """Add two integers."""
    return a + b
''')
        await run_ingestion_pipeline(
            repository_id=repo_id,
            commit_sha="stream123",
            source_directory=temp_dir,
            session=db_session,
        )

    # 2. SSE Streaming Request
    stream_response = await client.post(
        f"/api/v1/repositories/{repo_id}/chat",
        json={
            "message": "Where is the add function defined?",
            "stream": True,
        },
        headers=headers,
    )
    assert stream_response.status_code == 200
    assert "text/event-stream" in stream_response.headers.get("content-type", "")

    # 3. Parse SSE Lines
    lines = stream_response.text.split("\n\n")
    events = []
    complete_event = None

    for block in lines:
        block = block.strip()
        if not block:
            continue
        if block.startswith("data: "):
            payload = json.loads(block[6:])
            events.append(payload)
            if payload.get("event") == "complete":
                complete_event = payload

    # Verify token deltas and complete event
    assert len(events) >= 1
    assert complete_event is not None
    assert complete_event["event"] == "complete"
    assert "answer" in complete_event
    assert "grounding_status" in complete_event
    assert complete_event["grounding_status"] in ("VERIFIED", "PARTIALLY_VERIFIED", "UNSUPPORTED")
    assert "citations" in complete_event

    # 4. Verify message persistence in DB after complete event
    conv_id = complete_event["conversation_id"]
    detail_res = await client.get(
        f"/api/v1/repositories/{repo_id}/chat/sessions/{conv_id}",
        headers=headers,
    )
    assert detail_res.status_code == 200
    detail = detail_res.json()
    assert len(detail["messages"]) == 2  # user + assistant
    assert detail["messages"][1]["role"] == "ASSISTANT"
    assert detail["messages"][1]["grounding_status"] == complete_event["grounding_status"]


@pytest.mark.asyncio
async def test_chat_sse_client_disconnect_cancellation(client: AsyncClient, db_session: AsyncSession):
    """Verify that when a client disconnects midway during streaming, incomplete messages are NOT persisted."""
    reg_res = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "disconnect_user@codeatlas.dev",
            "password": "Password123!",
            "full_name": "Disconnect Tester",
        },
    )
    token = reg_res.json()["tokens"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    create_repo = await client.post(
        "/api/v1/repositories",
        json={
            "github_url": "https://github.com/codeatlas/disconnect-test.git",
            "default_branch": "main",
        },
        headers=headers,
    )
    repo_id = create_repo.json()["id"]

    with tempfile.TemporaryDirectory() as temp_dir:
        fpath = os.path.join(temp_dir, "long_service.py")
        with open(fpath, "w", encoding="utf-8") as f:
            f.write('''
def execute_long_process(task_id: str) -> str:
    """Execute a complex worker process for the given task."""
    return f"Completed {task_id}"
''')
        await run_ingestion_pipeline(
            repository_id=repo_id,
            commit_sha="disc_commit_1",
            source_directory=temp_dir,
            session=db_session,
        )

    # Fetch user model for direct service invocation
    user_stmt = select(User).where(User.email == "disconnect_user@codeatlas.dev")
    user_obj = (await db_session.execute(user_stmt)).scalar_one()

    # Stream turns and disconnect prematurely
    chat_req = ChatRequest(message="Where is execute_long_process defined?", stream=True)
    generator = ChatService.stream_chat_message(
        session=db_session,
        repository_id=repo_id,
        request=chat_req,
        user=user_obj,
    )

    # Consume the first event/token
    first_item = await generator.__anext__()
    assert "data:" in first_item

    # Close generator to simulate client disconnect / cancellation
    await generator.aclose()

    # Verify conversation state in database:
    # Incomplete assistant message must NOT be saved!
    sessions_res = await client.get(
        f"/api/v1/repositories/{repo_id}/chat/sessions",
        headers=headers,
    )
    assert sessions_res.status_code == 200
    sessions = sessions_res.json()
    if sessions:
        conv_id = sessions[0]["id"]
        detail_res = await client.get(
            f"/api/v1/repositories/{repo_id}/chat/sessions/{conv_id}",
            headers=headers,
        )
        assert detail_res.status_code == 200
        msgs = detail_res.json()["messages"]
        assistant_msgs = [m for m in msgs if m["role"] == "ASSISTANT"]
        assert len(assistant_msgs) == 0, "Incomplete assistant message must NOT be persisted on disconnect"


@pytest.mark.asyncio
async def test_chat_sse_llm_failure_error_event(client: AsyncClient, db_session: AsyncSession):
    """Verify that an LLM failure during streaming yields an error event and rolls back uncommitted messages."""
    reg_res = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "llm_fail_user@codeatlas.dev",
            "password": "Password123!",
            "full_name": "Failure Tester",
        },
    )
    token = reg_res.json()["tokens"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    create_repo = await client.post(
        "/api/v1/repositories",
        json={
            "github_url": "https://github.com/codeatlas/failure-test.git",
            "default_branch": "main",
        },
        headers=headers,
    )
    repo_id = create_repo.json()["id"]

    with tempfile.TemporaryDirectory() as temp_dir:
        fpath = os.path.join(temp_dir, "app.py")
        with open(fpath, "w", encoding="utf-8") as f:
            f.write('''
def run_app_server():
    """Start and run the application server."""
    return True
''')
        await run_ingestion_pipeline(
            repository_id=repo_id,
            commit_sha="fail_sha_1",
            source_directory=temp_dir,
            session=db_session,
        )

    # Patch MockLLMProvider.stream to raise an exception simulating LLM API outage
    async def mock_failing_stream(*args, **kwargs):
        raise RuntimeError("LLM service unavailable: 503 Provider Outage")
        yield "token"  # unreachable generator syntax

    with unittest.mock.patch("packages.ai.mock_provider.MockLLMProvider.stream", side_effect=mock_failing_stream):
        stream_res = await client.post(
            f"/api/v1/repositories/{repo_id}/chat",
            json={"message": "Where is run_app_server defined?", "stream": True},
            headers=headers,
        )
        assert stream_res.status_code == 200
        assert "text/event-stream" in stream_res.headers.get("content-type", "")
        body = stream_res.text
        assert "error" in body
        assert "LLM service unavailable" in body

        # Verify database has no falsely completed assistant message
        sessions_res = await client.get(
            f"/api/v1/repositories/{repo_id}/chat/sessions",
            headers=headers,
        )
        assert sessions_res.status_code == 200
        sessions = sessions_res.json()
        if sessions:
            conv_id = sessions[0]["id"]
            detail = (await client.get(f"/api/v1/repositories/{repo_id}/chat/sessions/{conv_id}", headers=headers)).json()
            assistant_msgs = [m for m in detail["messages"] if m["role"] == "ASSISTANT"]
            assert len(assistant_msgs) == 0, "No falsely completed assistant message should exist after LLM error"
