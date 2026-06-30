from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.tools.models.tool_action_model import ToolAction


class ToolActionRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        agent_id: UUID,
        name: str,
        action_type: str,
        description: str,
        parameters_schema: dict,
        credentials: dict | None,
        config: dict | None,
    ) -> ToolAction:
        action = ToolAction(
            agent_id=agent_id,
            name=name,
            action_type=action_type,
            description=description,
            parameters_schema=parameters_schema,
            credentials=credentials,
            config=config,
        )
        self.db.add(action)
        await self.db.commit()
        await self.db.refresh(action)
        return action

    async def get_by_agent(self, agent_id: UUID) -> list[ToolAction]:
        result = await self.db.execute(
            select(ToolAction)
            .where(ToolAction.agent_id == agent_id)
            .order_by(ToolAction.created_at)
        )
        return list(result.scalars().all())

    async def get_by_id(self, action_id: UUID) -> ToolAction | None:
        return await self.db.get(ToolAction, action_id)

    async def update(self, action: ToolAction, **fields) -> ToolAction:
        for key, value in fields.items():
            setattr(action, key, value)
        await self.db.commit()
        await self.db.refresh(action)
        return action

    async def delete(self, action: ToolAction) -> None:
        await self.db.delete(action)
        await self.db.commit()
