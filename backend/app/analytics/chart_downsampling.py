from collections.abc import Iterable
from datetime import datetime
from decimal import Decimal
from typing import Protocol
from uuid import UUID


class TimeValuePoint(Protocol):
    @property
    def measurement_id(self) -> UUID: ...

    @property
    def measured_at(self) -> datetime: ...

    @property
    def value(self) -> Decimal: ...


def time_bucket_min_max[PointT: TimeValuePoint](
    points: Iterable[PointT],
    *,
    start: datetime,
    end: datetime,
    target_points: int,
) -> list[PointT]:
    """Select real extrema from deterministic time buckets, plus the first and last points."""
    if start >= end:
        raise ValueError("start must be earlier than end")
    if target_points < 4:
        raise ValueError("target_points must be at least 4")

    bucket_count = max((target_points - 2) // 2, 1)
    duration_seconds = (end - start).total_seconds()
    extrema: dict[int, tuple[PointT, PointT]] = {}
    first: PointT | None = None
    last: PointT | None = None

    for point in points:
        if first is None:
            first = point
        last = point
        elapsed_seconds = (point.measured_at - start).total_seconds()
        bucket_index = min(
            bucket_count - 1,
            max(0, int(elapsed_seconds / duration_seconds * bucket_count)),
        )
        current = extrema.get(bucket_index)
        if current is None:
            extrema[bucket_index] = (point, point)
            continue
        minimum, maximum = current
        if point.value < minimum.value:
            minimum = point
        if point.value > maximum.value:
            maximum = point
        extrema[bucket_index] = (minimum, maximum)

    if first is None or last is None:
        return []

    selected = {first.measurement_id: first, last.measurement_id: last}
    for minimum, maximum in extrema.values():
        selected[minimum.measurement_id] = minimum
        selected[maximum.measurement_id] = maximum
    return sorted(selected.values(), key=lambda point: (point.measured_at, point.measurement_id))
