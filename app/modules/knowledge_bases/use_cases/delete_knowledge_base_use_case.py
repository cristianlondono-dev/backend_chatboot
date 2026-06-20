from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException
from app.core.logging.loggers import application_logger
from app.modules.documents.repositories.document_chunk_repository import (
    DocumentChunkRepository
)
from app.modules.documents.repositories.document_repository import (
    DocumentRepository
)
from app.modules.embeddings.repositories.chunk_embedding_repository import (
    ChunkEmbeddingRepository
)
from app.modules.knowledge_bases.repositories.knowledge_base_repository import (
    KnowledgeBaseRepository
)


class DeleteKnowledgeBaseUseCase:

    def __init__(
        self,
        db: AsyncSession
    ):
        self.db = db
        self.kb_repository = KnowledgeBaseRepository(db)
        self.document_repository = DocumentRepository(db)
        self.chunk_repository = DocumentChunkRepository(db)
        self.embedding_repository = ChunkEmbeddingRepository(db)

    async def execute(self, knowledge_base_id: UUID) -> None:
        kb = await self.kb_repository.get_by_id(knowledge_base_id)
        if not kb:
            raise NotFoundException("Knowledge base", str(knowledge_base_id))

        # No FK has ON DELETE CASCADE configured, so children are removed
        # bottom-up before the knowledge base itself.
        await self.embedding_repository.delete_by_knowledge_base_id(knowledge_base_id)
        await self.chunk_repository.delete_by_knowledge_base_id(knowledge_base_id)
        await self.document_repository.delete_by_knowledge_base_id(knowledge_base_id)
        await self.kb_repository.delete(knowledge_base_id)

        await self.db.commit()

        application_logger.info(
            f"Knowledge base deleted: '{kb.name}' | org={kb.organization_id} | id={kb.id}"
        )
