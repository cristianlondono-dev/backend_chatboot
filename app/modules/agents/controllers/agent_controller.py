import json
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database.database import get_db
from app.modules.agents.repositories.agent_repository import AgentRepository
from app.modules.agents.schemas.agent_schema import (
    AddKnowledgeBaseRequest,
    AgentResponse,
    AskAgentRequest,
    AskAgentResponse,
    CreateAgentRequest,
    UpdateAgentRequest,
)
from app.modules.agents.use_cases.agent_use_cases import (
    AddKnowledgeBaseToAgentUseCase,
    CreateAgentUseCase,
    RemoveKnowledgeBaseFromAgentUseCase,
)
from app.modules.retrieval.use_cases.ask_multi_kb_use_case import AskMultiKbUseCase

router = APIRouter(prefix="/agents", tags=["Agents"])


@router.post("", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
async def create_agent(
    body: CreateAgentRequest,
    db: AsyncSession = Depends(get_db)
):
    use_case = CreateAgentUseCase(db)
    return await use_case.execute(
        organization_id=body.organization_id,
        name=body.name,
        description=body.description,
        visibility=body.visibility
    )


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(
    agent_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    repo = AgentRepository(db)
    agent = await repo.get_by_id(agent_id)
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agente no encontrado")
    return agent


@router.patch("/{agent_id}", response_model=AgentResponse)
async def update_agent(
    agent_id: UUID,
    body: UpdateAgentRequest,
    db: AsyncSession = Depends(get_db)
):
    repo = AgentRepository(db)
    agent = await repo.update(agent_id, **body.model_dump(exclude_none=True))
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agente no encontrado")
    return agent


@router.post("/{agent_id}/knowledge-bases", status_code=status.HTTP_204_NO_CONTENT)
async def add_knowledge_base(
    agent_id: UUID,
    body: AddKnowledgeBaseRequest,
    db: AsyncSession = Depends(get_db)
):
    repo = AgentRepository(db)
    if not await repo.get_by_id(agent_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agente no encontrado")

    use_case = AddKnowledgeBaseToAgentUseCase(db)
    await use_case.execute(agent_id, body.knowledge_base_id)


@router.delete("/{agent_id}/knowledge-bases/{knowledge_base_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_knowledge_base(
    agent_id: UUID,
    knowledge_base_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    use_case = RemoveKnowledgeBaseFromAgentUseCase(db)
    removed = await use_case.execute(agent_id, knowledge_base_id)
    if not removed:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vínculo no encontrado")


@router.post("/{agent_id}/ask", response_model=AskAgentResponse)
async def ask_agent(
    agent_id: UUID,
    body: AskAgentRequest,
    top_k: int = Query(default=5, ge=1, le=20, description="Número de chunks a recuperar"),
    db: AsyncSession = Depends(get_db)
):
    repo = AgentRepository(db)
    if not await repo.get_by_id(agent_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agente no encontrado")

    kb_ids = await repo.get_knowledge_base_ids(agent_id)
    if not kb_ids:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="El agente no tiene bases de conocimiento vinculadas"
        )

    use_case = AskMultiKbUseCase(db)
    answer = await use_case.execute(knowledge_base_ids=kb_ids, question=body.question, top_k=top_k)

    return AskAgentResponse(question=body.question, answer=answer)


@router.post("/{agent_id}/ask/stream")
async def ask_agent_stream(
    agent_id: UUID,
    body: AskAgentRequest,
    top_k: int = Query(default=5, ge=1, le=20, description="Número de chunks a recuperar"),
    db: AsyncSession = Depends(get_db)
):
    repo = AgentRepository(db)
    if not await repo.get_by_id(agent_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agente no encontrado")

    kb_ids = await repo.get_knowledge_base_ids(agent_id)
    if not kb_ids:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="El agente no tiene bases de conocimiento vinculadas"
        )

    use_case = AskMultiKbUseCase(db)

    async def event_stream():
        async for chunk in use_case.execute_stream(kb_ids, body.question, top_k=top_k):
            yield f"data: {json.dumps(chunk)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
