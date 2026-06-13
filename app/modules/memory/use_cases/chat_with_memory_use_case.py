import asyncio
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging.loggers import rag_logger
from app.modules.agents.repositories.agent_repository import AgentRepository
from app.modules.embeddings.repositories.chunk_embedding_repository import ChunkEmbeddingRepository
from app.modules.llm.providers.openai_provider import OpenAIEmbeddingService
from app.modules.llm.services.openai_chat_service import OpenAIChatService
from app.modules.memory.repositories.user_repository import UserRepository
from app.modules.memory.repositories.message_repository import MessageRepository
from app.modules.memory.repositories.user_memory_repository import UserMemoryRepository
from app.modules.memory.repositories.conversation_summary_repository import ConversationSummaryRepository
from app.modules.memory.services.session_manager_service import SessionManagerService
from app.modules.memory.services.memory_extraction_service import MemoryExtractionService
from app.modules.memory.services.summarization_service import SummarizationService
from app.modules.memory.services.context_builder_service import ContextBuilderService


class ChatWithMemoryUseCase:

    def __init__(self, db: AsyncSession):
        self.db = db
        self.user_repo = UserRepository(db)
        self.message_repo = MessageRepository(db)
        self.memory_repo = UserMemoryRepository(db)
        self.summary_repo = ConversationSummaryRepository(db)
        self.agent_repo = AgentRepository(db)
        self.chunk_repo = ChunkEmbeddingRepository(db)
        self.session_manager = SessionManagerService(db)
        self.summarization = SummarizationService(db)
        self.context_builder = ContextBuilderService()
        self.embedding_service = OpenAIEmbeddingService()
        self.memory_extraction = MemoryExtractionService()
        self.chat_service = OpenAIChatService()

    async def execute(
        self,
        agent_id: uuid.UUID,
        external_id: str,
        question: str,
        user_name: str | None = None,
        top_k: int = 5
    ) -> dict:
        # 1. Get or create user and session
        user = await self.user_repo.get_or_create(external_id, name=user_name)
        session = await self.session_manager.get_or_create(agent_id, user.id)

        # 2. Embed the question once — reuse for all semantic searches
        question_embedding = self.embedding_service.generate_embedding(question)

        # 3. Parallel: recent messages + memory search + summary search + RAG
        recent_msgs_task = self.message_repo.get_recent(session.id, limit=20)
        high_mem_task = self.memory_repo.get_high_importance(agent_id, user.id)
        rel_mem_task = self.memory_repo.search_similar(agent_id, user.id, question_embedding, limit=5)
        rel_sum_task = self.summary_repo.search_similar(agent_id, user.id, question_embedding, limit=3)

        recent_messages, high_memories, relevant_memories, relevant_summaries = await asyncio.gather(
            recent_msgs_task, high_mem_task, rel_mem_task, rel_sum_task
        )

        # 4. RAG context (only if agent has knowledge bases)
        kb_ids = await self.agent_repo.get_knowledge_base_ids(agent_id)
        rag_context: str | None = None
        if kb_ids:
            rag_results = await self.chunk_repo.search_similar_in_kbs(
                knowledge_base_ids=kb_ids,
                embedding=question_embedding,
                limit=top_k
            )
            if rag_results:
                rag_context = "\n\n---\n\n".join(
                    f"[Fuente: {r['file_name']} | Relevancia: {r['similarity']:.0%}]\n{r['chunk'].content}"
                    for r in rag_results
                )
            rag_logger.info(
                f"[memory-chat] Question: {question[:120]}\n"
                f"  KBs: {[str(k) for k in kb_ids]} | Chunks: {len(rag_results if kb_ids else [])}"
            )

        # 5. Build system prompt + conversation history messages
        system_prompt = self.context_builder.build_system_prompt(
            user=user,
            high_importance_memories=high_memories,
            relevant_memories=relevant_memories,
            relevant_summaries=relevant_summaries,
            rag_context=rag_context
        )
        messages = self.context_builder.build_messages(system_prompt, recent_messages)
        messages.append({"role": "user", "content": question})

        # 6. Generate response
        answer = self.chat_service.generate_response_with_messages(messages)

        # 7. Persist messages and update session activity
        await self.message_repo.create(session.id, "user", question)
        await self.message_repo.create(session.id, "assistant", answer)
        await self.session_manager.touch(session.id)

        # 8. Extract and store memories from user message
        facts = self.memory_extraction.extract(question)
        for fact in facts:
            saved_memory = await self.memory_repo.create(
                agent_id=agent_id,
                user_id=user.id,
                memory=fact["memory"],
                importance=fact.get("importance", "medium")
            )
            mem_embedding = self.embedding_service.generate_embedding(fact["memory"])
            await self.memory_repo.create_embedding(saved_memory.id, "text-embedding-3-small", mem_embedding)

        # 9. Summarize if threshold reached
        await self.summarization.summarize_if_needed(agent_id, user.id, session)

        return {
            "session_id": session.id,
            "user_id": user.id,
            "question": question,
            "answer": answer
        }
