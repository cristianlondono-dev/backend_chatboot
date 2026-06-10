from uuid import UUID
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class CreateAgentRequest(BaseModel):
    organization_id: UUID
    name: str
    description: str | None = None
    visibility: Literal["internal", "external", "both"] = "internal"


class AddKnowledgeBaseRequest(BaseModel):
    knowledge_base_id: UUID


class AgentKnowledgeBaseInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    knowledge_base_id: UUID
    added_at: datetime


class AgentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    name: str
    description: str | None
    visibility: str
    created_at: datetime
    knowledge_bases: list[AgentKnowledgeBaseInfo]


class AskAgentRequest(BaseModel):
    question: str


class AskAgentResponse(BaseModel):
    question: str
    answer: str
    sources: list[str] = []
