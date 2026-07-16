from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDPrimaryKeyMixin, utc_now


class Measurement(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "measurements"
    __table_args__ = (
        ForeignKeyConstraint(
            ["sensor_channel_id", "device_id"],
            ["sensor_channels.id", "sensor_channels.device_id"],
            name="fk_measurements_channel_device",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["uplink_event_id", "device_id"],
            ["uplink_events.id", "uplink_events.device_id"],
            name="fk_measurements_uplink_device",
            ondelete="RESTRICT",
        ),
        UniqueConstraint(
            "uplink_event_id",
            "sensor_channel_id",
            "measured_at",
            name="uq_measurements_event_channel_time",
        ),
        Index("ix_measurements_channel_time_id", "sensor_channel_id", "measured_at", "id"),
        Index("ix_measurements_device_time_id", "device_id", "measured_at", "id"),
        CheckConstraint(
            "quality_flag IN ('valid', 'out_of_range', 'suspect')", name="quality_flag"
        ),
    )

    uplink_event_id: Mapped[UUID]
    device_id: Mapped[UUID] = mapped_column(ForeignKey("devices.id", ondelete="RESTRICT"))
    sensor_channel_id: Mapped[UUID]
    numeric_value: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    measured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    quality_flag: Mapped[str] = mapped_column(String(20), nullable=False)
    quality_notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
