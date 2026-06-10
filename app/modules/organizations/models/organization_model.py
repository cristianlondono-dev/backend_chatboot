import uuid

from sqlalchemy import DateTime
from sqlalchemy import String
from sqlalchemy import func

from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

from app.core.database.base import Base


class Organization(Base):

    __tablename__ = "organizations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    trade_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )

    business_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )

    tax_id: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        unique=True
    )

    contact_phone: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        unique=True
    )

    address: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True
    )

    department: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True
    )

    city: Mapped[str | None] = mapped_column(
        String(100),
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
        onupdate=func.now(),
        nullable=False
    )