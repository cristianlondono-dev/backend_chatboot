import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.memory.models.user_channel_model import UserChannel


class UserChannelRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get(self, channel: str, channel_id: str) -> UserChannel | None:
        result = await self.db.execute(
            select(UserChannel).where(
                UserChannel.channel == channel,
                UserChannel.channel_id == channel_id
            )
        )
        return result.scalar_one_or_none()

    async def link(self, user_id: uuid.UUID, channel: str, channel_id: str) -> UserChannel:
        """Links a channel identity to a user. Idempotent — returns existing if already linked."""
        existing = await self.get(channel, channel_id)
        if existing:
            return existing
        entry = UserChannel(user_id=user_id, channel=channel, channel_id=channel_id)
        self.db.add(entry)
        await self.db.commit()
        await self.db.refresh(entry)
        return entry
