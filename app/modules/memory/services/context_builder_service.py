from app.modules.memory.models.user_model import User
from app.modules.memory.models.message_model import Message


class ContextBuilderService:
    """Assembles the OpenAI messages list for the memory-enhanced chat."""

    def build_system_prompt(
        self,
        user: User,
        high_importance_memories: list,
        relevant_memories: list[dict],
        relevant_summaries: list[dict],
        rag_context: str | None
    ) -> str:
        sections: list[str] = [
            "Eres un asistente inteligente con memoria persistente. "
            "Conoces al usuario y tienes acceso a contexto de conversaciones previas. "
            "Responde siempre en español de forma clara y útil."
        ]

        # User profile — all data lives in high-importance memories
        if high_importance_memories:
            lines = [f"- {mem.memory}" for mem in high_importance_memories]
            sections.append("=== PERFIL DEL USUARIO ===\n" + "\n".join(lines))

        # Relevant memories
        if relevant_memories:
            lines = [
                f"- {item['memory'].memory} (relevancia: {item['similarity']:.0%})"
                for item in relevant_memories
            ]
            sections.append("=== MEMORIAS RELEVANTES ===\n" + "\n".join(lines))

        # Relevant summaries
        if relevant_summaries:
            lines = [
                f"- {item['summary'].summary[:300]} (relevancia: {item['similarity']:.0%})"
                for item in relevant_summaries
            ]
            sections.append("=== CONVERSACIONES ANTERIORES RELEVANTES ===\n" + "\n".join(lines))

        # RAG context
        if rag_context:
            sections.append("=== DOCUMENTOS RELEVANTES ===\n" + rag_context)
        else:
            sections.append(
                "=== DOCUMENTOS RELEVANTES ===\n"
                "No encontré documentos relevantes para esta pregunta."
            )

        return "\n\n".join(sections)

    def build_messages(
        self,
        system_prompt: str,
        recent_messages: list[Message]
    ) -> list[dict]:
        messages = [{"role": "system", "content": system_prompt}]
        for msg in recent_messages:
            messages.append({"role": msg.role, "content": msg.content})
        return messages
