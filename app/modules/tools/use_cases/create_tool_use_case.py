import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException
from app.modules.agents.repositories.agent_repository import AgentRepository
from app.modules.tools.models.agent_tool_model import AgentTool
from app.modules.tools.repositories.agent_tool_repository import AgentToolRepository


class CreateAgentToolUseCase:

    def __init__(self, db: AsyncSession):
        self.tool_repo = AgentToolRepository(db)
        self.agent_repo = AgentRepository(db)

    async def execute(self, agent_id: uuid.UUID, **kwargs) -> AgentTool:
        if not await self.agent_repo.get_by_id(agent_id):
            raise NotFoundException("Agente", str(agent_id))
        return await self.tool_repo.create(agent_id=agent_id, **kwargs)
