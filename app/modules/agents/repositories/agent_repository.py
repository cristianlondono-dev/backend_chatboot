from uuid import UUID

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

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
        visibility: str,
        business_type: str = "products",
        escalation_notes: str | None = None
    ) -> Agent:
        agent = Agent(
            organization_id=organization_id,
            name=name,
            description=description,
            visibility=visibility,
            business_type=business_type,
            escalation_notes=escalation_notes
        )
        self.db.add(agent)
        await self.db.commit()
        # Reload with relationship so serialization doesn't fail
        return await self._load(agent.id)

    async def update(self, agent_id: UUID, **fields) -> Agent | None:
        agent = await self.get_by_id(agent_id)
        if not agent:
            return None
        for key, value in fields.items():
            setattr(agent, key, value)
        await self.db.commit()
        return await self._load(agent_id)

    async def get_by_id(self, agent_id: UUID) -> Agent | None:
        result = await self.db.execute(
            select(Agent)
            .where(Agent.id == agent_id)
            .options(selectinload(Agent.knowledge_bases))
        )
        return result.scalar_one_or_none()

    async def get_by_organization_id(self, organization_id: UUID) -> list[Agent]:
        result = await self.db.execute(
            select(Agent)
            .where(Agent.organization_id == organization_id)
            .options(selectinload(Agent.knowledge_bases))
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

    async def delete_by_organization_id(self, organization_id: UUID) -> None:
        # Cascades at the DB level to agent_knowledge_bases, agent_tools and tool_actions.
        await self.db.execute(delete(Agent).where(Agent.organization_id == organization_id))

    async def get_knowledge_base_ids(self, agent_id: UUID) -> list[UUID]:
        result = await self.db.execute(
            select(AgentKnowledgeBase.knowledge_base_id).where(
                AgentKnowledgeBase.agent_id == agent_id
            )
        )
        return list(result.scalars().all())

    async def _load(self, agent_id: UUID) -> Agent:
        result = await self.db.execute(
            select(Agent)
            .where(Agent.id == agent_id)
            .options(selectinload(Agent.knowledge_bases))
            .execution_options(populate_existing=True)
        )
        return result.scalar_one()
