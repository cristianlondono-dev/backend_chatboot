from uuid import UUID
from datetime import datetime
from typing import Any

from pydantic import BaseModel


class CreateAgentToolRequest(BaseModel):
    channel: str
    identifier_type: str
    user_type: str
    resolver_type: str = "none"
    resolver_config: dict[str, Any] | None = None
    field_mapping: dict[str, str] | None = None
    onboarding_questions: list[dict[str, str]] | None = None


class AgentToolResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    agent_id: UUID
    channel: str
    identifier_type: str
    user_type: str
    resolver_type: str
    field_mapping: dict[str, Any] | None
    onboarding_questions: list[dict[str, str]] | None
    is_active: bool
    created_at: datetime
