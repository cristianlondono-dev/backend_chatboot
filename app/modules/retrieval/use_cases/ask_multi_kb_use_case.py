import time
from uuid import UUID
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging.loggers import rag_logger
from app.modules.embeddings.repositories.chunk_embedding_repository import ChunkEmbeddingRepository
from app.modules.llm.providers.openai_provider import OpenAIEmbeddingService
from app.modules.llm.services.openai_chat_service import OpenAIChatService

_NO_INFO = "No encontré información suficiente para responder."


class AskMultiKbUseCase:
    """Searches across an arbitrary list of knowledge base IDs."""

    def __init__(self, db: AsyncSession):
        self.embedding_repository = ChunkEmbeddingRepository(db)
        self.embedding_service = OpenAIEmbeddingService()
        self.chat_service = OpenAIChatService()

    @staticmethod
    def _build_context_block(item: dict) -> str:
        return (
            f"[Fuente: {item['file_name']} | Relevancia: {item['similarity']:.0%}]\n"
            f"{item['chunk'].content}"
        )

    def _build_prompt(self, context: str, question: str) -> str:
        return f"""Eres un asistente especializado en responder preguntas usando únicamente la información suministrada.

Cada fragmento de contexto incluye su fuente y relevancia entre corchetes.
Si la respuesta no existe en el contexto, responde exactamente: "{_NO_INFO}"

CONTEXTO:

{context}

PREGUNTA:

{question}
"""

    async def _get_context(
        self,
        knowledge_base_ids: list[UUID],
        question: str,
        top_k: int = 5
    ) -> str | None:
        question_embedding = self.embedding_service.generate_embedding(question)

        t0 = time.perf_counter()
        results = await self.embedding_repository.search_similar_in_kbs(
            knowledge_base_ids=knowledge_base_ids,
            embedding=question_embedding,
            limit=top_k
        )
        elapsed_ms = (time.perf_counter() - t0) * 1000

        kb_ids_str = [str(kb) for kb in knowledge_base_ids]
        chunk_scores = [
            f"{item['file_name']}#{str(item['chunk'].id)[:8]} ({item['similarity']:.3f})"
            for item in results
        ]
        rag_logger.info(
            f"Question: {question[:120]}\n"
            f"  KBs: {kb_ids_str}\n"
            f"  top_k: {top_k} | Chunks found: {len(results)}\n"
            f"  Scores: {chunk_scores}\n"
            f"  Search time: {elapsed_ms:.1f}ms"
        )

        if not results:
            return None

        return "\n\n---\n\n".join(self._build_context_block(item) for item in results)

    async def execute(
        self,
        knowledge_base_ids: list[UUID],
        question: str,
        top_k: int = 5
    ) -> str:
        context = await self._get_context(knowledge_base_ids, question, top_k=top_k)

        if context is None:
            return _NO_INFO

        prompt = self._build_prompt(context, question)
        return self.chat_service.generate_response(prompt)

    async def execute_stream(
        self,
        knowledge_base_ids: list[UUID],
        question: str,
        top_k: int = 5
    ) -> AsyncGenerator[str, None]:
        context = await self._get_context(knowledge_base_ids, question, top_k=top_k)

        if context is None:
            yield _NO_INFO
            return

        prompt = self._build_prompt(context, question)

        async for chunk in self.chat_service.generate_response_stream(prompt):
            yield chunk
