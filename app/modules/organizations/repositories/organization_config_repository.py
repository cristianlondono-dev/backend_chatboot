from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.organizations.models.organization_config_model import OrganizationConfig


class OrganizationConfigRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_organization_id(self, organization_id: UUID) -> OrganizationConfig | None:
        result = await self.db.execute(
            select(OrganizationConfig).where(OrganizationConfig.organization_id == organization_id)
        )
        return result.scalar_one_or_none()

    async def upsert(
        self,
        organization_id: UUID,
        openai_api_key: str | None,
        storage_provider: str,
        storage_credentials: dict | None,
        storage_config: dict | None,
    ) -> OrganizationConfig:
        config = await self.get_by_organization_id(organization_id)

        if config is None:
            config = OrganizationConfig(organization_id=organization_id)
            self.db.add(config)

        config.openai_api_key = openai_api_key
        config.storage_provider = storage_provider
        config.storage_credentials = storage_credentials
        config.storage_config = storage_config

        await self.db.commit()
        await self.db.refresh(config)
        return config
