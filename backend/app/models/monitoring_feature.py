from uuid import UUID

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class MonitoringFeature(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "monitoring_features"
    __table_args__ = (
        UniqueConstraint("site_id", "public_slug", name="uq_monitoring_features_site_slug"),
        UniqueConstraint("id", "site_id", name="uq_monitoring_features_id_site_id"),
        CheckConstraint("feature_type IN ('swale', 'tree_pit', 'testbed')", name="feature_type"),
    )

    site_id: Mapped[UUID] = mapped_column(ForeignKey("sites.id", ondelete="RESTRICT"), index=True)
    public_slug: Mapped[str] = mapped_column(String(100), nullable=False)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    feature_type: Mapped[str] = mapped_column(String(30), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
