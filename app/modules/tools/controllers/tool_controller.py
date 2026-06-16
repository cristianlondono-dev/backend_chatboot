from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database.database import get_db
from app.core.exceptions import NotFoundException
from app.modules.tools.repositories.agent_tool_repository import AgentToolRepository
from app.modules.tools.schemas.tool_schema import AgentToolResponse, CreateAgentToolRequest
from app.modules.tools.use_cases.create_tool_use_case import CreateAgentToolUseCase

router = APIRouter(prefix="/agents", tags=["Tools"])


@router.post("/{agent_id}/tools", response_model=AgentToolResponse, status_code=status.HTTP_201_CREATED)
async def create_tool(
    agent_id: UUID,
    body: CreateAgentToolRequest,
    db: AsyncSession = Depends(get_db)
):
    use_case = CreateAgentToolUseCase(db)
    try:
        return await use_case.execute(
            agent_id=agent_id,
            channel=body.channel,
            identifier_type=body.identifier_type,
            user_type=body.user_type,
            resolver_type=body.resolver_type,
            resolver_config=body.resolver_config,
            field_mapping=body.field_mapping,
            onboarding_questions=body.onboarding_questions
        )
    except NotFoundException as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.get("/{agent_id}/tools", response_model=list[AgentToolResponse])
async def list_tools(agent_id: UUID, db: AsyncSession = Depends(get_db)):
    return await AgentToolRepository(db).get_by_agent(agent_id)


@router.get("/{agent_id}/tools/{tool_id}", response_model=AgentToolResponse)
async def get_tool(agent_id: UUID, tool_id: UUID, db: AsyncSession = Depends(get_db)):
    tool = await AgentToolRepository(db).get_by_id(tool_id)
    if not tool or tool.agent_id != agent_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tool no encontrado")
    return tool


@router.delete("/{agent_id}/tools/{tool_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tool(agent_id: UUID, tool_id: UUID, db: AsyncSession = Depends(get_db)):
    deleted = await AgentToolRepository(db).delete(tool_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tool no encontrado")
