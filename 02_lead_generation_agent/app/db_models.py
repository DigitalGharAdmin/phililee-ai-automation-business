"""Portable lead row, with database-enforced commercial identity uniqueness."""

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import DateTime, Integer, String, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Lead(Base):
    __tablename__ = "leads"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(320))
    company: Mapped[str | None] = mapped_column(String(200))
    message: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(30))
    service_interest: Mapped[str | None] = mapped_column(String(40))
    budget_range: Mapped[str | None] = mapped_column(String(30))
    timeline: Mapped[str | None] = mapped_column(String(30))
    company_size: Mapped[str | None] = mapped_column(String(30))
    lead_score: Mapped[int] = mapped_column(Integer)
    qualification: Mapped[str] = mapped_column(String(10))
    priority: Mapped[str] = mapped_column(String(10))
    recommended_action: Mapped[str] = mapped_column(String(10))
    ai_status: Mapped[str | None] = mapped_column(String(10))
    ai_assessment: Mapped[dict | None] = mapped_column(JSON)
    final_qualification: Mapped[str | None] = mapped_column(String(10))
    final_priority: Mapped[str | None] = mapped_column(String(10))
    final_recommended_action: Mapped[str | None] = mapped_column(String(10))
    dedup_key: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)
