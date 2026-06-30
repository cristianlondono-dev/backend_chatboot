import uuid

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database.base import Base


class OrganizationConfig(Base):

    __tablename__ = "organization_configs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )

    openai_api_key: Mapped[str | None] = mapped_column(String(255), nullable=True)

    storage_provider: Mapped[str] = mapped_column(String(50), nullable=False, default="supabase")

    storage_credentials: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    storage_config: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
