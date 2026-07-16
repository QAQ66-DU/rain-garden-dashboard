from typing import Any
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    ForeignKeyConstraint,
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
        ForeignKeyConstraint(
            ["metric_code", "unit_code"],
            ["metric_definitions.metric_code", "metric_definitions.unit_code"],
            name="fk_sensor_channels_metric_definition",
            ondelete="RESTRICT",
        ),
        CheckConstraint("depth_cm IS NULL OR depth_cm >= 0", name="nonnegative_depth"),
    )

    device_id: Mapped[UUID] = mapped_column(
        ForeignKey("devices.id", ondelete="RESTRICT"), index=True
    )
    channel_code: Mapped[str] = mapped_column(String(100), nullable=False)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    metric_code: Mapped[str] = mapped_column(String(100), nullable=False)
    unit_code: Mapped[str] = mapped_column(String(50), nullable=False)
    depth_cm: Mapped[float | None]
    position_label: Mapped[str | None] = mapped_column(String(200))
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    channel_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, nullable=False, default=dict
    )
