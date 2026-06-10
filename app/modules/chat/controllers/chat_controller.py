from fastapi import APIRouter

from app.modules.chat.schemas.chat_schema import ChatRequest, ChatResponse
from app.modules.chat.services.chat_service import ChatService

router = APIRouter(prefix="/chat", tags=["Chat"])

chat_service = ChatService()


@router.post("", response_model=ChatResponse)
async def chat(payload: ChatRequest):

    response = await chat_service.process_message(
        payload.message
    )

    return ChatResponse(
        response=response
    )