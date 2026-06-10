from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.documents.models.document_model import Document


class DocumentRepository:

    def __init__(
        self,
        db: AsyncSession
    ):
        self.db = db

    async def create(
        self,
        knowledge_base_id,
        file_name: str,
        file_type: str,
        file_size: int,
        file_url: str | None = None
    ) -> Document:

        document = Document(
            knowledge_base_id=knowledge_base_id,
            file_name=file_name,
            file_type=file_type,
            file_size=file_size,
            file_url=file_url
        )

        self.db.add(document)

        await self.db.commit()

        await self.db.refresh(document)

        return document

    async def update_status(
        self,
        document_id: UUID,
        status: str
    ) -> None:

        document = await self.db.get(Document, document_id)

        if document:
            document.status = status
            await self.db.commit()

    async def update_progress(
        self,
        document_id: UUID,
        chunks_processed: int,
        chunks_total: int | None = None
    ) -> None:

        document = await self.db.get(Document, document_id)

        if document:
            document.chunks_processed = chunks_processed

            if chunks_total is not None:
                document.chunks_total = chunks_total

            await self.db.commit()