from sqlalchemy import Column, String, Boolean, Text, Integer, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, TimestampMixin, UUIDMixin
import uuid


class User(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "users"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(Text)
    job_title: Mapped[str | None] = mapped_column(String(255))
    department: Mapped[str | None] = mapped_column(String(100))
    phone: Mapped[str | None] = mapped_column(String(50))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    mfa_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    mfa_secret: Mapped[str | None] = mapped_column(Text)
    last_login_at = mapped_column(DateTime(timezone=True), nullable=True)
    failed_login_attempts: Mapped[int] = mapped_column(Integer, default=0)
    locked_until = mapped_column(DateTime(timezone=True), nullable=True)
    password_changed_at = mapped_column(DateTime(timezone=True), nullable=False)
    password_expires_at = mapped_column(DateTime(timezone=True), nullable=True)
    reset_token: Mapped[str | None] = mapped_column(String(255), nullable=True)
    reset_token_expires_at = mapped_column(DateTime(timezone=True), nullable=True)
