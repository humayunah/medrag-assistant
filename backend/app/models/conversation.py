import uuid

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDPk, UpdateTimestampMixin


class Conversation(UpdateTimestampMixin, Base):
    __tablename__ = "conversations"

    id: Mapped[UUIDPk]
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("user_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Relationships
    user = relationship("UserProfile", back_populates="conversations")
    messages = relationship(
        "QueryMessage",
        back_populates="conversation",
        cascade="all, delete-orphan",
        lazy="noload",
        order_by="QueryMessage.created_at",
    )
