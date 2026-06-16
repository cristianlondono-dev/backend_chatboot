import uuid

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database.base import Base


class UserChannel(Base):
    """
    Maps a channel-specific identifier to a canonical user.
    Enables cross-channel identity: the same person on WhatsApp and Teams
    resolves to the same User via their canonical_id.
    """

    __tablename__ = "user_channels"
    __table_args__ = (UniqueConstraint("channel", "channel_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    channel: Mapped[str] = mapped_column(String(50), nullable=False)    # "whatsapp" | "teams" | "webchat"
    channel_id: Mapped[str] = mapped_column(String(255), nullable=False) # "+57300..." | "user@empresa.com"
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
