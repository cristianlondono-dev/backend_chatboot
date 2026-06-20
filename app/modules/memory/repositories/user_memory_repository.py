import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.memory.models.user_memory_model import UserMemory
from app.modules.memory.models.user_memory_embedding_model import UserMemoryEmbedding

MIN_SIMILARITY = 0.30


class UserMemoryRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        agent_id: uuid.UUID,
        user_id: uuid.UUID,
        memory: str,
        importance: str = "medium",
        source_field: str | None = None
    ) -> UserMemory:
        obj = UserMemory(
            agent_id=agent_id, user_id=user_id, memory=memory,
            importance=importance, source_field=source_field
        )
        self.db.add(obj)
        await self.db.commit()
        await self.db.refresh(obj)
        return obj

    async def get_source_fields(self, agent_id: uuid.UUID, user_id: uuid.UUID) -> set[str]:
        """Resolver column names already stored as memories for this user."""
        result = await self.db.execute(
            select(UserMemory.source_field).where(
                UserMemory.agent_id == agent_id,
                UserMemory.user_id == user_id,
                UserMemory.source_field.is_not(None)
            )
        )
        return set(result.scalars().all())

    async def create_embedding(self, memory_id: uuid.UUID, model_name: str, embedding: list[float]) -> UserMemoryEmbedding:
        obj = UserMemoryEmbedding(memory_id=memory_id, model_name=model_name, embedding=embedding)
        self.db.add(obj)
        await self.db.commit()
        await self.db.refresh(obj)
        return obj

    async def delete_by_agent_ids(self, agent_ids: list[uuid.UUID]) -> None:
        if not agent_ids:
            return
        await self.db.execute(delete(UserMemory).where(UserMemory.agent_id.in_(agent_ids)))

    async def get_high_importance(self, agent_id: uuid.UUID, user_id: uuid.UUID) -> list[UserMemory]:
        result = await self.db.execute(
            select(UserMemory).where(
                UserMemory.agent_id == agent_id,
                UserMemory.user_id == user_id,
                UserMemory.importance == "high"
            ).order_by(UserMemory.created_at.desc()).limit(20)
        )
        return list(result.scalars().all())

    async def search_similar(
        self,
        agent_id: uuid.UUID,
        user_id: uuid.UUID,
        embedding: list[float],
        limit: int = 5
    ) -> list[dict]:
        similarity_expr = (1 - UserMemoryEmbedding.embedding.cosine_distance(embedding))

        result = await self.db.execute(
            select(UserMemory, similarity_expr.label("similarity"))
            .join(UserMemoryEmbedding, UserMemoryEmbedding.memory_id == UserMemory.id)
            .where(UserMemory.agent_id == agent_id, UserMemory.user_id == user_id)
            .order_by(similarity_expr.desc())
            .limit(limit)
        )

        rows = result.all()
        return [
            {"memory": row[0], "similarity": float(row[1])}
            for row in rows
            if float(row[1]) >= MIN_SIMILARITY
        ]
