import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.organizations.models.organization_config_model import OrganizationConfig


class OrganizationConfigRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_organization(self, organization_id: uuid.UUID) -> OrganizationConfig | None:
        result = await self.db.execute(
            select(OrganizationConfig).where(OrganizationConfig.organization_id == organization_id)
        )
        return result.scalar_one_or_none()

    async def upsert(
        self,
        organization_id: uuid.UUID,
        openai_api_key: str | None,
        storage_provider: str,
        storage_credentials: dict | None,
        storage_config: dict | None,
    ) -> OrganizationConfig:
        existing = await self.get_by_organization(organization_id)

        if existing:
            existing.openai_api_key = openai_api_key
            existing.storage_provider = storage_provider
            existing.storage_credentials = storage_credentials
            existing.storage_config = storage_config
            await self.db.flush()
            return existing

        record = OrganizationConfig(
            organization_id=organization_id,
            openai_api_key=openai_api_key,
            storage_provider=storage_provider,
            storage_credentials=storage_credentials,
            storage_config=storage_config,
        )
        self.db.add(record)
        await self.db.flush()
        await self.db.refresh(record)
        return record
