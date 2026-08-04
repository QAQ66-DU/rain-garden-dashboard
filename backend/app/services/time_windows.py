from datetime import UTC, datetime, timedelta

from app.services.errors import ServiceError


def normalize_utc_timestamp(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ServiceError(
            422,
            "Timezone required",
            "Timestamps must include an explicit timezone offset.",
            "timezone_required",
        )
    return value.astimezone(UTC)


def validate_time_window(
    start: datetime, end: datetime, *, max_range_days: int
) -> tuple[datetime, datetime]:
    normalized_start = normalize_utc_timestamp(start)
    normalized_end = normalize_utc_timestamp(end)
    if normalized_start >= normalized_end:
        raise ServiceError(
            422,
            "Invalid time range",
            "The start timestamp must be earlier than the end timestamp.",
            "invalid_time_range",
        )
    if normalized_end - normalized_start > timedelta(days=max_range_days):
        raise ServiceError(
            422,
            "Time range too large",
            f"The maximum permitted range is {max_range_days} days.",
            "time_range_too_large",
        )
    return normalized_start, normalized_end


def resolve_measurement_window(
    start: datetime | None,
    end: datetime | None,
    reference_time: datetime,
    *,
    default_range_days: int,
    max_range_days: int,
) -> tuple[datetime, datetime, bool]:
    if (start is None) != (end is None):
        raise ServiceError(
            422,
            "Incomplete measurement range",
            "Provide both start and end timestamps, or omit both for the default range.",
            "incomplete_time_range",
        )
    default_applied = start is None
    if start is None or end is None:
        # Query windows remain half-open. Advance the exclusive default end by the
        # smallest stored timestamp unit so an observation at the dataset watermark
        # is included without changing explicit [start, end) requests.
        end = reference_time + timedelta(microseconds=1)
        start = end - timedelta(days=default_range_days)
    normalized_start, normalized_end = validate_time_window(
        start, end, max_range_days=max_range_days
    )
    return normalized_start, normalized_end, default_applied
