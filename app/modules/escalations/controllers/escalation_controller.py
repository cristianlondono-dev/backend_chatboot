from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database.database import get_db
from app.modules.escalations.repositories.escalation_repository import EscalationRepository
from app.modules.escalations.schemas.escalation_schema import (
    EscalationDetailOut,
    EscalationMessageOut,
    EscalationOut,
    EscalationUpdatedOut,
    SendHumanMessageRequest,
    TakeEscalationOut,
    UpdateEscalationRequest,
)
from app.modules.memory.repositories.chat_session_repository import ChatSessionRepository
from app.modules.memory.repositories.message_repository import MessageRepository

router = APIRouter(prefix="/escalations", tags=["Escalations"])


@router.get("", response_model=list[EscalationOut])
async def list_escalations(
    is_resolved: bool | None = Query(default=None),
    db: AsyncSession = Depends(get_db)
):
    return await EscalationRepository(db).list_all(is_resolved=is_resolved)


@router.patch("/{escalation_id}", response_model=EscalationUpdatedOut)
async def update_escalation(
    escalation_id: UUID,
    body: UpdateEscalationRequest,
    db: AsyncSession = Depends(get_db)
):
    updated = await EscalationRepository(db).set_resolved(escalation_id, body.is_resolved)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Escalamiento no encontrado")
    return updated


@router.get("/{escalation_id}", response_model=EscalationDetailOut)
async def get_escalation_detail(
    escalation_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    detail = await EscalationRepository(db).get_detail(escalation_id)
    if not detail:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Escalamiento no encontrado")
    return detail


@router.get("/{escalation_id}/messages", response_model=list[EscalationMessageOut])
async def get_escalation_messages(
    escalation_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    detail = await EscalationRepository(db).get_detail(escalation_id)
    if not detail:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Escalamiento no encontrado")
    return await MessageRepository(db).get_recent(detail["session_id"], limit=500)


@router.post("/{escalation_id}/take", response_model=TakeEscalationOut)
async def take_escalation(
    escalation_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    detail = await EscalationRepository(db).get_detail(escalation_id)
    if not detail:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Escalamiento no encontrado")
    await ChatSessionRepository(db).set_paused(detail["session_id"], True)
    return {"session_id": detail["session_id"], "is_paused": True}


@router.post(
    "/{escalation_id}/messages",
    response_model=EscalationMessageOut,
    status_code=status.HTTP_201_CREATED
)
async def send_human_message(
    escalation_id: UUID,
    body: SendHumanMessageRequest,
    db: AsyncSession = Depends(get_db)
):
    detail = await EscalationRepository(db).get_detail(escalation_id)
    if not detail:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Escalamiento no encontrado")
    message = await MessageRepository(db).create(detail["session_id"], "human", body.content)
    await ChatSessionRepository(db).touch(detail["session_id"])
    return message
