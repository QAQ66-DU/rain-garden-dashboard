"""Add monitoring features and explicit channel configuration metadata.

Revision ID: 0002
Revises: 0001
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "unit_definitions",
        sa.Column("unit_code", sa.String(50), primary_key=True),
        sa.Column("display_name", sa.String(100), nullable=False),
        sa.Column("unit_symbol", sa.String(50), nullable=False),
        sa.Column("meaning", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.execute(
        sa.text(
            """
            INSERT INTO unit_definitions
                (unit_code, display_name, unit_symbol, meaning, created_at, updated_at)
            SELECT unit_code, unit_code, MIN(unit_symbol),
                   'Physical unit migrated from the Phase 1 metric catalogue.',
                   MIN(created_at), MAX(updated_at)
            FROM metric_definitions
            GROUP BY unit_code
            """
        )
    )
    op.drop_constraint(
        "fk_sensor_channels_metric_definition", "sensor_channels", type_="foreignkey"
    )
    op.drop_constraint("pk_metric_definitions", "metric_definitions", type_="primary")
    op.create_primary_key("pk_metric_definitions", "metric_definitions", ["metric_code"])
    op.drop_column("metric_definitions", "unit_symbol")
    op.drop_column("metric_definitions", "unit_code")
    op.alter_column("sensor_channels", "unit_code", existing_type=sa.String(50), nullable=True)
    op.create_foreign_key(
        "fk_sensor_channels_metric_code_metric_definitions",
        "sensor_channels",
        "metric_definitions",
        ["metric_code"],
        ["metric_code"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_sensor_channels_unit_code_unit_definitions",
        "sensor_channels",
        "unit_definitions",
        ["unit_code"],
        ["unit_code"],
        ondelete="RESTRICT",
    )

    op.create_table(
        "monitoring_features",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("site_id", sa.Uuid(), nullable=False),
        sa.Column("public_slug", sa.String(100), nullable=False),
        sa.Column("display_name", sa.String(200), nullable=False),
        sa.Column("feature_type", sa.String(30), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "feature_type IN ('swale', 'tree_pit')",
            name="feature_type",
        ),
        sa.ForeignKeyConstraint(["site_id"], ["sites.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("site_id", "public_slug", name="uq_monitoring_features_site_slug"),
        sa.UniqueConstraint("id", "site_id", name="uq_monitoring_features_id_site_id"),
    )
    op.create_index("ix_monitoring_features_site_id", "monitoring_features", ["site_id"])

    op.add_column("devices", sa.Column("monitoring_feature_id", sa.Uuid(), nullable=True))
    op.add_column(
        "devices",
        sa.Column(
            "sensor_configuration_status",
            sa.String(20),
            nullable=False,
            server_default="configured",
        ),
    )
    op.create_index("ix_devices_monitoring_feature_id", "devices", ["monitoring_feature_id"])
    op.create_foreign_key(
        "fk_devices_monitoring_feature_site",
        "devices",
        "monitoring_features",
        ["monitoring_feature_id", "site_id"],
        ["id", "site_id"],
        ondelete="RESTRICT",
    )
    op.drop_constraint(op.f("ck_devices_device_type"), "devices", type_="check")
    op.create_check_constraint(
        "device_type",
        "devices",
        "device_type IN ('weather_station', 'soil_moisture_sensor', "
        "'water_level_sensor', 'multi_depth_soil_probe')",
    )
    op.create_check_constraint(
        "sensor_configuration_status",
        "devices",
        "sensor_configuration_status IN ('configured', 'pending')",
    )

    op.add_column(
        "sensor_channels",
        sa.Column(
            "unit_confirmation_status",
            sa.String(30),
            nullable=False,
            server_default="synthetic_demo_only",
        ),
    )
    op.add_column(
        "sensor_channels",
        sa.Column("expected_reporting_interval_seconds", sa.Integer(), nullable=True),
    )
    op.add_column(
        "sensor_channels",
        sa.Column("reporting_schedule_anchor_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "sensor_channels",
        sa.Column("reporting_jitter_tolerance_seconds", sa.Integer(), nullable=True),
    )
    op.add_column(
        "sensor_channels",
        sa.Column("water_level_reference_or_datum", sa.String(200), nullable=True),
    )
    op.create_check_constraint(
        "positive_reporting_interval",
        "sensor_channels",
        "expected_reporting_interval_seconds IS NULL OR expected_reporting_interval_seconds > 0",
    )
    op.create_check_constraint(
        "nonnegative_reporting_jitter",
        "sensor_channels",
        "reporting_jitter_tolerance_seconds IS NULL OR reporting_jitter_tolerance_seconds >= 0",
    )
    op.create_check_constraint(
        "unit_confirmation_status",
        "sensor_channels",
        "unit_confirmation_status IN ('pending', 'confirmed', 'synthetic_demo_only')",
    )
    op.create_check_constraint(
        "confirmed_unit_requires_code",
        "sensor_channels",
        "unit_confirmation_status = 'pending' OR unit_code IS NOT NULL",
    )
    op.alter_column(
        "sensor_channels",
        "unit_confirmation_status",
        server_default="pending",
    )


def downgrade() -> None:
    op.drop_constraint(
        op.f("ck_sensor_channels_confirmed_unit_requires_code"),
        "sensor_channels",
        type_="check",
    )
    op.drop_constraint(
        op.f("ck_sensor_channels_unit_confirmation_status"),
        "sensor_channels",
        type_="check",
    )
    op.drop_constraint(
        op.f("ck_sensor_channels_nonnegative_reporting_jitter"),
        "sensor_channels",
        type_="check",
    )
    op.drop_constraint(
        op.f("ck_sensor_channels_positive_reporting_interval"),
        "sensor_channels",
        type_="check",
    )
    op.drop_column("sensor_channels", "water_level_reference_or_datum")
    op.drop_column("sensor_channels", "reporting_jitter_tolerance_seconds")
    op.drop_column("sensor_channels", "reporting_schedule_anchor_at")
    op.drop_column("sensor_channels", "expected_reporting_interval_seconds")
    op.drop_column("sensor_channels", "unit_confirmation_status")

    op.drop_constraint(op.f("ck_devices_sensor_configuration_status"), "devices", type_="check")
    op.drop_constraint(op.f("ck_devices_device_type"), "devices", type_="check")
    op.create_check_constraint(
        "device_type",
        "devices",
        "device_type IN ('weather_station', 'soil_moisture_sensor', 'water_level_sensor')",
    )
    op.drop_constraint("fk_devices_monitoring_feature_site", "devices", type_="foreignkey")
    op.drop_index("ix_devices_monitoring_feature_id", table_name="devices")
    op.drop_column("devices", "sensor_configuration_status")
    op.drop_column("devices", "monitoring_feature_id")
    op.drop_table("monitoring_features")

    op.drop_constraint(
        "fk_sensor_channels_unit_code_unit_definitions", "sensor_channels", type_="foreignkey"
    )
    op.drop_constraint(
        "fk_sensor_channels_metric_code_metric_definitions",
        "sensor_channels",
        type_="foreignkey",
    )
    op.add_column("metric_definitions", sa.Column("unit_code", sa.String(50), nullable=True))
    op.add_column("metric_definitions", sa.Column("unit_symbol", sa.String(50), nullable=True))
    op.execute(
        sa.text(
            """
            UPDATE metric_definitions AS metric
            SET unit_code = source.unit_code,
                unit_symbol = unit_definitions.unit_symbol
            FROM (
                SELECT metric_code, MIN(unit_code) AS unit_code
                FROM sensor_channels
                WHERE unit_code IS NOT NULL
                GROUP BY metric_code
            ) AS source
            JOIN unit_definitions ON unit_definitions.unit_code = source.unit_code
            WHERE metric.metric_code = source.metric_code
            """
        )
    )
    op.drop_constraint("pk_metric_definitions", "metric_definitions", type_="primary")
    op.create_primary_key(
        "pk_metric_definitions", "metric_definitions", ["metric_code", "unit_code"]
    )
    op.alter_column("metric_definitions", "unit_code", nullable=False)
    op.alter_column("metric_definitions", "unit_symbol", nullable=False)
    op.alter_column("sensor_channels", "unit_code", nullable=False)
    op.create_foreign_key(
        "fk_sensor_channels_metric_definition",
        "sensor_channels",
        "metric_definitions",
        ["metric_code", "unit_code"],
        ["metric_code", "unit_code"],
        ondelete="RESTRICT",
    )
    op.drop_table("unit_definitions")
