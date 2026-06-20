from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.knowledge_bases.models.knowledge_base_model import (
    KnowledgeBase
)


class KnowledgeBaseRepository:

    def __init__(
        self,
        db: AsyncSession
    ):
        self.db = db

    async def create(
        self,
        organization_id,
        name: str,
        description: str | None = None,
        area: str | None = None
    ) -> KnowledgeBase:

        knowledge_base = KnowledgeBase(
            organization_id=organization_id,
            name=name,
            description=description,
            area=area
        )

        self.db.add(knowledge_base)

        await self.db.commit()

        await self.db.refresh(knowledge_base)

        return knowledge_base

    async def get_by_organization_id(
        self,
        organization_id: UUID,
        area: str | None = None
    ) -> list[KnowledgeBase]:

        query = select(KnowledgeBase).where(
            KnowledgeBase.organization_id == organization_id
        )

        if area is not None:
            query = query.where(KnowledgeBase.area == area)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_by_id(self, knowledge_base_id: UUID) -> KnowledgeBase | None:
        return await self.db.get(KnowledgeBase, knowledge_base_id)

    async def delete(self, knowledge_base_id: UUID) -> None:
        await self.db.execute(
            delete(KnowledgeBase).where(KnowledgeBase.id == knowledge_base_id)
        )