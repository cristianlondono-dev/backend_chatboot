import uuid

from sqlalchemy import Boolean, DateTime, ForeignKey, JSON, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database.base import Base


class AgentTool(Base):
    """
    Configures how users connect to an agent (channel) and how their
    identity is resolved (resolver).

    user_type="internal": resolver is mandatory — if the user is not found
                          in the external source, access is denied.
    user_type="external": no resolver needed — phone is the canonical identity,
                          onboarding_questions are asked on first contact.
    """

    __tablename__ = "agent_tools"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False)

    # Channel configuration
    channel: Mapped[str] = mapped_column(String(50), nullable=False)          # "whatsapp" | "teams" | "webchat" | "slack"
    identifier_type: Mapped[str] = mapped_column(String(50), nullable=False)  # "phone" | "email" | "employee_id"
    user_type: Mapped[str] = mapped_column(String(20), nullable=False)        # "internal" | "external"

    # Resolver configuration (how to validate/fetch user data from external source)
    resolver_type: Mapped[str] = mapped_column(String(50), nullable=False, default="none")  # "none" | "rest_api"
    resolver_config: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # {
    #   "url": "https://hr.empresa.com/api/empleados/{identifier}",
    #   "method": "GET",
    #   "headers": {"Authorization": "Bearer TOKEN"},
    #   "response_path": "data",        # optional: dot-separated path to employee object
    #   "canonical_field": "employee_id" # field to use as canonical user ID
    # }

    # Maps external fields to memory templates
    field_mapping: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # { "NOMBRE": "Nombre: {value}", "CARGO": "Trabaja como {value}" }

    # Onboarding questions (used for external users or as fallback)
    onboarding_questions: Mapped[list | None] = mapped_column(JSON, nullable=True)
    # [{"question": "¿Cuál es tu nombre?", "memory_key": "Nombre"}, ...]

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
