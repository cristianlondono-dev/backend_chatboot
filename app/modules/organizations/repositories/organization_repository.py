from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.organizations.models.organization_model import Organization


class OrganizationRepository:

    def __init__(
        self,
        db: AsyncSession
    ):
        self.db = db

    async def get_all(self) -> list[Organization]:
        result = await self.db.execute(select(Organization).order_by(Organization.created_at.desc()))
        return list(result.scalars().all())

    async def delete(self, organization: Organization) -> None:
        await self.db.delete(organization)
        await self.db.commit()

    async def create(
        self,
        trade_name: str,
        business_name: str,
        tax_id: str,
        contact_phone: str | None = None,
        address: str | None = None,
        department: str | None = None,
        city: str | None = None
    ) -> Organization:

        organization = Organization(
            trade_name=trade_name,
            business_name=business_name,
            tax_id=tax_id,
            contact_phone=contact_phone,
            address=address,
            department=department,
            city=city
        )

        self.db.add(organization)

        await self.db.commit()

        await self.db.refresh(organization)

        return organization
    
    async def get_by_id(self, organization_id: UUID) -> Organization | None:
        return await self.db.get(Organization, organization_id)

    async def get_by_tax_id(
        self,
        tax_id: str
    ) -> Organization | None:

        query = select(Organization).where(
            Organization.tax_id == tax_id
        )

        result = await self.db.execute(query)

        return result.scalar_one_or_none()
    
    
    async def get_by_contact_phone(
        self,
        contact_phone: str
    ) -> Organization | None:

        query = select(Organization).where(
            Organization.contact_phone == contact_phone
        )

        result = await self.db.execute(query)

        return result.scalar_one_or_none()