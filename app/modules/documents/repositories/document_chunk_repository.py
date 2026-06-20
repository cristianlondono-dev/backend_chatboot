from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.documents.models.document_chunk_model import (
    DocumentChunk
)
from app.modules.documents.models.document_model import Document


class DocumentChunkRepository:

    def __init__(
        self,
        db: AsyncSession
    ):
        self.db = db

    async def create(
        self,
        document_id,
        chunk_index: int,
        content: str,
        chunk_metadata: dict | None = None
    ) -> DocumentChunk:

        chunk = DocumentChunk(
            document_id=document_id,
            chunk_index=chunk_index,
            content=content,
            chunk_metadata=chunk_metadata
        )

        self.db.add(chunk)

        await self.db.commit()

        await self.db.refresh(chunk)

        return chunk

    async def delete_by_knowledge_base_id(self, knowledge_base_id: UUID) -> None:
        document_ids_subquery = select(Document.id).where(
            Document.knowledge_base_id == knowledge_base_id
        )
        await self.db.execute(
            delete(DocumentChunk).where(DocumentChunk.document_id.in_(document_ids_subquery))
        )