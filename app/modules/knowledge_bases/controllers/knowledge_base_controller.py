import json
import os
import tempfile
from uuid import UUID

from fastapi import APIRouter
from fastapi import Depends
from fastapi import File
from fastapi import HTTPException
from fastapi import Query
from fastapi import UploadFile
from fastapi import status
from fastapi.responses import StreamingResponse

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database.database import get_db
from app.modules.documents.repositories.document_repository import (
    DocumentRepository
)
from app.modules.documents.services.document_extractor_service import (
    SUPPORTED_TYPES
)
from app.modules.knowledge_bases.repositories.knowledge_base_repository import (
    KnowledgeBaseRepository
)
from app.modules.knowledge_bases.schemas.knowledge_base_schema import (
    AskRequest,
    AskResponse,
    CreateKnowledgeBaseRequest,
    DocumentUploadResponse,
    KnowledgeBaseResponse
)
from app.modules.knowledge_bases.use_cases.create_knowledge_base_use_case import (
    CreateKnowledgeBaseUseCase
)
from app.modules.knowledge_bases.use_cases.delete_knowledge_base_use_case import (
    DeleteKnowledgeBaseUseCase
)
from app.modules.documents.use_cases.process_document_use_case import (
    ProcessDocumentUseCase
)
from app.modules.retrieval.use_cases.ask_knowledge_base_use_case import (
    AskKnowledgeBaseUseCase
)

router = APIRouter(
    prefix="/knowledge-bases",
    tags=["Knowledge Bases"]
)

_CONTENT_TYPE_MAP: dict[str, str] = {
    "application/pdf": "pdf",
    "text/csv": "csv",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "application/json": "json",
    "text/plain": "txt",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "xlsx",
    "application/vnd.ms-excel": "xlsx",
}


def _resolve_file_type(content_type: str | None, filename: str) -> str:
    if content_type and content_type in _CONTENT_TYPE_MAP:
        resolved = _CONTENT_TYPE_MAP[content_type]
        if resolved in SUPPORTED_TYPES:
            return resolved

    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    if extension in SUPPORTED_TYPES:
        return extension

    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail=(
            f"Unsupported file type. "
            f"Accepted: {', '.join(sorted(SUPPORTED_TYPES))}"
        )
    )


@router.post(
    "",
    response_model=KnowledgeBaseResponse,
    status_code=status.HTTP_201_CREATED
)
async def create_knowledge_base(
    body: CreateKnowledgeBaseRequest,
    db: AsyncSession = Depends(get_db)
):
    use_case = CreateKnowledgeBaseUseCase(db)

    return await use_case.execute(
        organization_id=body.organization_id,
        name=body.name,
        description=body.description,
        area=body.area
    )


@router.get(
    "/{knowledge_base_id}",
    response_model=KnowledgeBaseResponse
)
async def get_knowledge_base(
    knowledge_base_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    kb = await KnowledgeBaseRepository(db).get_by_id(knowledge_base_id)
    if not kb:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge base no encontrada")
    return kb


@router.delete(
    "/{knowledge_base_id}",
    status_code=status.HTTP_204_NO_CONTENT
)
async def delete_knowledge_base(
    knowledge_base_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    await DeleteKnowledgeBaseUseCase(db).execute(knowledge_base_id)


@router.get(
    "/{knowledge_base_id}/documents",
    response_model=list[DocumentUploadResponse]
)
async def list_knowledge_base_documents(
    knowledge_base_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    return await DocumentRepository(db).get_by_knowledge_base_id(knowledge_base_id)


@router.post(
    "/{knowledge_base_id}/documents",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_201_CREATED
)
async def upload_document(
    knowledge_base_id: UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    file_type = _resolve_file_type(file.content_type, file.filename or "")

    file_bytes = await file.read()
    file_size = len(file_bytes)

    suffix = f".{file_type}"

    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name

    try:
        use_case = ProcessDocumentUseCase(db)

        document = await use_case.execute(
            knowledge_base_id=knowledge_base_id,
            file_path=tmp_path,
            file_name=file.filename or tmp_path,
            file_type=file_type,
            file_size=file_size,
            file_bytes=file_bytes
        )
    finally:
        os.unlink(tmp_path)

    return document


@router.post(
    "/{knowledge_base_id}/ask",
    response_model=AskResponse
)
async def ask_knowledge_base(
    knowledge_base_id: UUID,
    body: AskRequest,
    top_k: int = Query(default=5, ge=1, le=20, description="Número de chunks a recuperar"),
    db: AsyncSession = Depends(get_db)
):
    use_case = AskKnowledgeBaseUseCase(db)

    answer = await use_case.execute(
        knowledge_base_id=knowledge_base_id,
        question=body.question,
        top_k=top_k
    )

    return AskResponse(question=body.question, answer=answer)


@router.post("/{knowledge_base_id}/ask/stream")
async def ask_knowledge_base_stream(
    knowledge_base_id: UUID,
    body: AskRequest,
    top_k: int = Query(default=5, ge=1, le=20, description="Número de chunks a recuperar"),
    db: AsyncSession = Depends(get_db)
):
    use_case = AskKnowledgeBaseUseCase(db)

    async def event_stream():
        async for chunk in use_case.execute_stream(knowledge_base_id, body.question, top_k=top_k):
            yield f"data: {json.dumps(chunk)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
