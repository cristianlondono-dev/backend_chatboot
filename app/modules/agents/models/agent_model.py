import uuid

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database.base import Base


class Agent(Base):

    __tablename__ = "agents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id"),
        nullable=False
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )

    description: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True
    )

    # "internal" | "external" | "both"
    visibility: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="internal"
    )

    # "products" | "services" | "both"
    business_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="products",
        server_default="products"
    )

    escalation_notes: Mapped[str | None] = mapped_column(
        String(2000),
        nullable=True
    )

    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    knowledge_bases: Mapped[list["AgentKnowledgeBase"]] = relationship(  # noqa: F821
        "AgentKnowledgeBase",
        back_populates="agent",
        lazy="raise"
    )
