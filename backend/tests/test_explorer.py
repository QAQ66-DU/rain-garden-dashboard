from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from app.analytics.explorer import (
    PeriodObservation,
    calculate_coverage,
    calculate_period_summary,
    schedule_slots,
)

ANCHOR = datetime(2026, 1, 1, tzinfo=UTC)


def observation(
    identifier: int,
    hour: int,
    minute: int,
    value: str,
    *,
    quality_flag: str = "valid",
    received_delay_minutes: int = 0,
) -> PeriodObservation:
    measured = ANCHOR + timedelta(hours=hour, minutes=minute)
    return PeriodObservation(
        measurement_id=UUID(int=identifier),
        measured_at=measured,
        received_at=measured + timedelta(minutes=received_delay_minutes),
        numeric_value=Decimal(value),
        quality_flag=quality_flag,
    )


def test_schedule_slots_are_aligned_and_half_open() -> None:
    slots = schedule_slots(
        ANCHOR + timedelta(minutes=10),
        ANCHOR + timedelta(minutes=50),
        3600,
        ANCHOR,
    )

    assert slots == ()
    assert schedule_slots(ANCHOR, ANCHOR + timedelta(hours=2), 3600, ANCHOR) == (
        ANCHOR,
        ANCHOR + timedelta(hours=1),
    )

    observations = [observation(1, 0, 20, "4.2")]
    coverage = calculate_coverage(
        observations,
        start=ANCHOR + timedelta(minutes=10),
        end=ANCHOR + timedelta(minutes=50),
        interval_seconds=3600,
        anchor_at=ANCHOR,
        jitter_tolerance_seconds=300,
    )
    summary = calculate_period_summary("water_level", observations, coverage, interval_seconds=3600)
    assert coverage.status == "no_expected_slots"
    assert summary.status == "no_data"


def test_coverage_deduplicates_slots_and_labels_timing() -> None:
    observations = [
        observation(1, 0, 1, "0"),
        observation(2, 0, 3, "9"),
        observation(
            3,
            1,
            0,
            "112",
            quality_flag="out_of_range",
            received_delay_minutes=70,
        ),
        observation(4, 2, 20, "5"),
    ]

    result = calculate_coverage(
        observations,
        start=ANCHOR,
        end=ANCHOR + timedelta(hours=4),
        interval_seconds=3600,
        anchor_at=ANCHOR,
        jitter_tolerance_seconds=300,
    )

    assert result.expected_observations == 4
    assert result.received_observations == 2
    assert result.valid_observations == 1
    assert result.flagged_observations == 1
    assert result.missing_observations == 2
    assert result.coverage_percentage == 50.0
    assert result.late_observations == 1
    assert result.out_of_tolerance_observations == 1
    assert result.duplicate_slot_observations == 1
    assert result.slot_observations[0].numeric_value == Decimal("0")
    assert result.missing_intervals[0].start == ANCHOR + timedelta(hours=2)
    assert result.missing_intervals[0].end == ANCHOR + timedelta(hours=4)
    assert result.missing_intervals[0].expected_slots == 2
    statuses = {item.measurement_id: item.timing_status for item in result.observation_timing}
    assert statuses == {
        UUID(int=1): "on_schedule",
        UUID(int=2): "duplicate_slot",
        UUID(int=3): "late",
        UUID(int=4): "out_of_tolerance",
    }


def test_coverage_is_unavailable_without_confirmed_schedule() -> None:
    result = calculate_coverage(
        [observation(1, 0, 0, "0")],
        start=ANCHOR,
        end=ANCHOR + timedelta(hours=1),
        interval_seconds=None,
        anchor_at=None,
        jitter_tolerance_seconds=None,
    )

    assert result.status == "unavailable"
    assert result.expected_observations is None
    assert result.coverage_percentage is None
    assert result.observation_timing[0].timing_status == "schedule_unavailable"


def test_rainfall_duration_requires_complete_valid_coverage() -> None:
    observations = [
        observation(1, 0, 0, "0"),
        observation(2, 1, 0, "1.2"),
        observation(3, 2, 0, "2.4"),
        observation(4, 3, 0, "0"),
    ]
    complete = calculate_coverage(
        observations,
        start=ANCHOR,
        end=ANCHOR + timedelta(hours=4),
        interval_seconds=3600,
        anchor_at=ANCHOR,
        jitter_tolerance_seconds=300,
    )
    summary = calculate_period_summary(
        "rainfall_intensity", observations, complete, interval_seconds=3600
    )

    duration = next(
        item for item in summary.statistics if item.code == "duration_above_zero_seconds"
    )
    assert summary.status == "available"
    assert duration.value == 7200

    incomplete_observations = observations[:-1]
    incomplete = calculate_coverage(
        incomplete_observations,
        start=ANCHOR,
        end=ANCHOR + timedelta(hours=4),
        interval_seconds=3600,
        anchor_at=ANCHOR,
        jitter_tolerance_seconds=300,
    )
    insufficient = calculate_period_summary(
        "rainfall_intensity",
        incomplete_observations,
        incomplete,
        interval_seconds=3600,
    )
    assert insufficient.status == "insufficient_data"
    assert all(item.code != "duration_above_zero_seconds" for item in insufficient.statistics)


def test_wind_direction_uses_latest_value_without_arithmetic_mean() -> None:
    observations = [observation(1, 0, 0, "359"), observation(2, 1, 0, "1")]
    coverage = calculate_coverage(
        observations,
        start=ANCHOR,
        end=ANCHOR + timedelta(hours=2),
        interval_seconds=3600,
        anchor_at=ANCHOR,
        jitter_tolerance_seconds=0,
    )

    summary = calculate_period_summary(
        "wind_direction", observations, coverage, interval_seconds=3600
    )

    assert [(item.code, item.value) for item in summary.statistics] == [("latest", 1.0)]
