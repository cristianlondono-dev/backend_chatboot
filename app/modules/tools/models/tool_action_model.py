import uuid

from sqlalchemy import Boolean, DateTime, ForeignKey, JSON, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database.base import Base


class ToolAction(Base):
    """
    An executable action the chatbot can invoke during a conversation.

    The LLM uses OpenAI function-calling to trigger actions. Each ToolAction
    becomes one function definition visible to the model.

    action_type is a built-in key (e.g. "shopify_get_order") or "custom_rest"
    for arbitrary HTTP endpoints.

    credentials → sensitive data (tokens, API keys).
                  Store encrypted in production.
    config      → non-sensitive settings (store URL, calendar ID, timezone …).
    parameters_schema → JSON Schema object the LLM must fill when calling the action.
                        Auto-populated from the built-in action defaults; override as needed.
    """

    __tablename__ = "tool_actions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False
    )

    # Unique name within the agent — used as OpenAI function name
    name: Mapped[str] = mapped_column(String(100), nullable=False)

    # Built-in type or "custom_rest"
    action_type: Mapped[str] = mapped_column(String(100), nullable=False)

    # Description shown to the LLM so it knows when to call this action
    description: Mapped[str] = mapped_column(Text, nullable=False)

    # JSON Schema for the parameters the LLM must supply
    parameters_schema: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    # Sensitive credentials (API keys, OAuth tokens, etc.)
    credentials: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Non-sensitive config (store URL, calendar ID, timezone, etc.)
    config: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
