from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid5

from app.analytics.chart_downsampling import time_bucket_min_max

NAMESPACE = UUID("00000000-0000-4000-8000-000000000001")


@dataclass(frozen=True)
class Point:
    measurement_id: UUID
    measured_at: datetime
    value: Decimal


def test_time_bucket_min_max_preserves_real_extrema_endpoints_and_order() -> None:
    start = datetime(2026, 8, 1, tzinfo=UTC)
    values = [Decimal("2"), Decimal("50"), Decimal("1"), Decimal("3"), Decimal("-40"), Decimal("4")]
    points = [
        Point(uuid5(NAMESPACE, str(index)), start + timedelta(hours=index), value)
        for index, value in enumerate(values)
    ]

    selected = time_bucket_min_max(
        points,
        start=start,
        end=start + timedelta(hours=6),
        target_points=4,
    )

    assert len(selected) <= 4
    assert selected[0] == points[0]
    assert selected[-1] == points[-1]
    assert points[1] in selected
    assert points[4] in selected
    assert [point.measured_at for point in selected] == sorted(
        point.measured_at for point in selected
    )
