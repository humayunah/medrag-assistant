from sqlalchemy import String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDPk, UpdateTimestampMixin


class Tenant(UpdateTimestampMixin, Base):
    __tablename__ = "tenants"

    id: Mapped[UUIDPk]
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    settings: Mapped[dict | None] = mapped_column(JSONB, default=dict)

    # Relationships
    members = relationship("UserProfile", back_populates="tenant", lazy="selectin")
    documents = relationship("Document", back_populates="tenant", lazy="noload")
    invitations = relationship("Invitation", back_populates="tenant", lazy="noload")
