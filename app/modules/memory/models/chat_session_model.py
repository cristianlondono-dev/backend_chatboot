import uuid

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database.base import Base


class ChatSession(Base):

    __tablename__ = "chat_sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agents.id"), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")  # "active" | "closed"

    # True mientras un humano está atendiendo esta conversación desde el panel
    # de Escalamientos — el bot no genera respuestas automáticas en ese estado.
    is_paused: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # None = onboarding complete. N = index of the next question to ask (external users only).
    onboarding_step: Mapped[int | None] = mapped_column(Integer, nullable=True)

    started_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_message_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    ended_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
