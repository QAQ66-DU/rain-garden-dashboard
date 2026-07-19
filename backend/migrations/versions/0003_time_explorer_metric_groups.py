"""Add controlled metric groups for Time Explorer.

Revision ID: 0003
Revises: 0002
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "metric_definitions",
        sa.Column(
            "metric_group",
            sa.String(30),
            nullable=False,
            server_default="operational",
        ),
    )
    op.execute(
        sa.text(
            """
            UPDATE metric_definitions
            SET metric_group = CASE
                WHEN metric_code IN (
                    'water_level', 'rainfall_intensity', 'water_level_mm', 'rainfall_mm'
                ) THEN 'hydrology'
                WHEN metric_code IN (
                    'soil_moisture', 'soil_temperature', 'soil_electrical_conductivity',
                    'soil_moisture_vwc_pct'
                ) THEN 'soil'
                WHEN metric_code IN (
                    'air_temperature', 'relative_humidity', 'wind_speed', 'wind_direction',
                    'light_intensity', 'uv_index', 'barometric_pressure',
                    'air_temperature_c', 'relative_humidity_pct'
                ) THEN 'weather'
                ELSE 'operational'
            END
            """
        )
    )
    op.create_check_constraint(
        "metric_group",
        "metric_definitions",
        "metric_group IN ('hydrology', 'soil', 'weather', 'operational')",
    )


def downgrade() -> None:
    op.drop_constraint(
        op.f("ck_metric_definitions_metric_group"),
        "metric_definitions",
        type_="check",
    )
    op.drop_column("metric_definitions", "metric_group")
