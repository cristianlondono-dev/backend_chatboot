from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database.database import get_db
from app.modules.agents.repositories.agent_repository import AgentRepository
from app.modules.memory.repositories.message_repository import MessageRepository
from app.modules.memory.repositories.user_memory_repository import UserMemoryRepository
from app.modules.memory.repositories.user_repository import UserRepository
from app.modules.memory.schemas.memory_schema import ChatRequest, ChatResponse, MemoryOut, MessageOut
from app.modules.memory.use_cases.chat_with_memory_use_case import ChatWithMemoryUseCase

router = APIRouter(prefix="/agents", tags=["Memory & Chat"])


@router.post("/{agent_id}/chat", response_model=ChatResponse, status_code=status.HTTP_200_OK)
async def chat_with_memory(
    agent_id: UUID,
    body: ChatRequest,
    top_k: int = Query(default=5, ge=1, le=20, description="Número de chunks a recuperar del RAG"),
    db: AsyncSession = Depends(get_db)
):
    agent_repo = AgentRepository(db)
    if not await agent_repo.get_by_id(agent_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agente no encontrado")

    use_case = ChatWithMemoryUseCase(db)
    result = await use_case.execute(
        agent_id=agent_id,
        external_id=body.external_id,
        question=body.question,
        user_name=body.name,
        top_k=top_k
    )
    return ChatResponse(**result)


@router.get("/{agent_id}/users/{external_id}/history", response_model=list[MessageOut])
async def get_conversation_history(
    agent_id: UUID,
    external_id: str,
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db)
):
    user = await UserRepository(db).get_by_external_id(external_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")

    from app.modules.memory.repositories.chat_session_repository import ChatSessionRepository
    session = await ChatSessionRepository(db).get_active(agent_id, user.id)
    if not session:
        return []

    return await MessageRepository(db).get_recent(session.id, limit=limit)


@router.get("/{agent_id}/users/{external_id}/memories", response_model=list[MemoryOut])
async def get_user_memories(
    agent_id: UUID,
    external_id: str,
    db: AsyncSession = Depends(get_db)
):
    user = await UserRepository(db).get_by_external_id(external_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")

    memories = await UserMemoryRepository(db).get_high_importance(agent_id, user.id)
    return memories
