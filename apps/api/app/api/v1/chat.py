from typing import List
from fastapi import APIRouter, Depends, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.database import get_db_session
from apps.api.app.models.user import User
from apps.api.app.api.v1.auth import get_current_user
from apps.api.app.schemas.chat import (
    ChatRequest,
    ChatMessageResponse,
    ConversationSummary,
    ConversationDetail,
)
from apps.api.app.services.chat_service import ChatService

router = APIRouter(prefix="/repositories/{repository_id}/chat", tags=["Codebase Chat & RAG"])


@router.post("", response_model=ChatMessageResponse, status_code=status.HTTP_200_OK)
async def send_chat_message(
    repository_id: str,
    request: ChatRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    """Submit a question to the codebase RAG engine (synchronous or SSE streaming)."""
    if request.stream:
        generator = ChatService.stream_chat_message(
            session=session,
            repository_id=repository_id,
            request=request,
            user=current_user,
        )
        return StreamingResponse(
            generator,
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    return await ChatService.send_chat_message(
        session=session,
        repository_id=repository_id,
        request=request,
        user=current_user,
    )


@router.get("/sessions", response_model=List[ConversationSummary])
async def list_chat_sessions(
    repository_id: str,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    """List all chat sessions for this repository owned by the authenticated user."""
    return await ChatService.list_conversations(
        session=session,
        repository_id=repository_id,
        user=current_user,
    )


@router.get("/sessions/{session_id}", response_model=ConversationDetail)
async def get_chat_session(
    repository_id: str,
    session_id: str,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    """Retrieve full conversation thread with verified citations and context metadata."""
    return await ChatService.get_conversation(
        session=session,
        repository_id=repository_id,
        conversation_id=session_id,
        user=current_user,
    )


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_chat_session(
    repository_id: str,
    session_id: str,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    """Delete a conversation session."""
    await ChatService.delete_conversation(
        session=session,
        repository_id=repository_id,
        conversation_id=session_id,
        user=current_user,
    )
