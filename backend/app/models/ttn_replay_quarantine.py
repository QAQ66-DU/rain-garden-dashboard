from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDPrimaryKeyMixin, utc_now


class TTNReplayQuarantine(UUIDPrimaryKeyMixin, Base):
    """Private preserve-first storage for replay events that cannot be associated safely."""

    __tablename__ = "ttn_replay_quarantine"
    __table_args__ = (
        UniqueConstraint("source", "idempotency_key", name="uq_ttn_quarantine_source_key"),
    )

    source: Mapped[str] = mapped_column(String(50), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(64), nullable=False)
    event_name: Mapped[str | None] = mapped_column(String(100))
    received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    failure_code: Mapped[str] = mapped_column(String(100), nullable=False)
    parser_version: Mapped[str] = mapped_column(String(100), nullable=False)
    failure_detail: Mapped[str | None] = mapped_column(Text)
    raw_payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
