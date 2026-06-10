from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import NotFoundException
from app.core.logging.loggers import application_logger, error_logger
from app.modules.documents.models.document_model import Document
from app.modules.documents.repositories.document_chunk_repository import (
    DocumentChunkRepository
)
from app.modules.documents.repositories.document_repository import (
    DocumentRepository
)
from app.modules.knowledge_bases.repositories.knowledge_base_repository import (
    KnowledgeBaseRepository
)
from app.modules.documents.services.document_extractor_service import (
    DocumentExtractorService
)
from app.modules.documents.services.text_chunker_service import (
    TextChunkerService
)
from app.modules.documents.services.text_cleaner_service import (
    TextCleanerService
)
from app.modules.embeddings.repositories.chunk_embedding_repository import (
    ChunkEmbeddingRepository
)
from app.modules.llm.providers.openai_provider import OpenAIEmbeddingService

_CONTENT_TYPES = {
    "pdf": "application/pdf",
    "csv": "text/csv",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "json": "application/json",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "txt": "text/plain",
}


class ProcessDocumentUseCase:

    def __init__(
        self,
        db: AsyncSession
    ):
        self.document_repository = DocumentRepository(db)
        self.kb_repository = KnowledgeBaseRepository(db)
        self.chunk_repository = DocumentChunkRepository(db)
        self.embedding_repository = ChunkEmbeddingRepository(db)

        self.extractor_service = DocumentExtractorService()
        self.text_cleaner = TextCleanerService()
        self.text_chunker = TextChunkerService()
        self.embedding_service = OpenAIEmbeddingService()

    def _upload_to_supabase(
        self,
        file_bytes: bytes,
        knowledge_base_id: UUID,
        file_name: str,
        file_type: str
    ) -> str | None:
        if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_KEY:
            return None
        try:
            from app.modules.storage.services.supabase_storage_service import (
                SupabaseStorageService
            )
            content_type = _CONTENT_TYPES.get(file_type, "application/octet-stream")
            storage = SupabaseStorageService()
            return storage.upload(
                file_bytes=file_bytes,
                knowledge_base_id=knowledge_base_id,
                file_name=file_name,
                content_type=content_type
            )
        except Exception:
            return None

    async def execute(
        self,
        knowledge_base_id,
        file_path: str,
        file_name: str,
        file_type: str,
        file_size: int,
        file_bytes: bytes | None = None
    ) -> Document:

        if not await self.kb_repository.get_by_id(knowledge_base_id):
            raise NotFoundException("Base de conocimiento", str(knowledge_base_id))

        file_url: str | None = None
        if file_bytes is not None:
            file_url = self._upload_to_supabase(
                file_bytes=file_bytes,
                knowledge_base_id=knowledge_base_id,
                file_name=file_name,
                file_type=file_type
            )

        document = await self.document_repository.create(
            knowledge_base_id=knowledge_base_id,
            file_name=file_name,
            file_type=file_type,
            file_size=file_size,
            file_url=file_url
        )

        application_logger.info(
            f"Document uploaded: '{file_name}' | type={file_type} "
            f"| size={file_size}B | kb={knowledge_base_id} | id={document.id}"
            + (f" | url={file_url}" if file_url else "")
        )

        try:
            await self.document_repository.update_status(
                document.id,
                "PROCESSING"
            )

            raw_text = self.extractor_service.extract(file_path, file_type)
            clean_text = self.text_cleaner.clean(raw_text)
            chunks = self.text_chunker.split_text(clean_text)

            chunks_total = len(chunks)

            await self.document_repository.update_progress(
                document_id=document.id,
                chunks_processed=0,
                chunks_total=chunks_total
            )

            for index, chunk_text in enumerate(chunks):

                chunk = await self.chunk_repository.create(
                    document_id=document.id,
                    chunk_index=index,
                    content=chunk_text,
                    chunk_metadata={}
                )

                embedding = self.embedding_service.generate_embedding(
                    chunk_text
                )

                await self.embedding_repository.create(
                    chunk_id=chunk.id,
                    model_name="text-embedding-3-small",
                    embedding=embedding
                )

                await self.document_repository.update_progress(
                    document_id=document.id,
                    chunks_processed=index + 1
                )

            await self.document_repository.update_status(
                document.id,
                "PROCESSED"
            )

            application_logger.info(
                f"Document processed: '{file_name}' | chunks={chunks_total} "
                f"| kb={knowledge_base_id} | id={document.id}"
            )

        except Exception as exc:
            await self.document_repository.update_status(
                document.id,
                "FAILED"
            )
            error_logger.error(
                f"Document processing failed: '{file_name}' | id={document.id} "
                f"| {type(exc).__name__}: {exc}",
                exc_info=True
            )
            raise

        return document
