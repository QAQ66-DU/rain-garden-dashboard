from sqlalchemy import Boolean, CheckConstraint, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class MetricDefinition(TimestampMixin, Base):
    __tablename__ = "metric_definitions"
    __table_args__ = (
        CheckConstraint(
            "metric_group IN ('hydrology', 'soil', 'weather', 'operational')",
            name="metric_group",
        ),
    )

    metric_code: Mapped[str] = mapped_column(String(100), primary_key=True)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    metric_group: Mapped[str] = mapped_column(String(30), nullable=False)
    meaning: Mapped[str] = mapped_column(Text, nullable=False)
    expected_type: Mapped[str] = mapped_column(String(50), nullable=False)
    valid_min: Mapped[float | None]
    valid_max: Mapped[float | None]
    validity_basis: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(String(200), nullable=False)
    scientifically_confirmed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
