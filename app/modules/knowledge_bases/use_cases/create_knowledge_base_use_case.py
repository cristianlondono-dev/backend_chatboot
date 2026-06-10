from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException
from app.core.logging.loggers import application_logger
from app.modules.knowledge_bases.models.knowledge_base_model import (
    KnowledgeBase
)
from app.modules.knowledge_bases.repositories.knowledge_base_repository import (
    KnowledgeBaseRepository
)
from app.modules.organizations.repositories.organization_repository import (
    OrganizationRepository
)


class CreateKnowledgeBaseUseCase:

    def __init__(
        self,
        db: AsyncSession
    ):
        self.repository = KnowledgeBaseRepository(db)
        self.org_repository = OrganizationRepository(db)

    async def execute(
        self,
        organization_id: UUID,
        name: str,
        description: str | None = None,
        area: str | None = None
    ) -> KnowledgeBase:

        if not await self.org_repository.get_by_id(organization_id):
            raise NotFoundException("Organización", str(organization_id))

        kb = await self.repository.create(
            organization_id=organization_id,
            name=name,
            description=description,
            area=area
        )

        application_logger.info(
            f"Knowledge base created: '{kb.name}' "
            f"| org={kb.organization_id} | area={kb.area or 'none'} | id={kb.id}"
        )

        return kb
