from datetime import UTC, datetime
from decimal import Decimal

import pytest
from app.ingestion.contracts import CanonicalMeasurement
from pydantic import ValidationError


def test_canonical_measurement_rejects_non_finite_values() -> None:
    with pytest.raises(ValidationError):
        CanonicalMeasurement(
            channel_code="rainfall",
            numeric_value=Decimal("NaN"),
            measured_at=datetime(2026, 6, 1, tzinfo=UTC),
        )


def test_canonical_measurement_requires_timezone() -> None:
    with pytest.raises(ValidationError):
        CanonicalMeasurement(
            channel_code="rainfall",
            numeric_value=Decimal("0"),
            measured_at=datetime(2026, 6, 1),
        )
