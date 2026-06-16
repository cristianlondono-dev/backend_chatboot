from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.memory.models.user_model import User
from app.modules.memory.models.user_channel_model import UserChannel


class UserRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_canonical_id(self, canonical_id: str) -> User | None:
        result = await self.db.execute(
            select(User).where(User.canonical_id == canonical_id)
        )
        return result.scalar_one_or_none()

    async def get_by_channel(self, channel: str, channel_id: str) -> User | None:
        result = await self.db.execute(
            select(User)
            .join(UserChannel, UserChannel.user_id == User.id)
            .where(UserChannel.channel == channel, UserChannel.channel_id == channel_id)
        )
        return result.scalar_one_or_none()

    async def create(self, canonical_id: str, user_type: str) -> User:
        user = User(canonical_id=canonical_id, user_type=user_type)
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def get_or_create(self, canonical_id: str, user_type: str) -> tuple["User", bool]:
        """Returns (user, created) — created=True when a new user was inserted."""
        user = await self.get_by_canonical_id(canonical_id)
        if user:
            return user, False
        user = await self.create(canonical_id=canonical_id, user_type=user_type)
        return user, True
