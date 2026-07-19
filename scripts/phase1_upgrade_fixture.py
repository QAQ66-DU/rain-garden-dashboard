"""Prepare and verify a minimal populated Phase 1 schema during migration checks."""

from __future__ import annotations

import argparse
from os import environ

from sqlalchemy import create_engine, text

SITE_ID = "00000000-0000-0000-0000-000000000001"
DEVICE_ID = "00000000-0000-0000-0000-000000000002"
CHANNEL_ID = "00000000-0000-0000-0000-000000000003"


def prepare() -> None:
    engine = create_engine(environ["DATABASE_URL"])
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                INSERT INTO metric_definitions
                    (metric_code, unit_code, display_name, unit_symbol, meaning,
                     expected_type, validity_basis, source, scientifically_confirmed,
                     created_at, updated_at)
                VALUES
                    ('rainfall_mm', 'mm', 'Rainfall', 'mm', 'Legacy rainfall',
                     'number', 'Legacy vocabulary', 'Phase 1', false, now(), now())
                """
            )
        )
        connection.execute(
            text(
                """
                INSERT INTO sites
                    (id, name, public_location_label, location_disclosure,
                     display_timezone, active, created_at, updated_at)
                VALUES
                    (:site_id, 'Migration fixture', 'Withheld', 'private',
                     'Europe/London', true, now(), now())
                """
            ),
            {"site_id": SITE_ID},
        )
        connection.execute(
            text(
                """
                INSERT INTO devices
                    (id, site_id, external_device_id, display_name, device_type,
                     location_disclosure, created_at, updated_at)
                VALUES
                    (:device_id, :site_id, 'legacy-migration-fixture',
                     'Legacy migration fixture', 'weather_station', 'private', now(), now())
                """
            ),
            {"device_id": DEVICE_ID, "site_id": SITE_ID},
        )
        connection.execute(
            text(
                """
                INSERT INTO sensor_channels
                    (id, device_id, channel_code, display_name, metric_code, unit_code,
                     active, metadata, created_at, updated_at)
                VALUES
                    (:channel_id, :device_id, 'rainfall', 'Rainfall', 'rainfall_mm',
                     'mm', true, '{}', now(), now())
                """
            ),
            {"channel_id": CHANNEL_ID, "device_id": DEVICE_ID},
        )
    engine.dispose()


def verify() -> None:
    engine = create_engine(environ["DATABASE_URL"])
    with engine.connect() as connection:
        migrated = connection.execute(
            text(
                """
                SELECT sensor_channels.metric_code,
                       sensor_channels.unit_code,
                       sensor_channels.unit_confirmation_status,
                       sensor_channels.expected_reporting_interval_seconds,
                       sensor_channels.reporting_schedule_anchor_at,
                       unit_definitions.unit_symbol
                FROM sensor_channels
                JOIN unit_definitions
                  ON unit_definitions.unit_code = sensor_channels.unit_code
                WHERE sensor_channels.id = :channel_id
                """
            ),
            {"channel_id": CHANNEL_ID},
        ).one()
    engine.dispose()
    assert tuple(migrated) == ("rainfall_mm", "mm", "synthetic_demo_only", None, None, "mm")


def cleanup() -> None:
    engine = create_engine(environ["DATABASE_URL"])
    with engine.begin() as connection:
        connection.execute(
            text("DELETE FROM sensor_channels WHERE id = :identifier"),
            {"identifier": CHANNEL_ID},
        )
        connection.execute(
            text("DELETE FROM devices WHERE id = :identifier"),
            {"identifier": DEVICE_ID},
        )
        connection.execute(
            text("DELETE FROM sites WHERE id = :identifier"),
            {"identifier": SITE_ID},
        )
    engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("prepare", "verify", "cleanup"))
    args = parser.parse_args()
    {"prepare": prepare, "verify": verify, "cleanup": cleanup}[args.action]()


if __name__ == "__main__":
    main()
