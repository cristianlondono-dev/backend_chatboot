import uuid
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.memory.models.chat_session_model import ChatSession

_INACTIVITY_MINUTES = 30


class ChatSessionRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_active(self, agent_id: uuid.UUID, user_id: uuid.UUID) -> ChatSession | None:
        result = await self.db.execute(
            select(ChatSession).where(
                ChatSession.agent_id == agent_id,
                ChatSession.user_id == user_id,
                ChatSession.status == "active"
            ).order_by(ChatSession.started_at.desc()).limit(1)
        )
        return result.scalar_one_or_none()

    async def create(self, agent_id: uuid.UUID, user_id: uuid.UUID, onboarding_step: int | None = None) -> ChatSession:
        session = ChatSession(
            agent_id=agent_id,
            user_id=user_id,
            status="active",
            onboarding_step=onboarding_step
        )
        self.db.add(session)
        await self.db.commit()
        await self.db.refresh(session)
        return session

    async def close(self, session_id: uuid.UUID) -> None:
        await self.db.execute(
            update(ChatSession)
            .where(ChatSession.id == session_id)
            .values(status="closed", ended_at=_now())
        )
        await self.db.commit()

    async def touch(self, session_id: uuid.UUID) -> None:
        await self.db.execute(
            update(ChatSession)
            .where(ChatSession.id == session_id)
            .values(last_message_at=_now())
        )
        await self.db.commit()

    async def advance_onboarding(self, session_id: uuid.UUID, next_step: int | None) -> None:
        """Set onboarding_step to next_step. Pass None to mark onboarding complete."""
        await self.db.execute(
            update(ChatSession)
            .where(ChatSession.id == session_id)
            .values(onboarding_step=next_step)
        )
        await self.db.commit()

    def is_expired(self, session: ChatSession) -> bool:
        now = _now()
        last = session.last_message_at
        if last.tzinfo is None:
            last = last.replace(tzinfo=timezone.utc)
        return (now - last).total_seconds() / 60 > _INACTIVITY_MINUTES


def _now() -> datetime:
    return datetime.now(timezone.utc)
