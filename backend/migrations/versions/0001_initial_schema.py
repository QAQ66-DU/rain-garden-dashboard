"""Create the Phase 0 sensor monitoring schema.

Revision ID: 0001
Revises: None
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "metric_definitions",
        sa.Column("metric_code", sa.String(100), primary_key=True),
        sa.Column("unit_code", sa.String(50), primary_key=True),
        sa.Column("display_name", sa.String(200), nullable=False),
        sa.Column("unit_symbol", sa.String(50), nullable=False),
        sa.Column("meaning", sa.Text(), nullable=False),
        sa.Column("expected_type", sa.String(50), nullable=False),
        sa.Column("valid_min", sa.Float(), nullable=True),
        sa.Column("valid_max", sa.Float(), nullable=True),
        sa.Column("validity_basis", sa.Text(), nullable=False),
        sa.Column("source", sa.String(200), nullable=False),
        sa.Column("scientifically_confirmed", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("metric_code", "unit_code", name="pk_metric_definitions"),
    )
    op.create_table(
        "sites",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("public_location_label", sa.String(300), nullable=False),
        sa.Column("location_disclosure", sa.String(20), nullable=False),
        sa.Column("private_latitude", sa.Float(), nullable=True),
        sa.Column("private_longitude", sa.Float(), nullable=True),
        sa.Column("display_timezone", sa.String(100), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "private_latitude IS NULL OR private_latitude BETWEEN -90 AND 90",
            name="private_latitude_range",
        ),
        sa.CheckConstraint(
            "private_longitude IS NULL OR private_longitude BETWEEN -180 AND 180",
            name="private_longitude_range",
        ),
        sa.CheckConstraint(
            "location_disclosure IN ('withheld', 'approximate', 'private')",
            name="location_disclosure",
        ),
        sa.UniqueConstraint("name", name="uq_sites_name"),
    )
    op.create_table(
        "devices",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("site_id", sa.Uuid(), nullable=False),
        sa.Column("external_device_id", sa.String(200), nullable=False),
        sa.Column("display_name", sa.String(200), nullable=False),
        sa.Column("device_type", sa.String(40), nullable=False),
        sa.Column("operational_override", sa.String(20), nullable=True),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("private_latitude", sa.Float(), nullable=True),
        sa.Column("private_longitude", sa.Float(), nullable=True),
        sa.Column("location_disclosure", sa.String(20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "device_type IN ('weather_station', 'soil_moisture_sensor', 'water_level_sensor')",
            name="device_type",
        ),
        sa.CheckConstraint(
            "operational_override IS NULL OR operational_override IN ('maintenance', 'disabled')",
            name="operational_override",
        ),
        sa.CheckConstraint(
            "location_disclosure IN ('withheld', 'approximate', 'private')",
            name="location_disclosure",
        ),
        sa.CheckConstraint(
            "private_latitude IS NULL OR private_latitude BETWEEN -90 AND 90",
            name="private_latitude_range",
        ),
        sa.CheckConstraint(
            "private_longitude IS NULL OR private_longitude BETWEEN -180 AND 180",
            name="private_longitude_range",
        ),
        sa.ForeignKeyConstraint(["site_id"], ["sites.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("external_device_id", name="uq_devices_external_device_id"),
        sa.UniqueConstraint("id", "site_id", name="uq_devices_id_site_id"),
    )
    op.create_index("ix_devices_site_id", "devices", ["site_id"])
    op.create_table(
        "sensor_channels",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("device_id", sa.Uuid(), nullable=False),
        sa.Column("channel_code", sa.String(100), nullable=False),
        sa.Column("display_name", sa.String(200), nullable=False),
        sa.Column("metric_code", sa.String(100), nullable=False),
        sa.Column("unit_code", sa.String(50), nullable=False),
        sa.Column("depth_cm", sa.Float(), nullable=True),
        sa.Column("position_label", sa.String(200), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("depth_cm IS NULL OR depth_cm >= 0", name="nonnegative_depth"),
        sa.ForeignKeyConstraint(["device_id"], ["devices.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["metric_code", "unit_code"],
            ["metric_definitions.metric_code", "metric_definitions.unit_code"],
            name="fk_sensor_channels_metric_definition",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint("device_id", "channel_code", name="uq_sensor_channels_device_code"),
        sa.UniqueConstraint("id", "device_id", name="uq_sensor_channels_id_device_id"),
    )
    op.create_index("ix_sensor_channels_device_id", "sensor_channels", ["device_id"])
    op.create_table(
        "uplink_events",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("device_id", sa.Uuid(), nullable=False),
        sa.Column("source", sa.String(50), nullable=False),
        sa.Column("idempotency_key", sa.String(300), nullable=False),
        sa.Column("external_event_identifier", sa.String(300), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("measured_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("frame_counter", sa.Integer(), nullable=True),
        sa.Column("raw_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("payload_schema_version", sa.String(100), nullable=True),
        sa.Column("ingestion_status", sa.String(20), nullable=False),
        sa.Column("ingestion_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "frame_counter IS NULL OR frame_counter >= 0",
            name="frame_counter_nonnegative",
        ),
        sa.CheckConstraint(
            "ingestion_status IN ('accepted', 'rejected')",
            name="ingestion_status",
        ),
        sa.ForeignKeyConstraint(["device_id"], ["devices.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("source", "idempotency_key", name="uq_uplink_events_source_key"),
        sa.UniqueConstraint("id", "device_id", name="uq_uplink_events_id_device_id"),
    )
    op.create_index(
        "ix_uplink_events_device_received",
        "uplink_events",
        ["device_id", "received_at", "id"],
    )
    op.create_table(
        "measurements",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("uplink_event_id", sa.Uuid(), nullable=False),
        sa.Column("device_id", sa.Uuid(), nullable=False),
        sa.Column("sensor_channel_id", sa.Uuid(), nullable=False),
        sa.Column("numeric_value", sa.Numeric(18, 6), nullable=False),
        sa.Column("measured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("quality_flag", sa.String(20), nullable=False),
        sa.Column("quality_notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "quality_flag IN ('valid', 'out_of_range', 'suspect')",
            name="quality_flag",
        ),
        sa.ForeignKeyConstraint(["device_id"], ["devices.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["sensor_channel_id", "device_id"],
            ["sensor_channels.id", "sensor_channels.device_id"],
            name="fk_measurements_channel_device",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["uplink_event_id", "device_id"],
            ["uplink_events.id", "uplink_events.device_id"],
            name="fk_measurements_uplink_device",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "uplink_event_id",
            "sensor_channel_id",
            "measured_at",
            name="uq_measurements_event_channel_time",
        ),
    )
    op.create_index(
        "ix_measurements_channel_time_id",
        "measurements",
        ["sensor_channel_id", "measured_at", "id"],
    )
    op.create_index(
        "ix_measurements_device_time_id",
        "measurements",
        ["device_id", "measured_at", "id"],
    )


def downgrade() -> None:
    op.drop_table("measurements")
    op.drop_table("uplink_events")
    op.drop_table("sensor_channels")
    op.drop_table("devices")
    op.drop_table("sites")
    op.drop_table("metric_definitions")
