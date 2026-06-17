from uuid import UUID
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class UpsertOrganizationConfigRequest(BaseModel):
    openai_api_key: str | None = Field(
        default=None,
        description="OpenAI API key for this org. Falls back to the global env var if null."
    )
    storage_provider: Literal["supabase", "s3", "cloudinary"] = Field(
        default="supabase",
        description="Storage backend for document uploads."
    )
    storage_credentials: dict | None = Field(
        default=None,
        description=(
            "Provider-specific credentials.\n"
            "supabase → {url, service_key}\n"
            "s3       → {access_key_id, secret_access_key}\n"
            "cloudinary → {cloud_name, api_key, api_secret}"
        )
    )
    storage_config: dict | None = Field(
        default=None,
        description=(
            "Provider-specific config.\n"
            "supabase   → {bucket_name}\n"
            "s3         → {bucket, region}\n"
            "cloudinary → {folder}"
        )
    )


class OrganizationConfigResponse(BaseModel):
    id: UUID
    organization_id: UUID
    openai_api_key: str | None
    storage_provider: str
    storage_credentials: dict | None
    storage_config: dict | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
