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
SYNTHETIC_SCHEDULE_ANCHOR = SYNTHETIC_REFERENCE_TIME - timedelta(days=7)
SYNTHETIC_JITTER_TOLERANCE_SECONDS = 300
SYNTHETIC_DAYS = 7


@dataclass(frozen=True, slots=True)
class SyntheticDeviceSpec:
    external_device_id: str
    device_group: str
    sequence: int
    end_offset_hours: int


DEVICE_SPECS = (
    SyntheticDeviceSpec("synthetic-v2-swale-weather-001", "weather", 1, 0),
    SyntheticDeviceSpec("synthetic-v2-swale-soil-001", "soil", 1, 0),
    SyntheticDeviceSpec("synthetic-v2-swale-soil-002", "soil", 2, 1),
    SyntheticDeviceSpec("synthetic-v2-swale-soil-003", "soil", 3, 2),
    SyntheticDeviceSpec("synthetic-v2-swale-water-001", "water", 1, 3),
    SyntheticDeviceSpec("synthetic-v2-swale-water-002", "water", 2, 4),
    SyntheticDeviceSpec("synthetic-v2-swale-water-003", "water", 3, 5),
)

LEGACY_SYNTHETIC_EXTERNAL_IDS = frozenset(
    {"synthetic-weather-001", "synthetic-soil-001", "synthetic-water-001"}
)
CONFIRMED_SYNTHETIC_EXTERNAL_IDS = frozenset(
    {device.external_device_id for device in DEVICE_SPECS} | {"synthetic-v2-tree-pit-probe-001"}
)
KNOWN_SYNTHETIC_EXTERNAL_IDS = LEGACY_SYNTHETIC_EXTERNAL_IDS | CONFIRMED_SYNTHETIC_EXTERNAL_IDS


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
        "rainfall_intensity": _decimal(rainfall_pulses.get(index, 0.0)),
        "air_temperature": _decimal(
            11 + 4 * math.sin(((hour - 6) / 24) * 2 * math.pi) + rng.uniform(-0.5, 0.5)
        ),
        "relative_humidity": _decimal(humidity),
        "wind_speed": _decimal(max(0, 2.5 + 1.2 * math.sin(index / 9) + rng.uniform(-0.3, 0.3))),
        "wind_direction": _decimal((210 + index * 7 + rng.uniform(-8, 8)) % 360),
        "light_intensity": _decimal(max(0, 12000 * math.sin((hour / 24) * math.pi))),
        "uv_index": _decimal(max(0, 4.5 * math.sin((hour / 24) * math.pi))),
        "barometric_pressure": _decimal(1012 + 4 * math.sin(index / 31)),
    }


def _soil_values(index: int, sequence: int, rng: random.Random) -> dict[str, Decimal]:
    return {
        "soil_moisture": _decimal(
            29 + sequence * 2 + 2.4 * math.sin(index / 29) + rng.uniform(-0.4, 0.4)
        ),
        "soil_temperature": _decimal(
            10 + 2.2 * math.sin((index % 24) / 24 * 2 * math.pi) + rng.uniform(-0.2, 0.2)
        ),
        "soil_electrical_conductivity": _decimal(
            480 + sequence * 35 + 20 * math.sin(index / 37) + rng.uniform(-5, 5)
        ),
    }


def _water_values(index: int, sequence: int, rng: random.Random) -> dict[str, Decimal]:
    return {
        "water_level": _decimal(
            72 + sequence * 8 + 7 * math.sin(index / 17) + rng.uniform(-1.2, 1.2)
        )
    }


def generate_synthetic_uplinks() -> tuple[CanonicalUplink, ...]:
    rng = random.Random(SYNTHETIC_RANDOM_SEED)  # noqa: S311 - deterministic demo data
    uplinks: list[CanonicalUplink] = []

    for device in DEVICE_SPECS:
        final_time = SYNTHETIC_REFERENCE_TIME - timedelta(hours=device.end_offset_hours)
        timestamp = SYNTHETIC_SCHEDULE_ANCHOR
        index = 0
        while timestamp <= final_time:
            if device.device_group == "weather":
                values = _weather_values(index, rng)
                if index in {22, 94}:
                    values.pop("air_temperature")
            elif device.device_group == "soil":
                values = _soil_values(index, device.sequence, rng)
                if index in {24 + device.sequence, 88}:
                    values.pop("soil_moisture")
            else:
                values = _water_values(index, device.sequence, rng)
                if index in {37 + device.sequence, 91}:
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
                    idempotency_key=f"synthetic-v2:{device.external_device_id}:{stamp}",
                    external_device_id=device.external_device_id,
                    external_event_identifier=f"synthetic-v2-{device.sequence}-{index:04d}",
                    received_at=timestamp,
                    measured_at=timestamp,
                    payload_schema_version="synthetic-v2",
                    raw_payload={
                        "synthetic": True,
                        "demo_normalised_units": True,
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
