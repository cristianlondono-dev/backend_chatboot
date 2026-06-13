import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.memory.models.chat_session_model import ChatSession
from app.modules.memory.repositories.message_repository import MessageRepository
from app.modules.memory.repositories.conversation_summary_repository import ConversationSummaryRepository
from app.modules.llm.services.openai_chat_service import OpenAIChatService
from app.modules.llm.providers.openai_provider import OpenAIEmbeddingService
from app.core.logging.loggers import application_logger

_SUMMARY_PROMPT = """Resume la siguiente conversación en español de forma concisa (máximo 200 palabras).
Incluye: temas principales, decisiones tomadas e información relevante del usuario mencionada.

Conversación:
{conversation}

Resumen:"""

SUMMARY_THRESHOLD = 100  # summarize when session reaches this many messages


class SummarizationService:

    def __init__(self, db: AsyncSession):
        self.message_repo = MessageRepository(db)
        self.summary_repo = ConversationSummaryRepository(db)
        self.chat_service = OpenAIChatService()
        self.embedding_service = OpenAIEmbeddingService()

    async def summarize_if_needed(self, agent_id: uuid.UUID, user_id: uuid.UUID, session: ChatSession) -> bool:
        count = await self.message_repo.count(session.id)
        if count % SUMMARY_THRESHOLD != 0 or count == 0:
            return False

        messages = await self.message_repo.get_oldest_unsummarized(session.id, limit=80)
        if not messages:
            return False

        conversation = "\n".join(
            f"{msg.role.upper()}: {msg.content}" for msg in messages
        )
        prompt = _SUMMARY_PROMPT.format(conversation=conversation)
        summary_text = self.chat_service.generate_response(prompt)

        saved = await self.summary_repo.create(
            agent_id=agent_id,
            user_id=user_id,
            summary=summary_text,
            session_id=session.id
        )

        embedding = self.embedding_service.generate_embedding(summary_text)
        await self.summary_repo.create_embedding(
            summary_id=saved.id,
            model_name="text-embedding-3-small",
            embedding=embedding
        )

        application_logger.info(
            f"Summary generated | agent={agent_id} | user={user_id} | session={session.id} | msgs={count}"
        )
        return True
