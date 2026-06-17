import uuid

from sqlalchemy import DateTime, ForeignKey, JSON, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database.base import Base


class OrganizationConfig(Base):
    """
    Per-organization runtime configuration for multi-tenant deployments.

    Overrides global env vars (OPENAI_API_KEY, Supabase, etc.) when set.
    Falls back to environment defaults when fields are None.

    storage_provider: "supabase" | "s3" | "cloudinary"
    storage_credentials:
      supabase  → { "url": "...", "service_key": "..." }
      s3        → { "access_key_id": "...", "secret_access_key": "..." }
      cloudinary→ { "cloud_name": "...", "api_key": "...", "api_secret": "..." }
    storage_config:
      supabase  → { "bucket_name": "documents" }
      s3        → { "bucket": "...", "region": "us-east-1" }
      cloudinary→ { "folder": "chatbot-documents" }
    """

    __tablename__ = "organization_configs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        unique=True
    )

    # LLM provider — falls back to env OPENAI_API_KEY if None
    openai_api_key: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Storage provider
    storage_provider: Mapped[str] = mapped_column(String(50), nullable=False, default="supabase")
    storage_credentials: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    storage_config: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
