from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging.loggers import application_logger
from app.modules.organizations.models.organization_model import Organization
from app.modules.organizations.repositories.organization_repository import (
    OrganizationRepository
)
from app.modules.organizations.exceptions.organization_exceptions import (
    OrganizationAlreadyExistsException
)


class CreateOrganizationUseCase:

    def __init__(
        self,
        db: AsyncSession
    ):
        self.repository = OrganizationRepository(db)

    async def execute(
        self,
        trade_name: str,
        business_name: str,
        tax_id: str,
        contact_phone: str | None = None,
        address: str | None = None,
        department: str | None = None,
        city: str | None = None
    ) -> Organization:

        existing_organization = await self.repository.get_by_tax_id(
            tax_id
        )

        if existing_organization:
            raise OrganizationAlreadyExistsException(
                f"Organization with tax_id {tax_id} already exists"
            )

        organization = await self.repository.create(
            trade_name=trade_name,
            business_name=business_name,
            tax_id=tax_id,
            contact_phone=contact_phone,
            address=address,
            department=department,
            city=city
        )

        application_logger.info(
            f"Organization created: '{organization.trade_name}' "
            f"| tax_id={organization.tax_id} | id={organization.id}"
        )

        return organization