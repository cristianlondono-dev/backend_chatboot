from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.memory.models.user_model import User


class UserRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_external_id(self, external_id: str) -> User | None:
        result = await self.db.execute(
            select(User).where(User.external_id == external_id)
        )
        return result.scalar_one_or_none()

    async def create(self, external_id: str, name: str | None = None, email: str | None = None, phone: str | None = None) -> User:
        user = User(external_id=external_id, name=name, email=email, phone=phone)
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def get_or_create(self, external_id: str, name: str | None = None) -> User:
        user = await self.get_by_external_id(external_id)
        if user:
            return user
        return await self.create(external_id=external_id, name=name)
