from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDPrimaryKeyMixin, utc_now


class UplinkEvent(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "uplink_events"
    __table_args__ = (
        UniqueConstraint("source", "idempotency_key", name="uq_uplink_events_source_key"),
        UniqueConstraint("id", "device_id", name="uq_uplink_events_id_device_id"),
        CheckConstraint(
            "frame_counter IS NULL OR frame_counter >= 0", name="frame_counter_nonnegative"
        ),
        CheckConstraint("ingestion_status IN ('accepted', 'rejected')", name="ingestion_status"),
        Index("ix_uplink_events_device_received", "device_id", "received_at", "id"),
    )

    device_id: Mapped[UUID] = mapped_column(ForeignKey("devices.id", ondelete="RESTRICT"))
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(300), nullable=False)
    external_event_identifier: Mapped[str | None] = mapped_column(String(300))
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    measured_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    frame_counter: Mapped[int | None]
    raw_payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    payload_schema_version: Mapped[str | None] = mapped_column(String(100))
    ingestion_status: Mapped[str] = mapped_column(String(20), nullable=False)
    ingestion_error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
