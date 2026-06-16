import uuid

from sqlalchemy import DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database.base import Base


class User(Base):
    """
    Canonical user identity — identified by canonical_id which is stable
    across channels.

    internal: canonical_id comes from the external resolver (employee_id, email)
    external: canonical_id = phone number (universal across WhatsApp and web)
    """

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    canonical_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    user_type: Mapped[str] = mapped_column(String(20), nullable=False)  # "internal" | "external"
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
