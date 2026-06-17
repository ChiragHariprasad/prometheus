from sqlalchemy import Column, String, Boolean, Text, Integer, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, TimestampMixin, UUIDMixin


class Organization(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    domain: Mapped[str | None] = mapped_column(String(255))
    logo_url: Mapped[str | None] = mapped_column(Text)
    plan: Mapped[str] = mapped_column(String(50), default="enterprise")
    settings: Mapped[dict] = mapped_column(JSONB, default=dict)
    features: Mapped[dict] = mapped_column(JSONB, default=dict)
    max_customers: Mapped[int] = mapped_column(Integer, default=100000)
    max_users: Mapped[int] = mapped_column(Integer, default=100)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    trial_ends_at = mapped_column(DateTime(timezone=True), nullable=True)
