from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import LocationDisclosure


class Device(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "devices"
    __table_args__ = (
        UniqueConstraint("id", "site_id", name="uq_devices_id_site_id"),
        CheckConstraint(
            "private_latitude IS NULL OR private_latitude BETWEEN -90 AND 90",
            name="private_latitude_range",
        ),
        CheckConstraint(
            "private_longitude IS NULL OR private_longitude BETWEEN -180 AND 180",
            name="private_longitude_range",
        ),
        CheckConstraint(
            "device_type IN ('weather_station', 'soil_moisture_sensor', 'water_level_sensor')",
            name="device_type",
        ),
        CheckConstraint(
            "operational_override IS NULL OR operational_override IN ('maintenance', 'disabled')",
            name="operational_override",
        ),
        CheckConstraint(
            "location_disclosure IN ('withheld', 'approximate', 'private')",
            name="location_disclosure",
        ),
    )

    site_id: Mapped[UUID] = mapped_column(ForeignKey("sites.id", ondelete="RESTRICT"), index=True)
    external_device_id: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    device_type: Mapped[str] = mapped_column(String(40), nullable=False)
    operational_override: Mapped[str | None] = mapped_column(String(20))
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    private_latitude: Mapped[float | None]
    private_longitude: Mapped[float | None]
    location_disclosure: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=LocationDisclosure.WITHHELD.value,
    )
