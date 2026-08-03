"""Add isolated offline TTN replay metadata and private quarantine storage.

Revision ID: 0004
Revises: 0003
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint(
        op.f("ck_monitoring_features_feature_type"), "monitoring_features", type_="check"
    )
    op.create_check_constraint(
        "feature_type",
        "monitoring_features",
        "feature_type IN ('swale', 'tree_pit', 'testbed')",
    )
    op.drop_constraint(op.f("ck_devices_device_type"), "devices", type_="check")
    op.create_check_constraint(
        "device_type",
        "devices",
        "device_type IN ('weather_station', 'soil_moisture_sensor', "
        "'water_level_sensor', 'multi_depth_soil_probe', 'test_telemetry_device')",
    )

    op.add_column("devices", sa.Column("environment", sa.String(30), nullable=True))
    op.add_column("devices", sa.Column("source_system", sa.String(30), nullable=True))
    op.add_column("devices", sa.Column("ingestion_mode", sa.String(30), nullable=True))
    op.add_column("devices", sa.Column("provenance", sa.String(50), nullable=True))
    op.add_column(
        "devices",
        sa.Column("is_test_device", sa.Boolean(), nullable=False, server_default=sa.false()),
    )

    op.add_column("sensor_channels", sa.Column("scientific_meaning", sa.Text(), nullable=True))
    op.add_column(
        "sensor_channels",
        sa.Column(
            "verification_status",
            sa.String(20),
            nullable=False,
            server_default="catalogued",
        ),
    )
    op.add_column("sensor_channels", sa.Column("timestamp_basis", sa.String(50), nullable=True))
    op.create_check_constraint(
        "verification_status",
        "sensor_channels",
        "verification_status IN ('catalogued', 'unverified')",
    )

    op.add_column("uplink_events", sa.Column("ingestion_mode", sa.String(30), nullable=True))
    op.add_column("uplink_events", sa.Column("provenance", sa.String(50), nullable=True))

    op.create_table(
        "device_telemetry",
        sa.Column("device_id", sa.Uuid(), primary_key=True),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("battery_percent", sa.Numeric(8, 3), nullable=True),
        sa.Column("firmware_version", sa.String(100), nullable=True),
        sa.Column("hardware_version", sa.String(100), nullable=True),
        sa.Column("measurement_interval_value", sa.Numeric(18, 6), nullable=True),
        sa.Column("measurement_interval_unit", sa.String(30), nullable=True),
        sa.Column("threshold_measurement_interval_value", sa.Numeric(18, 6), nullable=True),
        sa.Column("latest_rssi_dbm", sa.Numeric(10, 3), nullable=True),
        sa.Column("latest_snr_db", sa.Numeric(10, 3), nullable=True),
        sa.Column("gateway_alias", sa.String(100), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "battery_percent IS NULL OR battery_percent BETWEEN 0 AND 100",
            name="battery_percent_range",
        ),
        sa.ForeignKeyConstraint(["device_id"], ["devices.id"], ondelete="CASCADE"),
    )

    op.create_table(
        "ttn_replay_quarantine",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("source", sa.String(50), nullable=False),
        sa.Column("idempotency_key", sa.String(64), nullable=False),
        sa.Column("event_name", sa.String(100), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failure_code", sa.String(100), nullable=False),
        sa.Column("parser_version", sa.String(100), nullable=False),
        sa.Column("failure_detail", sa.Text(), nullable=True),
        sa.Column("raw_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("source", "idempotency_key", name="uq_ttn_quarantine_source_key"),
    )


def downgrade() -> None:
    op.drop_table("ttn_replay_quarantine")
    op.drop_table("device_telemetry")
    op.drop_column("uplink_events", "provenance")
    op.drop_column("uplink_events", "ingestion_mode")
    op.drop_constraint(
        op.f("ck_sensor_channels_verification_status"),
        "sensor_channels",
        type_="check",
    )
    op.drop_column("sensor_channels", "timestamp_basis")
    op.drop_column("sensor_channels", "verification_status")
    op.drop_column("sensor_channels", "scientific_meaning")

    op.execute(
        sa.text(
            """
            DELETE FROM measurements
            WHERE device_id IN (SELECT id FROM devices WHERE is_test_device = true);
            DELETE FROM uplink_events
            WHERE device_id IN (SELECT id FROM devices WHERE is_test_device = true);
            DELETE FROM sensor_channels
            WHERE device_id IN (SELECT id FROM devices WHERE is_test_device = true);
            DELETE FROM devices WHERE is_test_device = true;
            DELETE FROM monitoring_features WHERE feature_type = 'testbed';
            DELETE FROM sites WHERE name = 'TTN Testbed';
            """
        )
    )
    op.drop_column("devices", "is_test_device")
    op.drop_column("devices", "provenance")
    op.drop_column("devices", "ingestion_mode")
    op.drop_column("devices", "source_system")
    op.drop_column("devices", "environment")

    op.drop_constraint(op.f("ck_devices_device_type"), "devices", type_="check")
    op.create_check_constraint(
        "device_type",
        "devices",
        "device_type IN ('weather_station', 'soil_moisture_sensor', "
        "'water_level_sensor', 'multi_depth_soil_probe')",
    )
    op.drop_constraint(
        op.f("ck_monitoring_features_feature_type"), "monitoring_features", type_="check"
    )
    op.create_check_constraint(
        "feature_type",
        "monitoring_features",
        "feature_type IN ('swale', 'tree_pit')",
    )
