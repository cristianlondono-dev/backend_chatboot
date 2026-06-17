from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database.database import get_db
from app.modules.agents.repositories.agent_repository import AgentRepository
from app.modules.tools.actions.action_registry import ActionRegistry
from app.modules.tools.repositories.tool_action_repository import ToolActionRepository
from app.modules.tools.schemas.tool_action_schema import (
    CreateToolActionRequest,
    TestToolActionRequest,
    TestToolActionResponse,
    ToolActionResponse,
    UpdateToolActionRequest,
)
from app.modules.tools.services.tool_action_executor_service import ToolActionExecutorService

router = APIRouter(prefix="/agents", tags=["Tool Actions"])


@router.get("/tool-actions/types")
async def list_action_types():
    """List all available built-in action_type values with their defaults."""
    result = []
    for action_type in ActionRegistry.list_types():
        defaults = ActionRegistry.get_defaults(action_type)
        result.append({
            "action_type": action_type,
            "default_description": defaults.get("description", ""),
            "default_parameters_schema": defaults.get("parameters_schema", {}),
        })
    return result


@router.post(
    "/{agent_id}/tool-actions",
    response_model=ToolActionResponse,
    status_code=status.HTTP_201_CREATED
)
async def create_tool_action(
    agent_id: UUID,
    body: CreateToolActionRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Register a new executable action for an agent.

    If parameters_schema is not provided, the built-in default for the
    action_type is used automatically.
    """
    agent = await AgentRepository(db).get_by_id(agent_id)
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agente no encontrado")

    parameters_schema = body.parameters_schema
    if not parameters_schema:
        defaults = ActionRegistry.get_defaults(body.action_type)
        parameters_schema = defaults.get("parameters_schema", {})

    repo = ToolActionRepository(db)
    record = await repo.create(
        agent_id=agent_id,
        name=body.name,
        action_type=body.action_type,
        description=body.description,
        parameters_schema=parameters_schema,
        credentials=body.credentials,
        config=body.config,
    )
    await db.commit()
    await db.refresh(record)
    return record


@router.get("/{agent_id}/tool-actions", response_model=list[ToolActionResponse])
async def list_tool_actions(agent_id: UUID, db: AsyncSession = Depends(get_db)):
    """List all tool actions configured for an agent."""
    return await ToolActionRepository(db).get_by_agent(agent_id)


@router.get("/{agent_id}/tool-actions/{action_id}", response_model=ToolActionResponse)
async def get_tool_action(agent_id: UUID, action_id: UUID, db: AsyncSession = Depends(get_db)):
    record = await ToolActionRepository(db).get_by_id(action_id)
    if not record or record.agent_id != agent_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tool action no encontrado")
    return record


@router.put("/{agent_id}/tool-actions/{action_id}", response_model=ToolActionResponse)
async def update_tool_action(
    agent_id: UUID,
    action_id: UUID,
    body: UpdateToolActionRequest,
    db: AsyncSession = Depends(get_db)
):
    repo = ToolActionRepository(db)
    record = await repo.get_by_id(action_id)
    if not record or record.agent_id != agent_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tool action no encontrado")

    updated = await repo.update(
        action_id=action_id,
        name=body.name,
        description=body.description,
        parameters_schema=body.parameters_schema,
        credentials=body.credentials,
        config=body.config,
        is_active=body.is_active,
    )
    await db.commit()
    await db.refresh(updated)
    return updated


@router.delete("/{agent_id}/tool-actions/{action_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tool_action(agent_id: UUID, action_id: UUID, db: AsyncSession = Depends(get_db)):
    repo = ToolActionRepository(db)
    record = await repo.get_by_id(action_id)
    if not record or record.agent_id != agent_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tool action no encontrado")
    await repo.delete(action_id)
    await db.commit()


@router.post(
    "/{agent_id}/tool-actions/{action_id}/test",
    response_model=TestToolActionResponse
)
async def test_tool_action(
    agent_id: UUID,
    action_id: UUID,
    body: TestToolActionRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Test a tool action by executing it directly with the given params.
    Useful for verifying credentials and config before enabling the action.
    """
    repo = ToolActionRepository(db)
    record = await repo.get_by_id(action_id)
    if not record or record.agent_id != agent_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tool action no encontrado")

    executor = ToolActionExecutorService()
    result = await executor.execute(record, body.params)

    if "error" in result:
        return TestToolActionResponse(success=False, error=result["error"])
    return TestToolActionResponse(success=True, result=result)
