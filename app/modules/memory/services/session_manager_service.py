import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.memory.models.chat_session_model import ChatSession
from app.modules.memory.repositories.chat_session_repository import ChatSessionRepository


class SessionManagerService:

    def __init__(self, db: AsyncSession):
        self.repo = ChatSessionRepository(db)

    async def get_or_create(self, agent_id: uuid.UUID, user_id: uuid.UUID) -> ChatSession:
        session = await self.repo.get_active(agent_id, user_id)

        if session and self.repo.is_expired(session):
            await self.repo.close(session.id)
            session = None

        if session is None:
            session = await self.repo.create(agent_id, user_id)

        return session

    async def touch(self, session_id: uuid.UUID) -> None:
        await self.repo.touch(session_id)
