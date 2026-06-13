from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.embeddings.models.chunk_embedding_model import ChunkEmbedding
from app.modules.documents.models.document_chunk_model import DocumentChunk
from app.modules.documents.models.document_model import Document

MIN_SIMILARITY = 0.30  # discard chunks with similarity below this (0 = unrelated, 1 = identical)


class ChunkEmbeddingRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        chunk_id: UUID,
        model_name: str,
        embedding: list[float]
    ) -> ChunkEmbedding:
        chunk_embedding = ChunkEmbedding(
            chunk_id=chunk_id,
            model_name=model_name,
            embedding=embedding
        )
        self.db.add(chunk_embedding)
        await self.db.commit()
        await self.db.refresh(chunk_embedding)
        return chunk_embedding

    async def search_similar(
        self,
        knowledge_base_id: UUID,
        embedding: list[float],
        limit: int = 5
    ) -> list[dict]:
        return await self.search_similar_in_kbs(
            knowledge_base_ids=[knowledge_base_id],
            embedding=embedding,
            limit=limit
        )

    async def search_similar_in_kbs(
        self,
        knowledge_base_ids: list[UUID],
        embedding: list[float],
        limit: int = 5
    ) -> list[dict]:
        if not knowledge_base_ids:
            return []

        # similarity = 1 - cosine_distance  (1 = identical, 0 = unrelated)
        similarity_expr = (1 - ChunkEmbedding.embedding.cosine_distance(embedding))

        query = (
            select(
                DocumentChunk,
                Document.knowledge_base_id.label("knowledge_base_id"),
                Document.file_name.label("file_name"),
                similarity_expr.label("similarity")
            )
            .join(ChunkEmbedding, ChunkEmbedding.chunk_id == DocumentChunk.id)
            .join(Document, Document.id == DocumentChunk.document_id)
            .where(Document.knowledge_base_id.in_(knowledge_base_ids))
            .order_by(similarity_expr.desc())
            .limit(limit)
        )

        result = await self.db.execute(query)

        rows = result.all()
        results = [
            {
                "chunk": row[0],
                "knowledge_base_id": row[1],
                "file_name": row[2],
                "similarity": float(row[3])
            }
            for row in rows
        ]

        return [item for item in results if item["similarity"] >= MIN_SIMILARITY]
