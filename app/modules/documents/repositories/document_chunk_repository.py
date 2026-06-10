from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.documents.models.document_chunk_model import (
    DocumentChunk
)


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