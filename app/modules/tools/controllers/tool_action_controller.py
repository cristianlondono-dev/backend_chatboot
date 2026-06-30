from uuid import UUID
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database.database import get_db
from app.modules.tools.models.tool_action_model import ToolAction
from app.modules.tools.repositories.tool_action_repository import ToolActionRepository
from app.modules.agents.repositories.agent_repository import AgentRepository

router = APIRouter(prefix="/agents", tags=["Tool Actions"])

ACTION_TYPES = [
    "shopify_get_order",
    "shopify_confirm_order",
    "shopify_list_orders",
    "shopify_cancel_order",
    "google_calendar_create_event",
    "google_calendar_list_events",
    "google_calendar_cancel_event",
    "google_calendar_update_event",
    "custom_rest",
    "human_handoff",
]


class ToolActionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    agent_id: UUID
    name: str
    action_type: str
    description: str
    parameters_schema: dict[str, Any]
    config: dict[str, Any] | None
    is_active: bool
    created_at: str

    @classmethod
    def from_orm_safe(cls, obj: ToolAction) -> "ToolActionResponse":
        from datetime import datetime
        return cls(
            id=obj.id,
            agent_id=obj.agent_id,
            name=obj.name,
            action_type=obj.action_type,
            description=obj.description,
            parameters_schema=obj.parameters_schema or {},
            config=obj.config,
            is_active=obj.is_active,
            created_at=obj.created_at.isoformat() if isinstance(obj.created_at, datetime) else str(obj.created_at),
        )


class CreateToolActionRequest(BaseModel):
    name: str
    action_type: str
    description: str
    parameters_schema: dict[str, Any] = {}
    credentials: dict[str, Any] | None = None
    config: dict[str, Any] | None = None


class UpdateToolActionRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    parameters_schema: dict[str, Any] | None = None
    credentials: dict[str, Any] | None = None
    config: dict[str, Any] | None = None
    is_active: bool | None = None


def _not_found():
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tool action no encontrada")


@router.get("/tool-actions/types")
async def list_action_types():
    return ACTION_TYPES


@router.post("/{agent_id}/tool-actions", response_model=ToolActionResponse, status_code=status.HTTP_201_CREATED)
async def create_tool_action(
    agent_id: UUID,
    body: CreateToolActionRequest,
    db: AsyncSession = Depends(get_db),
):
    if not await AgentRepository(db).get_by_id(agent_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agente no encontrado")
    if body.action_type not in ACTION_TYPES:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"action_type inválido: {body.action_type}")

    action = await ToolActionRepository(db).create(
        agent_id=agent_id,
        name=body.name,
        action_type=body.action_type,
        description=body.description,
        parameters_schema=body.parameters_schema,
        credentials=body.credentials,
        config=body.config,
    )
    return ToolActionResponse.from_orm_safe(action)


@router.get("/{agent_id}/tool-actions", response_model=list[ToolActionResponse])
async def list_tool_actions(agent_id: UUID, db: AsyncSession = Depends(get_db)):
    actions = await ToolActionRepository(db).get_by_agent(agent_id)
    return [ToolActionResponse.from_orm_safe(a) for a in actions]


@router.get("/{agent_id}/tool-actions/{action_id}", response_model=ToolActionResponse)
async def get_tool_action(agent_id: UUID, action_id: UUID, db: AsyncSession = Depends(get_db)):
    action = await ToolActionRepository(db).get_by_id(action_id)
    if not action or action.agent_id != agent_id:
        _not_found()
    return ToolActionResponse.from_orm_safe(action)


@router.put("/{agent_id}/tool-actions/{action_id}", response_model=ToolActionResponse)
async def update_tool_action(
    agent_id: UUID,
    action_id: UUID,
    body: UpdateToolActionRequest,
    db: AsyncSession = Depends(get_db),
):
    repo = ToolActionRepository(db)
    action = await repo.get_by_id(action_id)
    if not action or action.agent_id != agent_id:
        _not_found()
    updated = await repo.update(action, **body.model_dump(exclude_none=True))
    return ToolActionResponse.from_orm_safe(updated)


@router.delete("/{agent_id}/tool-actions/{action_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tool_action(agent_id: UUID, action_id: UUID, db: AsyncSession = Depends(get_db)):
    repo = ToolActionRepository(db)
    action = await repo.get_by_id(action_id)
    if not action or action.agent_id != agent_id:
        _not_found()
    await repo.delete(action)


@router.post("/{agent_id}/tool-actions/{action_id}/test")
async def test_tool_action(
    agent_id: UUID,
    action_id: UUID,
    body: dict[str, Any],
    db: AsyncSession = Depends(get_db),
):
    action = await ToolActionRepository(db).get_by_id(action_id)
    if not action or action.agent_id != agent_id:
        _not_found()
    return {"status": "ok", "action_type": action.action_type, "params": body.get("params", {})}
