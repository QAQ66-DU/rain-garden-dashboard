from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from statistics import median
from uuid import UUID


@dataclass(frozen=True, slots=True)
class PeriodObservation:
    measurement_id: UUID
    measured_at: datetime
    received_at: datetime
    numeric_value: Decimal
    quality_flag: str


@dataclass(frozen=True, slots=True)
class MissingInterval:
    start: datetime
    end: datetime
    expected_slots: int


@dataclass(frozen=True, slots=True)
class ObservationTiming:
    measurement_id: UUID
    expected_slot_at: datetime | None
    timing_status: str
    transmission_delay_seconds: float


@dataclass(frozen=True, slots=True)
class CoverageResult:
    status: str
    status_detail: str
    expected_observations: int | None
    received_observations: int | None
    valid_observations: int | None
    flagged_observations: int | None
    missing_observations: int | None
    coverage_percentage: float | None
    late_observations: int
    out_of_tolerance_observations: int
    duplicate_slot_observations: int
    missing_intervals: tuple[MissingInterval, ...]
    observation_timing: tuple[ObservationTiming, ...]
    slot_observations: tuple[PeriodObservation, ...]


@dataclass(frozen=True, slots=True)
class SummaryStatistic:
    code: str
    label: str
    value: float
    observed_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class SummaryResult:
    status: str
    status_detail: str
    statistics: tuple[SummaryStatistic, ...]
    included_measurement_ids: frozenset[UUID]


def schedule_slots(
    start: datetime, end: datetime, interval_seconds: int, anchor_at: datetime
) -> tuple[datetime, ...]:
    """Return schedule-aligned slots in the half-open UTC window [start, end)."""
    if interval_seconds <= 0:
        raise ValueError("Reporting interval must be positive")
    interval = timedelta(seconds=interval_seconds)
    first_index = math.ceil((start - anchor_at).total_seconds() / interval_seconds)
    slot = anchor_at + first_index * interval
    slots: list[datetime] = []
    while slot < end:
        slots.append(slot)
        slot += interval
    return tuple(slots)


def _missing_intervals(
    missing_slots: list[datetime], interval_seconds: int, end: datetime
) -> tuple[MissingInterval, ...]:
    if not missing_slots:
        return ()
    interval = timedelta(seconds=interval_seconds)
    groups: list[MissingInterval] = []
    group_start = missing_slots[0]
    previous = missing_slots[0]
    count = 1
    for slot in missing_slots[1:]:
        if slot == previous + interval:
            previous = slot
            count += 1
            continue
        groups.append(MissingInterval(group_start, min(previous + interval, end), count))
        group_start = previous = slot
        count = 1
    groups.append(MissingInterval(group_start, min(previous + interval, end), count))
    return tuple(groups)


def calculate_coverage(
    observations: list[PeriodObservation],
    *,
    start: datetime,
    end: datetime,
    interval_seconds: int | None,
    anchor_at: datetime | None,
    jitter_tolerance_seconds: int | None,
) -> CoverageResult:
    ordered = sorted(observations, key=lambda item: (item.measured_at, item.measurement_id))
    if interval_seconds is None or anchor_at is None or jitter_tolerance_seconds is None:
        unavailable_timings = tuple(
            ObservationTiming(
                item.measurement_id,
                None,
                "schedule_unavailable",
                (item.received_at - item.measured_at).total_seconds(),
            )
            for item in ordered
        )
        return CoverageResult(
            status="unavailable",
            status_detail=(
                "Coverage unavailable — reporting interval, schedule anchor, or timestamp-jitter "
                "tolerance is not confirmed."
            ),
            expected_observations=None,
            received_observations=None,
            valid_observations=None,
            flagged_observations=None,
            missing_observations=None,
            coverage_percentage=None,
            late_observations=0,
            out_of_tolerance_observations=0,
            duplicate_slot_observations=0,
            missing_intervals=(),
            observation_timing=unavailable_timings,
            slot_observations=(),
        )

    slots = schedule_slots(start, end, interval_seconds, anchor_at)
    if not slots:
        no_slot_timings = tuple(
            ObservationTiming(
                item.measurement_id,
                None,
                "no_expected_slot",
                (item.received_at - item.measured_at).total_seconds(),
            )
            for item in ordered
        )
        return CoverageResult(
            status="no_expected_slots",
            status_detail="No schedule-aligned expected slots fall inside the selected window.",
            expected_observations=0,
            received_observations=0,
            valid_observations=0,
            flagged_observations=0,
            missing_observations=0,
            coverage_percentage=None,
            late_observations=0,
            out_of_tolerance_observations=len(ordered),
            duplicate_slot_observations=0,
            missing_intervals=(),
            observation_timing=no_slot_timings,
            slot_observations=(),
        )

    interval = timedelta(seconds=interval_seconds)
    slot_set = set(slots)
    filled: dict[datetime, PeriodObservation] = {}
    timings: list[ObservationTiming] = []
    late_count = 0
    out_of_tolerance_count = 0
    duplicate_count = 0
    for observation in ordered:
        delay = (observation.received_at - observation.measured_at).total_seconds()
        # Timestamp jitter controls measured_at slot assignment. Reception delay is assessed
        # separately: an observation is late only after a full reporting interval has elapsed.
        late = delay > interval_seconds
        if late:
            late_count += 1
        relative = (observation.measured_at - anchor_at).total_seconds() / interval_seconds
        lower_index = math.floor(relative)
        candidates = (
            anchor_at + lower_index * interval,
            anchor_at + (lower_index + 1) * interval,
        )
        nearest = min(candidates, key=lambda slot: (abs(slot - observation.measured_at), slot))
        offset = abs((observation.measured_at - nearest).total_seconds())
        if nearest not in slot_set or offset > jitter_tolerance_seconds:
            out_of_tolerance_count += 1
            status = "late_and_out_of_tolerance" if late else "out_of_tolerance"
            timings.append(ObservationTiming(observation.measurement_id, nearest, status, delay))
            continue
        if nearest in filled:
            duplicate_count += 1
            status = "late_duplicate_slot" if late else "duplicate_slot"
            timings.append(ObservationTiming(observation.measurement_id, nearest, status, delay))
            continue
        filled[nearest] = observation
        timings.append(
            ObservationTiming(
                observation.measurement_id,
                nearest,
                "late" if late else "on_schedule",
                delay,
            )
        )

    selected = tuple(filled[slot] for slot in slots if slot in filled)
    received = len(selected)
    valid = sum(item.quality_flag == "valid" for item in selected)
    flagged = received - valid
    missing_slots = [slot for slot in slots if slot not in filled]
    expected = len(slots)
    return CoverageResult(
        status="available",
        status_detail=(
            "Coverage counts unique schedule-aligned slots in the half-open UTC window [start, "
            "end); flagged slots are received but not valid. Late means received more than one "
            "reporting interval after measured_at."
        ),
        expected_observations=expected,
        received_observations=received,
        valid_observations=valid,
        flagged_observations=flagged,
        missing_observations=len(missing_slots),
        coverage_percentage=round(received / expected * 100, 2),
        late_observations=late_count,
        out_of_tolerance_observations=out_of_tolerance_count,
        duplicate_slot_observations=duplicate_count,
        missing_intervals=_missing_intervals(missing_slots, interval_seconds, end),
        observation_timing=tuple(timings),
        slot_observations=selected,
    )


def _statistic(code: str, label: str, observation: PeriodObservation) -> SummaryStatistic:
    return SummaryStatistic(code, label, float(observation.numeric_value), observation.measured_at)


def calculate_period_summary(
    metric_code: str,
    observations: list[PeriodObservation],
    coverage: CoverageResult,
    *,
    interval_seconds: int | None,
) -> SummaryResult:
    if coverage.status in {"available", "no_expected_slots"}:
        candidates = list(coverage.slot_observations)
    else:
        candidates = sorted(observations, key=lambda item: (item.measured_at, item.measurement_id))
    valid = [item for item in candidates if item.quality_flag == "valid"]
    if not valid:
        return SummaryResult(
            "no_data",
            "No valid observations are available in the selected half-open period.",
            (),
            frozenset(),
        )

    first = valid[0]
    latest = valid[-1]
    minimum = min(valid, key=lambda item: (item.numeric_value, item.measured_at))
    maximum = max(valid, key=lambda item: (item.numeric_value, item.measured_at))
    median_value = float(median(item.numeric_value for item in valid))
    included = frozenset(item.measurement_id for item in valid)
    statistics: list[SummaryStatistic]

    if metric_code == "soil_moisture":
        statistics = [
            _statistic("first", "First valid", first),
            _statistic("latest", "Latest valid", latest),
            _statistic("minimum", "Minimum", minimum),
            SummaryStatistic("median", "Median", median_value),
            _statistic("maximum", "Maximum", maximum),
            SummaryStatistic(
                "change",
                "Change",
                float(latest.numeric_value - first.numeric_value),
                latest.measured_at,
            ),
        ]
    elif metric_code in {
        "soil_temperature",
        "soil_electrical_conductivity",
    }:
        statistics = [
            _statistic("minimum", "Minimum", minimum),
            SummaryStatistic("median", "Median", median_value),
            _statistic("maximum", "Maximum", maximum),
            _statistic("latest", "Latest valid", latest),
        ]
    elif metric_code == "water_level":
        statistics = [
            _statistic("first", "First valid", first),
            _statistic("latest", "Latest valid", latest),
            _statistic("minimum", "Minimum", minimum),
            _statistic("maximum", "Maximum / peak", maximum),
            SummaryStatistic(
                "change",
                "Change",
                float(latest.numeric_value - first.numeric_value),
                latest.measured_at,
            ),
        ]
    elif metric_code == "rainfall_intensity":
        statistics = [
            _statistic("latest", "Latest valid", latest),
            _statistic("maximum", "Maximum intensity", maximum),
        ]
        coverage_sufficient = (
            interval_seconds is not None
            and coverage.status == "available"
            and coverage.expected_observations is not None
            and coverage.expected_observations > 0
            and coverage.valid_observations == coverage.expected_observations
            and coverage.out_of_tolerance_observations == 0
        )
        if coverage_sufficient:
            assert interval_seconds is not None
            above_zero = sum(item.numeric_value > 0 for item in valid)
            statistics.append(
                SummaryStatistic(
                    "duration_above_zero_seconds",
                    "Duration above zero",
                    float(above_zero * interval_seconds),
                )
            )
        else:
            return SummaryResult(
                "insufficient_data",
                "Rainfall duration above zero is unavailable because cadence or complete valid "
                "coverage is insufficient.",
                tuple(statistics),
                included,
            )
    elif metric_code in {
        "air_temperature",
        "relative_humidity",
        "light_intensity",
        "barometric_pressure",
    }:
        statistics = [
            _statistic("minimum", "Minimum", minimum),
            SummaryStatistic("median", "Median", median_value),
            _statistic("maximum", "Maximum", maximum),
        ]
    elif metric_code == "wind_speed":
        statistics = [
            SummaryStatistic("median", "Median", median_value),
            _statistic("maximum", "Maximum", maximum),
        ]
    elif metric_code == "wind_direction":
        statistics = [_statistic("latest", "Latest valid direction", latest)]
    elif metric_code == "uv_index":
        statistics = [_statistic("maximum", "Maximum", maximum)]
    else:
        statistics = [_statistic("latest", "Latest valid", latest)]

    return SummaryResult(
        "available",
        "Summary statistics use valid, unique schedule-slot observations only when a schedule is "
        "configured; flagged values are excluded.",
        tuple(statistics),
        included,
    )
