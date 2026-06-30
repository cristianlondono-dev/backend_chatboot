from uuid import UUID
from datetime import datetime
from typing import Any

from pydantic import BaseModel
from pydantic import ConfigDict


class CreateOrganizationRequest(BaseModel):
    trade_name: str
    business_name: str
    tax_id: str
    contact_phone: str | None = None
    address: str | None = None
    department: str | None = None
    city: str | None = None


class OrganizationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    trade_name: str
    business_name: str
    tax_id: str
    contact_phone: str | None
    address: str | None
    department: str | None
    city: str | None
    created_at: datetime


class OrganizationConfigRequest(BaseModel):
    openai_api_key: str | None = None
    storage_provider: str = "supabase"
    storage_credentials: dict[str, Any] | None = None
    storage_config: dict[str, Any] | None = None


class OrganizationConfigResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    openai_api_key: str | None
    storage_provider: str
    storage_credentials: dict[str, Any] | None
    storage_config: dict[str, Any] | None
    created_at: datetime
    updated_at: datetime
