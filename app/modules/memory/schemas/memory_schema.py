from uuid import UUID
from datetime import datetime

from pydantic import BaseModel


class ChatRequest(BaseModel):
    external_id: str
    question: str
    name: str | None = None


class ChatResponse(BaseModel):
    session_id: UUID
    user_id: UUID
    question: str
    answer: str


class MessageOut(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    role: str
    content: str
    token_count: int | None
    created_at: datetime


class MemoryOut(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    memory: str
    importance: str
    created_at: datetime
