import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.memory.models.message_model import Message


class MessageRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, session_id: uuid.UUID, role: str, content: str, token_count: int | None = None) -> Message:
        message = Message(session_id=session_id, role=role, content=content, token_count=token_count)
        self.db.add(message)
        await self.db.commit()
        await self.db.refresh(message)
        return message

    async def get_recent(self, session_id: uuid.UUID, limit: int = 20) -> list[Message]:
        result = await self.db.execute(
            select(Message)
            .where(Message.session_id == session_id)
            .order_by(Message.created_at.desc())
            .limit(limit)
        )
        messages = list(result.scalars().all())
        return list(reversed(messages))  # chronological order

    async def get_oldest_unsummarized(self, session_id: uuid.UUID, limit: int = 80) -> list[Message]:
        result = await self.db.execute(
            select(Message)
            .where(Message.session_id == session_id)
            .order_by(Message.created_at.asc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def count(self, session_id: uuid.UUID) -> int:
        result = await self.db.execute(
            select(func.count()).where(Message.session_id == session_id)
        )
        return result.scalar_one()
