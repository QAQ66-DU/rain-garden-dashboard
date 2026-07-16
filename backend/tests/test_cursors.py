from datetime import UTC, datetime
from uuid import UUID

import pytest
from app.services.errors import ServiceError
from app.utils.cursors import (
    decode_measurement_cursor,
    decode_name_cursor,
    encode_cursor,
)


def test_measurement_cursor_round_trips() -> None:
    timestamp = datetime(2026, 6, 1, tzinfo=UTC)
    identifier = UUID("7adac86a-40b0-41fb-9b9d-304bf9344f98")
    cursor = encode_cursor({"measured_at": timestamp.isoformat(), "id": str(identifier)})

    assert decode_measurement_cursor(cursor) == (timestamp, identifier)


def test_invalid_cursor_has_safe_validation_error() -> None:
    with pytest.raises(ServiceError) as error:
        decode_name_cursor("not-a-cursor")

    assert error.value.status_code == 422
    assert error.value.error_code == "invalid_cursor"
