import asyncio
import json
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException, UnprocessableException
from app.core.logging.loggers import application_logger, rag_logger
from app.modules.agents.repositories.agent_repository import AgentRepository
from app.modules.embeddings.repositories.chunk_embedding_repository import ChunkEmbeddingRepository
from app.modules.llm.providers.openai_provider import OpenAIEmbeddingService
from app.modules.llm.services.openai_chat_service import OpenAIChatService
from app.modules.memory.repositories.chat_session_repository import ChatSessionRepository
from app.modules.memory.repositories.conversation_summary_repository import ConversationSummaryRepository
from app.modules.memory.repositories.message_repository import MessageRepository
from app.modules.memory.repositories.user_channel_repository import UserChannelRepository
from app.modules.memory.repositories.user_memory_repository import UserMemoryRepository
from app.modules.memory.repositories.user_repository import UserRepository
from app.modules.memory.services.context_builder_service import ContextBuilderService
from app.modules.memory.services.memory_extraction_service import MemoryExtractionService
from app.modules.memory.services.onboarding_service import OnboardingService
from app.modules.memory.services.session_manager_service import SessionManagerService
from app.modules.memory.services.summarization_service import SummarizationService
from app.modules.tools.repositories.agent_tool_repository import AgentToolRepository
from app.modules.tools.repositories.tool_action_repository import ToolActionRepository
from app.modules.tools.services.identity_resolution_service import IdentityResolutionService
from app.modules.tools.services.tool_action_executor_service import ToolActionExecutorService

_MAX_TOOL_ROUNDS = 5  # guard against infinite tool-call loops


class ChatWithMemoryUseCase:

    def __init__(self, db: AsyncSession):
        self.db = db
        self.user_repo = UserRepository(db)
        self.channel_repo = UserChannelRepository(db)
        self.session_repo = ChatSessionRepository(db)
        self.message_repo = MessageRepository(db)
        self.memory_repo = UserMemoryRepository(db)
        self.summary_repo = ConversationSummaryRepository(db)
        self.agent_repo = AgentRepository(db)
        self.tool_repo = AgentToolRepository(db)
        self.tool_action_repo = ToolActionRepository(db)
        self.chunk_repo = ChunkEmbeddingRepository(db)
        self.session_manager = SessionManagerService(db)
        self.summarization = SummarizationService(db)
        self.context_builder = ContextBuilderService()
        self.onboarding = OnboardingService()
        self.embedding_service = OpenAIEmbeddingService()
        self.memory_extraction = MemoryExtractionService()
        self.identity_service = IdentityResolutionService()
        self.tool_executor = ToolActionExecutorService()
        # chat_service is created lazily in _resolve_chat_service()
        # so we can inject a per-org API key when available.
        self._chat_service: OpenAIChatService | None = None

    async def _resolve_chat_service(self, agent_id: uuid.UUID) -> OpenAIChatService:
        """Return a chat service using the org's OpenAI key, falling back to env."""
        if self._chat_service is not None:
            return self._chat_service

        from app.modules.organizations.repositories.organization_config_repository import (
            OrganizationConfigRepository,
        )

        agent = await self.agent_repo.get_by_id(agent_id)
        org_api_key: str | None = None
        if agent:
            config = await OrganizationConfigRepository(self.db).get_by_organization(
                agent.organization_id
            )
            if config:
                org_api_key = config.openai_api_key

        self._chat_service = OpenAIChatService(api_key=org_api_key)
        return self._chat_service

    async def execute(
        self,
        agent_id: uuid.UUID,
        channel: str,
        channel_id: str,
        question: str,
        top_k: int = 5
    ) -> dict:
        # 1. Validate agent exists
        if not await self.agent_repo.get_by_id(agent_id):
            raise NotFoundException("Agente", str(agent_id))

        # 2. Find the tool configured for this channel
        tool = await self.tool_repo.get_by_agent_and_channel(agent_id, channel)
        if not tool:
            raise UnprocessableException(
                f"El agente no tiene un tool configurado para el canal '{channel}'"
            )

        # 3. Resolve identity
        resolution = self.identity_service.resolve(tool, channel_id)
        if resolution is None:
            application_logger.info(
                f"[chat] Access denied | agent={agent_id} | channel={channel} | id={channel_id}"
            )
            raise UnprocessableException(
                "No estás registrado en el sistema. Contacta al administrador."
            )

        canonical_id = resolution["canonical_id"]
        profile_memories = resolution["memories"]

        # 4. Get or create user + link channel
        user, is_new_user = await self.user_repo.get_or_create(canonical_id, tool.user_type)
        await self.channel_repo.link(user.id, channel, channel_id)

        # 5. Store profile memories from resolver (only on first encounter)
        if is_new_user and profile_memories:
            for mem in profile_memories:
                saved = await self.memory_repo.create(
                    agent_id=agent_id,
                    user_id=user.id,
                    memory=mem["memory"],
                    importance=mem.get("importance", "high")
                )
                emb = self.embedding_service.generate_embedding(mem["memory"])
                await self.memory_repo.create_embedding(saved.id, "text-embedding-3-small", emb)
            application_logger.info(
                f"[chat] Profile loaded from resolver | user={user.id} | memories={len(profile_memories)}"
            )

        # 6. Get or create session (auto-close if inactive >30min)
        session = await self.session_manager.get_or_create(agent_id, user.id)

        # 7. Handle onboarding (external users only, when questions are configured)
        if session.onboarding_step is not None:
            return await self._handle_onboarding(agent_id, user.id, session, tool, question)

        # 8. Check if new external user needs onboarding
        questions = tool.onboarding_questions or []
        if is_new_user and tool.user_type == "external" and questions:
            await self.session_repo.advance_onboarding(session.id, 0)
            greeting = self.onboarding.greeting_with_question(question, questions[0]["question"])
            await self.message_repo.create(session.id, "assistant", greeting)
            return {
                "session_id": session.id,
                "user_id": user.id,
                "question": question,
                "answer": greeting
            }

        # 9. Normal chat flow
        return await self._chat(agent_id, user.id, session, question, top_k)

    async def _handle_onboarding(self, agent_id, user_id, session, tool, user_answer: str) -> dict:
        questions = tool.onboarding_questions or []
        step = session.onboarding_step

        if step < len(questions):
            q = questions[step]
            label = OnboardingService.extract_memory_label(q)
            memory_text = f"{label}: {user_answer}"
            saved = await self.memory_repo.create(
                agent_id=agent_id, user_id=user_id,
                memory=memory_text, importance="high"
            )
            emb = self.embedding_service.generate_embedding(memory_text)
            await self.memory_repo.create_embedding(saved.id, "text-embedding-3-small", emb)
            await self.message_repo.create(session.id, "user", user_answer)

        next_step = step + 1

        if next_step < len(questions):
            await self.session_repo.advance_onboarding(session.id, next_step)
            next_q_text = questions[next_step]["question"]
            response = self.onboarding.transition_with_question(user_answer, next_q_text)
            await self.message_repo.create(session.id, "assistant", response)
            return {
                "session_id": session.id,
                "user_id": user_id,
                "question": user_answer,
                "answer": response
            }

        await self.session_repo.advance_onboarding(session.id, None)
        completion = self.onboarding.completion_message()
        await self.message_repo.create(session.id, "assistant", completion)
        return {
            "session_id": session.id,
            "user_id": user_id,
            "question": user_answer,
            "answer": completion
        }

    async def _chat(self, agent_id, user_id, session, question: str, top_k: int) -> dict:
        chat_service = await self._resolve_chat_service(agent_id)
        question_embedding = self.embedding_service.generate_embedding(question)

        # Parallel retrieval
        recent_msgs, high_mems, rel_mems, rel_sums = await asyncio.gather(
            self.message_repo.get_recent(session.id, limit=20),
            self.memory_repo.get_high_importance(agent_id, user_id),
            self.memory_repo.search_similar(agent_id, user_id, question_embedding, limit=5),
            self.summary_repo.search_similar(agent_id, user_id, question_embedding, limit=3)
        )

        # RAG context
        kb_ids = await self.agent_repo.get_knowledge_base_ids(agent_id)
        rag_context: str | None = None
        if kb_ids:
            rag_results = await self.chunk_repo.search_similar_in_kbs(
                knowledge_base_ids=kb_ids, embedding=question_embedding, limit=top_k
            )
            if rag_results:
                rag_context = "\n\n---\n\n".join(
                    f"[Fuente: {r['file_name']} | Relevancia: {r['similarity']:.0%}]\n{r['chunk'].content}"
                    for r in rag_results
                )
            rag_logger.info(
                f"[memory-chat] Question: {question[:120]}\n"
                f"  KBs: {[str(k) for k in kb_ids]} | top_k={top_k} | Chunks: {len(rag_results)}"
            )

        # Build prompt and message list
        user_obj = await self._get_user(user_id)
        system_prompt = self.context_builder.build_system_prompt(
            user=user_obj,
            high_importance_memories=high_mems,
            relevant_memories=rel_mems,
            relevant_summaries=rel_sums,
            rag_context=rag_context
        )
        messages = self.context_builder.build_messages(system_prompt, recent_msgs)
        messages.append({"role": "user", "content": question})

        # Load active tool actions and convert to OpenAI function definitions
        tool_actions = await self.tool_action_repo.get_active_by_agent(agent_id)
        openai_tools = [
            {
                "type": "function",
                "function": {
                    "name": ta.name,
                    "description": ta.description,
                    "parameters": ta.parameters_schema,
                },
            }
            for ta in tool_actions
        ] if tool_actions else None

        # Tool-calling loop — the model may request several rounds of tools
        answer: str = ""
        tool_action_map = {ta.name: ta for ta in tool_actions}

        for _ in range(_MAX_TOOL_ROUNDS):
            result = chat_service.generate_with_tools(messages, openai_tools)

            if not result.has_tool_calls:
                answer = result.content or ""
                break

            # Append the assistant's tool-call message so the model keeps context
            messages.append(result.raw_message)

            # Execute each tool call and append tool-result messages
            for tc in result.tool_calls:
                ta = tool_action_map.get(tc.name)
                if ta:
                    tool_result = await self.tool_executor.execute(ta, tc.arguments)
                else:
                    tool_result = {"error": f"Unknown tool '{tc.name}'"}

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps(tool_result, ensure_ascii=False),
                })
        else:
            # Safety net — should never happen with well-behaved models
            answer = "Lo siento, no pude completar la acción solicitada."

        # Persist messages and post-process
        await self.message_repo.create(session.id, "user", question)
        await self.message_repo.create(session.id, "assistant", answer)
        await self.session_manager.touch(session.id)

        facts = self.memory_extraction.extract(question)
        for fact in facts:
            saved = await self.memory_repo.create(
                agent_id=agent_id, user_id=user_id,
                memory=fact["memory"], importance=fact.get("importance", "medium")
            )
            emb = self.embedding_service.generate_embedding(fact["memory"])
            await self.memory_repo.create_embedding(saved.id, "text-embedding-3-small", emb)

        await self.summarization.summarize_if_needed(agent_id, user_id, session)

        return {
            "session_id": session.id,
            "user_id": user_id,
            "question": question,
            "answer": answer
        }

    async def _get_user(self, user_id: uuid.UUID):
        from sqlalchemy import select
        from app.modules.memory.models.user_model import User
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one()
