import json
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database.database import get_db
from app.modules.agents.repositories.agent_repository import AgentRepository
from app.modules.agents.schemas.agent_schema import AgentResponse
from app.modules.knowledge_bases.repositories.knowledge_base_repository import (
    KnowledgeBaseRepository,
)
from app.modules.knowledge_bases.schemas.knowledge_base_schema import AskRequest, AskResponse
from app.modules.organizations.exceptions.organization_exceptions import (
    OrganizationAlreadyExistsException,
)
from app.modules.organizations.schemas.organization_schema import (
    CreateOrganizationRequest,
    OrganizationResponse,
)
from app.modules.organizations.use_cases.create_organization_use_case import (
    CreateOrganizationUseCase,
)
from app.modules.retrieval.use_cases.ask_multi_kb_use_case import AskMultiKbUseCase

router = APIRouter(prefix="/organizations", tags=["Organizations"])


@router.post(
    "",
    response_model=OrganizationResponse,
    status_code=status.HTTP_201_CREATED
)
async def create_organization(
    body: CreateOrganizationRequest,
    db: AsyncSession = Depends(get_db)
):
    use_case = CreateOrganizationUseCase(db)

    try:
        organization = await use_case.execute(
            trade_name=body.trade_name,
            business_name=body.business_name,
            tax_id=body.tax_id,
            contact_phone=body.contact_phone,
            address=body.address,
            department=body.department,
            city=body.city
        )
    except OrganizationAlreadyExistsException as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))

    return organization


@router.get("/{organization_id}/agents", response_model=list[AgentResponse])
async def list_organization_agents(
    organization_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    repo = AgentRepository(db)
    return await repo.get_by_organization_id(organization_id)


@router.post("/{organization_id}/ask", response_model=AskResponse)
async def ask_organization(
    organization_id: UUID,
    body: AskRequest,
    area: str | None = Query(default=None, description="Filtrar por área/departamento"),
    top_k: int = Query(default=5, ge=1, le=20, description="Número de chunks a recuperar"),
    db: AsyncSession = Depends(get_db)
):
    kb_repo = KnowledgeBaseRepository(db)
    kbs = await kb_repo.get_by_organization_id(organization_id, area=area)

    if not kbs:
        detail = (
            f"No hay bases de conocimiento en el área '{area}'"
            if area else "La organización no tiene bases de conocimiento"
        )
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail)

    kb_ids = [kb.id for kb in kbs]
    use_case = AskMultiKbUseCase(db)
    answer = await use_case.execute(knowledge_base_ids=kb_ids, question=body.question, top_k=top_k)

    return AskResponse(question=body.question, answer=answer)


@router.post("/{organization_id}/ask/stream")
async def ask_organization_stream(
    organization_id: UUID,
    body: AskRequest,
    area: str | None = Query(default=None, description="Filtrar por área/departamento"),
    top_k: int = Query(default=5, ge=1, le=20, description="Número de chunks a recuperar"),
    db: AsyncSession = Depends(get_db)
):
    kb_repo = KnowledgeBaseRepository(db)
    kbs = await kb_repo.get_by_organization_id(organization_id, area=area)

    if not kbs:
        detail = (
            f"No hay bases de conocimiento en el área '{area}'"
            if area else "La organización no tiene bases de conocimiento"
        )
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail)

    kb_ids = [kb.id for kb in kbs]
    use_case = AskMultiKbUseCase(db)

    async def event_stream():
        async for chunk in use_case.execute_stream(kb_ids, body.question, top_k=top_k):
            yield f"data: {json.dumps(chunk)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
