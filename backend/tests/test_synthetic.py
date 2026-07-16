from decimal import Decimal

from app.db.synthetic import (
    SYNTHETIC_REFERENCE_TIME,
    generate_synthetic_uplinks,
)


def test_synthetic_generation_is_deterministic() -> None:
    first = generate_synthetic_uplinks()
    second = generate_synthetic_uplinks()

    assert first == second
    assert len(first) == 501
    assert max(uplink.received_at for uplink in first) == SYNTHETIC_REFERENCE_TIME


def test_synthetic_data_contains_missing_and_invalid_cases() -> None:
    uplinks = generate_synthetic_uplinks()
    weather = [uplink for uplink in uplinks if uplink.external_device_id == "synthetic-weather-001"]
    soil = [uplink for uplink in uplinks if uplink.external_device_id == "synthetic-soil-001"]

    assert any(
        all(item.channel_code != "air_temperature" for item in uplink.measurements)
        for uplink in weather
    )
    assert any(
        all(item.channel_code != "soil_10cm" for item in uplink.measurements) for uplink in soil
    )
    assert any(
        item.channel_code == "relative_humidity" and item.numeric_value == Decimal("112.000")
        for uplink in weather
        for item in uplink.measurements
    )
