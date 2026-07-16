import math
import random
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid5

from app.ingestion.contracts import CanonicalMeasurement, CanonicalUplink

SYNTHETIC_NAMESPACE = UUID("ab3a16d9-3a8c-4e17-8af0-5f7ce1687264")
SYNTHETIC_RANDOM_SEED = 20260716
SYNTHETIC_REFERENCE_TIME = datetime(2026, 6, 1, 12, tzinfo=UTC)
SYNTHETIC_CADENCE = timedelta(hours=1)
SYNTHETIC_DAYS = 7


@dataclass(frozen=True, slots=True)
class SyntheticDeviceSpec:
    external_device_id: str
    end_offset_hours: int


DEVICE_SPECS = (
    SyntheticDeviceSpec("synthetic-weather-001", 0),
    SyntheticDeviceSpec("synthetic-soil-001", 2),
    SyntheticDeviceSpec("synthetic-water-001", 4),
)


def stable_uuid(value: str) -> UUID:
    return uuid5(SYNTHETIC_NAMESPACE, value)


def _decimal(value: float) -> Decimal:
    return Decimal(f"{value:.3f}")


def _weather_values(index: int, rng: random.Random) -> dict[str, Decimal]:
    hour = index % 24
    rainfall_pulses = {18: 0.8, 19: 2.1, 20: 1.4, 75: 3.2, 76: 1.7, 126: 0.6}
    humidity = 72 + 12 * math.cos((hour / 24) * 2 * math.pi) + rng.uniform(-2, 2)
    if index == SYNTHETIC_DAYS * 24 - 6:
        humidity = 112
    return {
        "rainfall": _decimal(rainfall_pulses.get(index, 0.0)),
        "air_temperature": _decimal(
            11 + 4 * math.sin(((hour - 6) / 24) * 2 * math.pi) + rng.uniform(-0.5, 0.5)
        ),
        "relative_humidity": _decimal(humidity),
        "battery": _decimal(3.72 - index * 0.0003 + rng.uniform(-0.01, 0.01)),
        "rssi": _decimal(-86 + rng.uniform(-5, 5)),
        "snr": _decimal(7 + rng.uniform(-2, 2)),
    }


def _soil_values(index: int, rng: random.Random) -> dict[str, Decimal]:
    return {
        "soil_10cm": _decimal(31 + 2.8 * math.sin(index / 29) + rng.uniform(-0.4, 0.4)),
        "soil_30cm": _decimal(37 + 1.4 * math.sin(index / 41) + rng.uniform(-0.25, 0.25)),
        "battery": _decimal(3.65 - index * 0.0002 + rng.uniform(-0.008, 0.008)),
        "rssi": _decimal(-91 + rng.uniform(-4, 4)),
        "snr": _decimal(5 + rng.uniform(-1.5, 1.5)),
    }


def _water_values(index: int, rng: random.Random) -> dict[str, Decimal]:
    return {
        "water_level": _decimal(84 + 8 * math.sin(index / 17) + rng.uniform(-1.2, 1.2)),
        "battery": _decimal(3.81 - index * 0.0002 + rng.uniform(-0.008, 0.008)),
        "rssi": _decimal(-88 + rng.uniform(-4, 4)),
        "snr": _decimal(6 + rng.uniform(-1.5, 1.5)),
    }


def generate_synthetic_uplinks() -> tuple[CanonicalUplink, ...]:
    rng = random.Random(SYNTHETIC_RANDOM_SEED)  # noqa: S311 - deterministic demo data
    first_time = SYNTHETIC_REFERENCE_TIME - timedelta(days=SYNTHETIC_DAYS)
    uplinks: list[CanonicalUplink] = []

    for device in DEVICE_SPECS:
        final_time = SYNTHETIC_REFERENCE_TIME - timedelta(hours=device.end_offset_hours)
        timestamp = first_time
        index = 0
        while timestamp <= final_time:
            if device.external_device_id == "synthetic-weather-001":
                values = _weather_values(index, rng)
                if index in {22, 94}:
                    values.pop("air_temperature")
            elif device.external_device_id == "synthetic-soil-001":
                values = _soil_values(index, rng)
                if index in {24, 88}:
                    values.pop("soil_10cm")
                if index == 42:
                    values.pop("soil_30cm")
            else:
                values = _water_values(index, rng)
                if index in {37, 91}:
                    values.pop("water_level")

            stamp = timestamp.isoformat()
            measurements = [
                CanonicalMeasurement(
                    measurement_id=stable_uuid(
                        f"measurement:{device.external_device_id}:{channel_code}:{stamp}"
                    ),
                    channel_code=channel_code,
                    numeric_value=value,
                    measured_at=timestamp,
                )
                for channel_code, value in sorted(values.items())
            ]
            uplinks.append(
                CanonicalUplink(
                    event_id=stable_uuid(f"uplink:{device.external_device_id}:{stamp}"),
                    source="synthetic",
                    idempotency_key=f"synthetic:{device.external_device_id}:{stamp}",
                    external_device_id=device.external_device_id,
                    external_event_identifier=f"synthetic-{device.external_device_id}-{index:04d}",
                    received_at=timestamp,
                    measured_at=timestamp,
                    payload_schema_version="synthetic-v1",
                    raw_payload={
                        "synthetic": True,
                        "generator_cadence_minutes": 60,
                        "sequence": index,
                        "values": {key: str(value) for key, value in sorted(values.items())},
                    },
                    measurements=measurements,
                )
            )
            timestamp += SYNTHETIC_CADENCE
            index += 1
    return tuple(uplinks)
