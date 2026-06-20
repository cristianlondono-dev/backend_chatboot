import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.memory.models.conversation_summary_model import ConversationSummary
from app.modules.memory.models.conversation_summary_embedding_model import ConversationSummaryEmbedding

MIN_SIMILARITY = 0.30


class ConversationSummaryRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, agent_id: uuid.UUID, user_id: uuid.UUID, summary: str, session_id: uuid.UUID | None = None) -> ConversationSummary:
        obj = ConversationSummary(agent_id=agent_id, user_id=user_id, summary=summary, session_id=session_id)
        self.db.add(obj)
        await self.db.commit()
        await self.db.refresh(obj)
        return obj

    async def create_embedding(self, summary_id: uuid.UUID, model_name: str, embedding: list[float]) -> ConversationSummaryEmbedding:
        obj = ConversationSummaryEmbedding(summary_id=summary_id, model_name=model_name, embedding=embedding)
        self.db.add(obj)
        await self.db.commit()
        await self.db.refresh(obj)
        return obj

    async def delete_by_agent_ids(self, agent_ids: list[uuid.UUID]) -> None:
        if not agent_ids:
            return
        await self.db.execute(delete(ConversationSummary).where(ConversationSummary.agent_id.in_(agent_ids)))

    async def search_similar(
        self,
        agent_id: uuid.UUID,
        user_id: uuid.UUID,
        embedding: list[float],
        limit: int = 3
    ) -> list[dict]:
        similarity_expr = (1 - ConversationSummaryEmbedding.embedding.cosine_distance(embedding))

        result = await self.db.execute(
            select(ConversationSummary, similarity_expr.label("similarity"))
            .join(ConversationSummaryEmbedding, ConversationSummaryEmbedding.summary_id == ConversationSummary.id)
            .where(ConversationSummary.agent_id == agent_id, ConversationSummary.user_id == user_id)
            .order_by(similarity_expr.desc())
            .limit(limit)
        )

        rows = result.all()
        return [
            {"summary": row[0], "similarity": float(row[1])}
            for row in rows
            if float(row[1]) >= MIN_SIMILARITY
        ]
