import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.tools.models.agent_tool_model import AgentTool


class AgentToolRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, agent_id: uuid.UUID, **kwargs) -> AgentTool:
        tool = AgentTool(agent_id=agent_id, **kwargs)
        self.db.add(tool)
        await self.db.commit()
        await self.db.refresh(tool)
        return tool

    async def get_by_id(self, tool_id: uuid.UUID) -> AgentTool | None:
        result = await self.db.execute(
            select(AgentTool).where(AgentTool.id == tool_id, AgentTool.is_active.is_(True))
        )
        return result.scalar_one_or_none()

    async def get_by_agent(self, agent_id: uuid.UUID) -> list[AgentTool]:
        result = await self.db.execute(
            select(AgentTool).where(AgentTool.agent_id == agent_id, AgentTool.is_active.is_(True))
        )
        return list(result.scalars().all())

    async def get_by_agent_and_channel(self, agent_id: uuid.UUID, channel: str) -> AgentTool | None:
        result = await self.db.execute(
            select(AgentTool).where(
                AgentTool.agent_id == agent_id,
                AgentTool.channel == channel,
                AgentTool.is_active.is_(True)
            )
        )
        return result.scalar_one_or_none()

    async def delete(self, tool_id: uuid.UUID) -> bool:
        tool = await self.get_by_id(tool_id)
        if not tool:
            return False
        tool.is_active = False
        await self.db.commit()
        return True
