from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class SensorChannel(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "sensor_channels"
    __table_args__ = (
        UniqueConstraint("device_id", "channel_code", name="uq_sensor_channels_device_code"),
        UniqueConstraint("id", "device_id", name="uq_sensor_channels_id_device_id"),
        CheckConstraint("depth_cm IS NULL OR depth_cm >= 0", name="nonnegative_depth"),
        CheckConstraint(
            "expected_reporting_interval_seconds IS NULL OR "
            "expected_reporting_interval_seconds > 0",
            name="positive_reporting_interval",
        ),
        CheckConstraint(
            "reporting_jitter_tolerance_seconds IS NULL OR reporting_jitter_tolerance_seconds >= 0",
            name="nonnegative_reporting_jitter",
        ),
        CheckConstraint(
            "unit_confirmation_status IN ('pending', 'confirmed', 'synthetic_demo_only')",
            name="unit_confirmation_status",
        ),
        CheckConstraint(
            "unit_confirmation_status = 'pending' OR unit_code IS NOT NULL",
            name="confirmed_unit_requires_code",
        ),
    )

    device_id: Mapped[UUID] = mapped_column(
        ForeignKey("devices.id", ondelete="RESTRICT"), index=True
    )
    channel_code: Mapped[str] = mapped_column(String(100), nullable=False)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    metric_code: Mapped[str] = mapped_column(
        ForeignKey("metric_definitions.metric_code", ondelete="RESTRICT"), nullable=False
    )
    unit_code: Mapped[str | None] = mapped_column(
        ForeignKey("unit_definitions.unit_code", ondelete="RESTRICT")
    )
    unit_confirmation_status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="pending"
    )
    depth_cm: Mapped[float | None]
    position_label: Mapped[str | None] = mapped_column(String(200))
    expected_reporting_interval_seconds: Mapped[int | None] = mapped_column(Integer)
    reporting_schedule_anchor_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reporting_jitter_tolerance_seconds: Mapped[int | None] = mapped_column(Integer)
    water_level_reference_or_datum: Mapped[str | None] = mapped_column(String(200))
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    channel_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, nullable=False, default=dict
    )
