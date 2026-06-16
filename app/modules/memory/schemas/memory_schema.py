from uuid import UUID
from datetime import datetime

from pydantic import BaseModel


class ChatRequest(BaseModel):
    channel: str       # "whatsapp" | "teams" | "webchat" | "slack"
    channel_id: str    # the identifier in that channel (phone, email, employee_id)
    question: str


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
