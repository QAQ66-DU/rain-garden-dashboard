from sqlalchemy import Boolean, CheckConstraint, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import LocationDisclosure


class Site(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "sites"
    __table_args__ = (
        CheckConstraint(
            "private_latitude IS NULL OR private_latitude BETWEEN -90 AND 90",
            name="private_latitude_range",
        ),
        CheckConstraint(
            "private_longitude IS NULL OR private_longitude BETWEEN -180 AND 180",
            name="private_longitude_range",
        ),
        CheckConstraint(
            "location_disclosure IN ('withheld', 'approximate', 'private')",
            name="location_disclosure",
        ),
    )

    name: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text)
    public_location_label: Mapped[str] = mapped_column(String(300), nullable=False)
    location_disclosure: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=LocationDisclosure.WITHHELD.value,
    )
    private_latitude: Mapped[float | None]
    private_longitude: Mapped[float | None]
    display_timezone: Mapped[str] = mapped_column(String(100), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
