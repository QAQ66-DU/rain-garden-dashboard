from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, utc_now


class DeviceTelemetry(Base):
    """Latest operational status derived from a private replay event."""

    __tablename__ = "device_telemetry"
    __table_args__ = (
        CheckConstraint(
            "battery_percent IS NULL OR battery_percent BETWEEN 0 AND 100",
            name="battery_percent_range",
        ),
    )

    device_id: Mapped[UUID] = mapped_column(
        ForeignKey("devices.id", ondelete="CASCADE"), primary_key=True
    )
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    battery_percent: Mapped[Decimal | None] = mapped_column(Numeric(8, 3))
    firmware_version: Mapped[str | None] = mapped_column(String(100))
    hardware_version: Mapped[str | None] = mapped_column(String(100))
    measurement_interval_value: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    measurement_interval_unit: Mapped[str | None] = mapped_column(String(30))
    threshold_measurement_interval_value: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    latest_rssi_dbm: Mapped[Decimal | None] = mapped_column(Numeric(10, 3))
    latest_snr_db: Mapped[Decimal | None] = mapped_column(Numeric(10, 3))
    gateway_alias: Mapped[str | None] = mapped_column(String(100))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )
