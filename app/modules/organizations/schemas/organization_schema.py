from uuid import UUID
from datetime import datetime

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
