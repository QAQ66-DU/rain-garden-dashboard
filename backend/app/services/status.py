from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum


class ConnectivityStatus(StrEnum):
    UNKNOWN = "unknown"
    ONLINE = "online"
    STALE = "stale"
    OFFLINE = "offline"


@dataclass(frozen=True, slots=True)
class FreshnessResult:
    status: ConnectivityStatus
    reference_time: datetime
    age_seconds: int | None
    stale_after_minutes: int
    offline_after_minutes: int
    status_basis: str


def calculate_freshness(
    last_seen_at: datetime | None,
    reference_time: datetime,
    stale_after_minutes: int,
    offline_after_minutes: int,
    *,
    demo_mode: bool,
) -> FreshnessResult:
    basis = "dataset_reference_time" if demo_mode else "current_utc_time"
    if last_seen_at is None:
        return FreshnessResult(
            status=ConnectivityStatus.UNKNOWN,
            reference_time=reference_time,
            age_seconds=None,
            stale_after_minutes=stale_after_minutes,
            offline_after_minutes=offline_after_minutes,
            status_basis=basis,
        )

    age = max(reference_time - last_seen_at, timedelta(0))
    age_seconds = int(age.total_seconds())
    if age <= timedelta(minutes=stale_after_minutes):
        status = ConnectivityStatus.ONLINE
    elif age <= timedelta(minutes=offline_after_minutes):
        status = ConnectivityStatus.STALE
    else:
        status = ConnectivityStatus.OFFLINE
    return FreshnessResult(
        status=status,
        reference_time=reference_time,
        age_seconds=age_seconds,
        stale_after_minutes=stale_after_minutes,
        offline_after_minutes=offline_after_minutes,
        status_basis=basis,
    )
