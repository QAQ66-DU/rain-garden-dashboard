from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.db.sync_catalog import sync_metric_catalog
from app.db.synthetic import (
    SYNTHETIC_CADENCE,
    SYNTHETIC_DAYS,
    SYNTHETIC_RANDOM_SEED,
    SYNTHETIC_REFERENCE_TIME,
    generate_synthetic_uplinks,
    stable_uuid,
)
from app.ingestion.contracts import CanonicalUplink
from app.ingestion.service import ingest_canonical_uplink
from app.models.device import Device
from app.models.enums import DeviceType, LocationDisclosure
from app.models.sensor_channel import SensorChannel
from app.models.site import Site

SITE_ID = stable_uuid("site:orchard-park")


def seed_session(session: Session) -> tuple[CanonicalUplink, ...] | None:
    with session.begin_nested():
        sync_metric_catalog(session)
        session.flush()
        if session.scalar(select(Site).where(Site.id == SITE_ID)) is not None:
            return None

        site = Site(
            id=SITE_ID,
            name="Orchard Park demonstration site",
            description=(
                "Deterministic synthetic site for dashboard testing and research workflow design."
            ),
            public_location_label="Synthetic demonstration site; exact location not supplied.",
            location_disclosure=LocationDisclosure.WITHHELD,
            private_latitude=None,
            private_longitude=None,
            display_timezone="Europe/London",
            active=True,
        )
        session.add(site)
        session.flush()

        device_specs = (
            (
                "synthetic-weather-001",
                "Orchard weather station",
                DeviceType.WEATHER_STATION,
                (
                    ("rainfall", "Rainfall gauge", "rainfall_mm", "mm", None, "Open exposure"),
                    (
                        "air_temperature",
                        "Air temperature",
                        "air_temperature_c",
                        "deg_c",
                        None,
                        "Weather station",
                    ),
                    (
                        "relative_humidity",
                        "Relative humidity",
                        "relative_humidity_pct",
                        "pct",
                        None,
                        "Weather station",
                    ),
                    ("battery", "Battery voltage", "battery_voltage_v", "v", None, None),
                    ("rssi", "Network RSSI", "rssi_dbm", "dbm", None, None),
                    ("snr", "Network SNR", "snr_db", "db", None, None),
                ),
            ),
            (
                "synthetic-soil-001",
                "Orchard soil profile sensor",
                DeviceType.SOIL_MOISTURE_SENSOR,
                (
                    (
                        "soil_10cm",
                        "Soil moisture at 10 cm",
                        "soil_moisture_vwc_pct",
                        "vwc_pct",
                        10.0,
                        "Bed A",
                    ),
                    (
                        "soil_30cm",
                        "Soil moisture at 30 cm",
                        "soil_moisture_vwc_pct",
                        "vwc_pct",
                        30.0,
                        "Bed A",
                    ),
                    ("battery", "Battery voltage", "battery_voltage_v", "v", None, None),
                    ("rssi", "Network RSSI", "rssi_dbm", "dbm", None, None),
                    ("snr", "Network SNR", "snr_db", "db", None, None),
                ),
            ),
            (
                "synthetic-water-001",
                "Orchard water-level sensor",
                DeviceType.WATER_LEVEL_SENSOR,
                (
                    (
                        "water_level",
                        "Water level",
                        "water_level_mm",
                        "mm",
                        None,
                        "Synthetic outlet position",
                    ),
                    ("battery", "Battery voltage", "battery_voltage_v", "v", None, None),
                    ("rssi", "Network RSSI", "rssi_dbm", "dbm", None, None),
                    ("snr", "Network SNR", "snr_db", "db", None, None),
                ),
            ),
        )

        for external_id, display_name, device_type, channel_specs in device_specs:
            device = Device(
                id=stable_uuid(f"device:{external_id}"),
                site_id=site.id,
                external_device_id=external_id,
                display_name=display_name,
                device_type=device_type,
                operational_override=None,
                last_seen_at=None,
                private_latitude=None,
                private_longitude=None,
                location_disclosure=LocationDisclosure.WITHHELD,
            )
            session.add(device)
            session.flush()
            for channel_code, name, metric_code, unit_code, depth_cm, position in channel_specs:
                session.add(
                    SensorChannel(
                        id=stable_uuid(f"channel:{external_id}:{channel_code}"),
                        device_id=device.id,
                        channel_code=channel_code,
                        display_name=name,
                        metric_code=metric_code,
                        unit_code=unit_code,
                        depth_cm=depth_cm,
                        position_label=position,
                        active=True,
                        channel_metadata={
                            "synthetic": True,
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
        print("Synthetic dataset is already present; no rows were changed.")
        return
    print(
        "Seeded deterministic synthetic data: "
        f"{SYNTHETIC_DAYS} days, seed {SYNTHETIC_RANDOM_SEED}, "
        f"reference time {SYNTHETIC_REFERENCE_TIME.isoformat()}, "
        f"{len(uplinks)} unique uplinks, 1 duplicate attempt safely ignored."
    )


if __name__ == "__main__":
    seed()
