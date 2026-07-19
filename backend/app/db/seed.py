from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.db.sync_catalog import sync_metric_catalog
from app.db.synthetic import (
    CONFIRMED_SYNTHETIC_EXTERNAL_IDS,
    LEGACY_SYNTHETIC_EXTERNAL_IDS,
    SYNTHETIC_CADENCE,
    SYNTHETIC_DAYS,
    SYNTHETIC_JITTER_TOLERANCE_SECONDS,
    SYNTHETIC_RANDOM_SEED,
    SYNTHETIC_REFERENCE_TIME,
    SYNTHETIC_SCHEDULE_ANCHOR,
    generate_synthetic_uplinks,
    stable_uuid,
)
from app.ingestion.contracts import CanonicalUplink
from app.ingestion.service import ingest_canonical_uplink
from app.models.device import Device
from app.models.enums import (
    DeviceType,
    LocationDisclosure,
    MonitoringFeatureType,
    SensorConfigurationStatus,
    UnitConfirmationStatus,
)
from app.models.monitoring_feature import MonitoringFeature
from app.models.sensor_channel import SensorChannel
from app.models.site import Site

SITE_ID = stable_uuid("site:orchard-park")
SWALE_FEATURE_ID = stable_uuid("feature:orchard-park:swale")
TREE_PIT_FEATURE_ID = stable_uuid("feature:orchard-park:tree-pit")


class LegacyDemoDataError(RuntimeError):
    """The Phase 1 demo must be reset explicitly before v2 can be seeded."""


@dataclass(frozen=True, slots=True)
class ChannelSpec:
    channel_code: str
    display_name: str
    metric_code: str
    unit_code: str
    position_label: str | None = None
    water_level_reference_or_datum: str | None = None


@dataclass(frozen=True, slots=True)
class DeviceSpec:
    external_device_id: str
    display_name: str
    device_type: DeviceType
    feature_id: UUID
    latitude: float
    longitude: float
    channels: tuple[ChannelSpec, ...]
    configuration_status: SensorConfigurationStatus = SensorConfigurationStatus.CONFIGURED


SOIL_CHANNELS = (
    ChannelSpec("soil_moisture", "Soil moisture", "soil_moisture", "vwc_pct"),
    ChannelSpec("soil_temperature", "Soil temperature", "soil_temperature", "deg_c"),
    ChannelSpec(
        "soil_electrical_conductivity",
        "Soil electrical conductivity",
        "soil_electrical_conductivity",
        "us_cm",
    ),
)
WATER_CHANNELS = (ChannelSpec("water_level", "Water level", "water_level", "mm"),)
WEATHER_CHANNELS = (
    ChannelSpec("air_temperature", "Air temperature", "air_temperature", "deg_c"),
    ChannelSpec("relative_humidity", "Relative humidity", "relative_humidity", "pct"),
    ChannelSpec("wind_speed", "Wind speed", "wind_speed", "m_s"),
    ChannelSpec("wind_direction", "Wind direction", "wind_direction", "degree"),
    ChannelSpec("rainfall_intensity", "Rainfall intensity", "rainfall_intensity", "mm_h"),
    ChannelSpec("light_intensity", "Light intensity", "light_intensity", "lux"),
    ChannelSpec("uv_index", "UV index", "uv_index", "uv_index"),
    ChannelSpec("barometric_pressure", "Barometric pressure", "barometric_pressure", "hpa"),
)

DEVICE_SPECS = (
    DeviceSpec(
        "synthetic-v2-swale-soil-001",
        "Swale soil sensor 1",
        DeviceType.SOIL_MOISTURE_SENSOR,
        SWALE_FEATURE_ID,
        55.955391,
        -3.238305,
        SOIL_CHANNELS,
    ),
    DeviceSpec(
        "synthetic-v2-swale-soil-002",
        "Swale soil sensor 2",
        DeviceType.SOIL_MOISTURE_SENSOR,
        SWALE_FEATURE_ID,
        55.955470,
        -3.237539,
        SOIL_CHANNELS,
    ),
    DeviceSpec(
        "synthetic-v2-swale-soil-003",
        "Swale soil sensor 3",
        DeviceType.SOIL_MOISTURE_SENSOR,
        SWALE_FEATURE_ID,
        55.955613,
        -3.236647,
        SOIL_CHANNELS,
    ),
    DeviceSpec(
        "synthetic-v2-swale-water-001",
        "Swale water-level sensor 1",
        DeviceType.WATER_LEVEL_SENSOR,
        SWALE_FEATURE_ID,
        55.955383,
        -3.238577,
        WATER_CHANNELS,
    ),
    DeviceSpec(
        "synthetic-v2-swale-water-002",
        "Swale water-level sensor 2",
        DeviceType.WATER_LEVEL_SENSOR,
        SWALE_FEATURE_ID,
        55.955405,
        -3.237983,
        WATER_CHANNELS,
    ),
    DeviceSpec(
        "synthetic-v2-swale-water-003",
        "Swale water-level sensor 3",
        DeviceType.WATER_LEVEL_SENSOR,
        SWALE_FEATURE_ID,
        55.955528,
        -3.237223,
        WATER_CHANNELS,
    ),
    DeviceSpec(
        "synthetic-v2-swale-weather-001",
        "Swale weather station",
        DeviceType.WEATHER_STATION,
        SWALE_FEATURE_ID,
        55.955312,
        -3.238602,
        WEATHER_CHANNELS,
    ),
    DeviceSpec(
        "synthetic-v2-tree-pit-probe-001",
        "Tree-pit multi-depth probe",
        DeviceType.MULTI_DEPTH_SOIL_PROBE,
        TREE_PIT_FEATURE_ID,
        55.955466,
        -3.239190,
        (),
        SensorConfigurationStatus.PENDING,
    ),
)


def _existing_inventory(session: Session) -> set[str]:
    return set(session.scalars(select(Device.external_device_id).where(Device.site_id == SITE_ID)))


def seed_session(session: Session) -> tuple[CanonicalUplink, ...] | None:
    with session.begin_nested():
        sync_metric_catalog(session)
        session.flush()
        site = session.get(Site, SITE_ID)
        if site is not None:
            inventory = _existing_inventory(session)
            if inventory & LEGACY_SYNTHETIC_EXTERNAL_IDS:
                raise LegacyDemoDataError(
                    "Legacy Phase 1 synthetic data is present. Run the explicit demo-only reset "
                    "command after reviewing its scope; the normal seed will not delete rows."
                )
            if inventory == CONFIRMED_SYNTHETIC_EXTERNAL_IDS:
                return None
            raise RuntimeError(
                "Orchard Park already contains an unrecognized inventory; no rows were changed."
            )

        site = Site(
            id=SITE_ID,
            name="Orchard Park monitoring site",
            description=(
                "Confirmed monitoring inventory with deterministic synthetic demonstration data."
            ),
            public_location_label="Orchard Park, Edinburgh; exact sensor locations withheld.",
            location_disclosure=LocationDisclosure.PRIVATE,
            private_latitude=None,
            private_longitude=None,
            display_timezone="Europe/London",
            active=True,
        )
        session.add(site)
        session.flush()

        features = (
            MonitoringFeature(
                id=SWALE_FEATURE_ID,
                site_id=site.id,
                public_slug="swale",
                display_name="Swale",
                feature_type=MonitoringFeatureType.SWALE,
                active=True,
            ),
            MonitoringFeature(
                id=TREE_PIT_FEATURE_ID,
                site_id=site.id,
                public_slug="tree-pit",
                display_name="Tree pit",
                feature_type=MonitoringFeatureType.TREE_PIT,
                active=True,
            ),
        )
        session.add_all(features)
        session.flush()

        for spec in DEVICE_SPECS:
            device = Device(
                id=stable_uuid(f"device:{spec.external_device_id}"),
                site_id=site.id,
                monitoring_feature_id=spec.feature_id,
                external_device_id=spec.external_device_id,
                display_name=spec.display_name,
                device_type=spec.device_type,
                sensor_configuration_status=spec.configuration_status,
                operational_override=None,
                last_seen_at=None,
                private_latitude=spec.latitude,
                private_longitude=spec.longitude,
                location_disclosure=LocationDisclosure.PRIVATE,
            )
            session.add(device)
            session.flush()
            for channel in spec.channels:
                session.add(
                    SensorChannel(
                        id=stable_uuid(f"channel:{spec.external_device_id}:{channel.channel_code}"),
                        device_id=device.id,
                        channel_code=channel.channel_code,
                        display_name=channel.display_name,
                        metric_code=channel.metric_code,
                        unit_code=channel.unit_code,
                        unit_confirmation_status=UnitConfirmationStatus.SYNTHETIC_DEMO_ONLY,
                        depth_cm=None,
                        position_label=channel.position_label,
                        expected_reporting_interval_seconds=int(SYNTHETIC_CADENCE.total_seconds()),
                        reporting_schedule_anchor_at=SYNTHETIC_SCHEDULE_ANCHOR,
                        reporting_jitter_tolerance_seconds=SYNTHETIC_JITTER_TOLERANCE_SECONDS,
                        water_level_reference_or_datum=channel.water_level_reference_or_datum,
                        active=True,
                        channel_metadata={
                            "synthetic": True,
                            "demo_normalised_unit": True,
                            "generator_cadence_minutes": int(
                                SYNTHETIC_CADENCE.total_seconds() / 60
                            ),
                        },
                    )
                )
        session.flush()

        uplinks = generate_synthetic_uplinks()
        for uplink in uplinks:
            ingest_canonical_uplink(session, uplink)
        duplicate_result = ingest_canonical_uplink(session, uplinks[-1])
        if duplicate_result.created:
            raise RuntimeError("Synthetic duplicate uplink was not idempotent")

    return uplinks


def seed() -> None:
    with SessionLocal.begin() as session:
        uplinks = seed_session(session)
    if uplinks is None:
        print("Confirmed synthetic dataset is already present; no rows were changed.")
        return
    print(
        "Seeded confirmed Orchard Park synthetic data: "
        f"8 end devices, {SYNTHETIC_DAYS} days, seed {SYNTHETIC_RANDOM_SEED}, "
        f"reference time {SYNTHETIC_REFERENCE_TIME.isoformat()}, "
        f"{len(uplinks)} unique uplinks, 1 duplicate attempt safely ignored."
    )


if __name__ == "__main__":
    seed()
