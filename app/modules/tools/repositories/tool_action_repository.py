import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.tools.models.tool_action_model import ToolAction


class ToolActionRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        agent_id: uuid.UUID,
        name: str,
        action_type: str,
        description: str,
        parameters_schema: dict,
        credentials: dict | None,
        config: dict | None,
    ) -> ToolAction:
        record = ToolAction(
            agent_id=agent_id,
            name=name,
            action_type=action_type,
            description=description,
            parameters_schema=parameters_schema,
            credentials=credentials,
            config=config,
        )
        self.db.add(record)
        await self.db.flush()
        await self.db.refresh(record)
        return record

    async def get_by_id(self, action_id: uuid.UUID) -> ToolAction | None:
        return await self.db.get(ToolAction, action_id)

    async def get_by_agent(self, agent_id: uuid.UUID) -> list[ToolAction]:
        result = await self.db.execute(
            select(ToolAction).where(ToolAction.agent_id == agent_id)
        )
        return list(result.scalars().all())

    async def get_active_by_agent(self, agent_id: uuid.UUID) -> list[ToolAction]:
        result = await self.db.execute(
            select(ToolAction).where(
                ToolAction.agent_id == agent_id,
                ToolAction.is_active.is_(True)
            )
        )
        return list(result.scalars().all())

    async def update(
        self,
        action_id: uuid.UUID,
        name: str,
        description: str,
        parameters_schema: dict,
        credentials: dict | None,
        config: dict | None,
        is_active: bool,
    ) -> ToolAction | None:
        record = await self.get_by_id(action_id)
        if not record:
            return None

        record.name = name
        record.description = description
        record.parameters_schema = parameters_schema
        record.credentials = credentials
        record.config = config
        record.is_active = is_active
        await self.db.flush()
        return record

    async def delete(self, action_id: uuid.UUID) -> bool:
        record = await self.get_by_id(action_id)
        if not record:
            return False
        await self.db.delete(record)
        await self.db.flush()
        return True
