from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database.database import get_db
from app.core.exceptions import NotFoundException, UnprocessableException
from app.modules.memory.repositories.chat_session_repository import ChatSessionRepository
from app.modules.memory.repositories.message_repository import MessageRepository
from app.modules.memory.repositories.user_memory_repository import UserMemoryRepository
from app.modules.memory.repositories.user_repository import UserRepository
from app.modules.memory.schemas.memory_schema import ChatRequest, ChatResponse, MemoryOut, MessageOut
from app.modules.memory.use_cases.chat_with_memory_use_case import ChatWithMemoryUseCase

router = APIRouter(prefix="/agents", tags=["Memory & Chat"])


@router.post("/{agent_id}/chat", response_model=ChatResponse)
async def chat_with_memory(
    agent_id: UUID,
    body: ChatRequest,
    top_k: int = Query(default=5, ge=1, le=20, description="Chunks RAG a recuperar"),
    db: AsyncSession = Depends(get_db)
):
    try:
        use_case = ChatWithMemoryUseCase(db)
        result = await use_case.execute(
            agent_id=agent_id,
            channel=body.channel,
            channel_id=body.channel_id,
            question=body.question,
            top_k=top_k
        )
        return ChatResponse(**result)
    except (NotFoundException, UnprocessableException):
        raise
    except Exception:
        raise


@router.get("/{agent_id}/users/{channel}/{channel_id}/history", response_model=list[MessageOut])
async def get_conversation_history(
    agent_id: UUID,
    channel: str,
    channel_id: str,
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db)
):
    user = await UserRepository(db).get_by_channel(channel, channel_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")

    session = await ChatSessionRepository(db).get_active(agent_id, user.id)
    if not session:
        return []

    return await MessageRepository(db).get_recent(session.id, limit=limit)


@router.get("/{agent_id}/users/{channel}/{channel_id}/memories", response_model=list[MemoryOut])
async def get_user_memories(
    agent_id: UUID,
    channel: str,
    channel_id: str,
    db: AsyncSession = Depends(get_db)
):
    user = await UserRepository(db).get_by_channel(channel, channel_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")

    return await UserMemoryRepository(db).get_high_importance(agent_id, user.id)
