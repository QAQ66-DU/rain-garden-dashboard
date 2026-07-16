from datetime import UTC, datetime, timedelta

from app.services.status import ConnectivityStatus, calculate_freshness

REFERENCE = datetime(2026, 6, 1, 12, tzinfo=UTC)


def status_for(age_minutes: int | None) -> ConnectivityStatus:
    last_seen = None if age_minutes is None else REFERENCE - timedelta(minutes=age_minutes)
    return calculate_freshness(
        last_seen,
        REFERENCE,
        stale_after_minutes=90,
        offline_after_minutes=180,
        demo_mode=True,
    ).status


def test_status_boundaries_are_explicit() -> None:
    assert status_for(None) is ConnectivityStatus.UNKNOWN
    assert status_for(90) is ConnectivityStatus.ONLINE
    assert status_for(91) is ConnectivityStatus.STALE
    assert status_for(180) is ConnectivityStatus.STALE
    assert status_for(181) is ConnectivityStatus.OFFLINE


def test_demo_status_reports_dataset_reference_basis() -> None:
    result = calculate_freshness(None, REFERENCE, 90, 180, demo_mode=True)

    assert result.status_basis == "dataset_reference_time"
    assert result.reference_time == REFERENCE
