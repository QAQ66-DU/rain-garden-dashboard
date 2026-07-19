from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class UnitDefinition(TimestampMixin, Base):
    __tablename__ = "unit_definitions"

    unit_code: Mapped[str] = mapped_column(String(50), primary_key=True)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    unit_symbol: Mapped[str] = mapped_column(String(50), nullable=False)
    meaning: Mapped[str] = mapped_column(Text, nullable=False)
