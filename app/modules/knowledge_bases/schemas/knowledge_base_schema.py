from uuid import UUID
from datetime import datetime

from pydantic import BaseModel
from pydantic import ConfigDict


class CreateKnowledgeBaseRequest(BaseModel):
    organization_id: UUID
    name: str
    description: str | None = None
    area: str | None = None


class KnowledgeBaseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    name: str
    description: str | None
    area: str | None
    created_at: datetime


class AskRequest(BaseModel):
    question: str


class AskResponse(BaseModel):
    question: str
    answer: str


class DocumentUploadResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    knowledge_base_id: UUID
    file_name: str
    file_type: str
    file_size: int
    status: str
    chunks_total: int
    chunks_processed: int
    created_at: datetime

    @property
    def progress_percentage(self) -> float:
        if self.chunks_total == 0:
            return 0.0
        return round(self.chunks_processed / self.chunks_total * 100, 1)
