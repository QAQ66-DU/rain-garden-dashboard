from sqlalchemy import Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class MetricDefinition(TimestampMixin, Base):
    __tablename__ = "metric_definitions"

    metric_code: Mapped[str] = mapped_column(String(100), primary_key=True)
    unit_code: Mapped[str] = mapped_column(String(50), primary_key=True)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    unit_symbol: Mapped[str] = mapped_column(String(50), nullable=False)
    meaning: Mapped[str] = mapped_column(Text, nullable=False)
    expected_type: Mapped[str] = mapped_column(String(50), nullable=False)
    valid_min: Mapped[float | None]
    valid_max: Mapped[float | None]
    validity_basis: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(String(200), nullable=False)
    scientifically_confirmed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
