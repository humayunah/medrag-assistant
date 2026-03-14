import uuid

from sqlalchemy import Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import AppRole, Base, TimestampMixin


class UserProfile(TimestampMixin, Base):
    __tablename__ = "user_profiles"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
    )  # References auth.users(id) — set on signup, not auto-generated
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[AppRole] = mapped_column(
        Enum(AppRole, name="app_role", create_type=False),
        nullable=False,
        default=AppRole.STAFF,
    )
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Relationships
    tenant = relationship("Tenant", back_populates="members")
    documents = relationship(
        "Document", back_populates="uploaded_by_user", lazy="noload"
    )
    conversations = relationship("Conversation", back_populates="user", lazy="noload")
