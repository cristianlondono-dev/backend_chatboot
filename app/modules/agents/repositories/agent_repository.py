from uuid import UUID

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.agents.models.agent_model import Agent
from app.modules.agents.models.agent_knowledge_base_model import AgentKnowledgeBase


class AgentRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        organization_id: UUID,
        name: str,
        description: str | None,
        visibility: str
    ) -> Agent:
        agent = Agent(
            organization_id=organization_id,
            name=name,
            description=description,
            visibility=visibility
        )
        self.db.add(agent)
        await self.db.commit()
        await self.db.refresh(agent)
        return agent

    async def get_by_id(self, agent_id: UUID) -> Agent | None:
        return await self.db.get(Agent, agent_id)

    async def get_by_organization_id(self, organization_id: UUID) -> list[Agent]:
        result = await self.db.execute(
            select(Agent).where(Agent.organization_id == organization_id)
        )
        return list(result.scalars().all())

    async def add_knowledge_base(
        self,
        agent_id: UUID,
        knowledge_base_id: UUID
    ) -> AgentKnowledgeBase:
        link = AgentKnowledgeBase(
            agent_id=agent_id,
            knowledge_base_id=knowledge_base_id
        )
        self.db.add(link)
        await self.db.commit()
        return link

    async def remove_knowledge_base(
        self,
        agent_id: UUID,
        knowledge_base_id: UUID
    ) -> bool:
        result = await self.db.execute(
            delete(AgentKnowledgeBase).where(
                AgentKnowledgeBase.agent_id == agent_id,
                AgentKnowledgeBase.knowledge_base_id == knowledge_base_id
            )
        )
        await self.db.commit()
        return result.rowcount > 0

    async def get_knowledge_base_ids(self, agent_id: UUID) -> list[UUID]:
        result = await self.db.execute(
            select(AgentKnowledgeBase.knowledge_base_id).where(
                AgentKnowledgeBase.agent_id == agent_id
            )
        )
        return list(result.scalars().all())
