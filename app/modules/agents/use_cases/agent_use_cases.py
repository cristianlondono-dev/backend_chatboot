from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException
from app.modules.agents.models.agent_model import Agent
from app.modules.agents.repositories.agent_repository import AgentRepository
from app.modules.knowledge_bases.repositories.knowledge_base_repository import (
    KnowledgeBaseRepository,
)
from app.modules.organizations.repositories.organization_repository import (
    OrganizationRepository,
)


class CreateAgentUseCase:

    def __init__(self, db: AsyncSession):
        self.repository = AgentRepository(db)
        self.org_repository = OrganizationRepository(db)

    async def execute(
        self,
        organization_id: UUID,
        name: str,
        description: str | None,
        visibility: str,
        business_type: str = "products",
        escalation_notes: str | None = None
    ) -> Agent:
        if not await self.org_repository.get_by_id(organization_id):
            raise NotFoundException("Organización", str(organization_id))

        return await self.repository.create(
            organization_id=organization_id,
            name=name,
            description=description,
            visibility=visibility,
            business_type=business_type,
            escalation_notes=escalation_notes
        )


class UpdateAgentUseCase:

    def __init__(self, db: AsyncSession):
        self.repository = AgentRepository(db)

    async def execute(self, agent_id: UUID, **fields) -> Agent:
        agent = await self.repository.update(agent_id, **fields)
        if not agent:
            raise NotFoundException("Agente", str(agent_id))
        return agent


class AddKnowledgeBaseToAgentUseCase:

    def __init__(self, db: AsyncSession):
        self.repository = AgentRepository(db)
        self.kb_repository = KnowledgeBaseRepository(db)

    async def execute(self, agent_id: UUID, knowledge_base_id: UUID) -> None:
        if not await self.kb_repository.get_by_id(knowledge_base_id):
            raise NotFoundException("Base de conocimiento", str(knowledge_base_id))

        await self.repository.add_knowledge_base(agent_id, knowledge_base_id)


class RemoveKnowledgeBaseFromAgentUseCase:

    def __init__(self, db: AsyncSession):
        self.repository = AgentRepository(db)

    async def execute(self, agent_id: UUID, knowledge_base_id: UUID) -> bool:
        return await self.repository.remove_knowledge_base(agent_id, knowledge_base_id)
