from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.agents.models.agent_model import Agent
from app.modules.agents.repositories.agent_repository import AgentRepository


class CreateAgentUseCase:

    def __init__(self, db: AsyncSession):
        self.repository = AgentRepository(db)

    async def execute(
        self,
        organization_id: UUID,
        name: str,
        description: str | None,
        visibility: str
    ) -> Agent:
        return await self.repository.create(
            organization_id=organization_id,
            name=name,
            description=description,
            visibility=visibility
        )


class AddKnowledgeBaseToAgentUseCase:

    def __init__(self, db: AsyncSession):
        self.repository = AgentRepository(db)

    async def execute(self, agent_id: UUID, knowledge_base_id: UUID) -> None:
        await self.repository.add_knowledge_base(agent_id, knowledge_base_id)


class RemoveKnowledgeBaseFromAgentUseCase:

    def __init__(self, db: AsyncSession):
        self.repository = AgentRepository(db)

    async def execute(self, agent_id: UUID, knowledge_base_id: UUID) -> bool:
        return await self.repository.remove_knowledge_base(agent_id, knowledge_base_id)
