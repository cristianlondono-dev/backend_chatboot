from uuid import UUID
from datetime import datetime

from pydantic import BaseModel


class EscalationOut(BaseModel):
    id: UUID
    agent_id: UUID
    agent_name: str
    organization_name: str
    channel: str | None
    channel_id: str | None
    summary: str
    is_resolved: bool
    created_at: datetime
    resolved_at: datetime | None


class UpdateEscalationRequest(BaseModel):
    is_resolved: bool


class EscalationUpdatedOut(BaseModel):
    id: UUID
    is_resolved: bool
    resolved_at: datetime | None

    model_config = {"from_attributes": True}


class EscalationDetailOut(BaseModel):
    id: UUID
    agent_id: UUID
    agent_name: str
    organization_name: str
    user_id: UUID
    session_id: UUID
    channel: str | None
    channel_id: str | None
    summary: str
    is_resolved: bool
    is_paused: bool
    created_at: datetime
    resolved_at: datetime | None


class EscalationMessageOut(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    role: str
    content: str
    created_at: datetime


class SendHumanMessageRequest(BaseModel):
    content: str


class TakeEscalationOut(BaseModel):
    session_id: UUID
    is_paused: bool
