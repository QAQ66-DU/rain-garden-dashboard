"""Separate TTN measurement quality from pending scientific metadata.

Revision ID: 0005
Revises: 0004
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            UPDATE measurements AS measurement
            SET quality_flag = 'valid',
                quality_notes = NULL
            FROM uplink_events AS uplink
            WHERE measurement.uplink_event_id = uplink.id
              AND measurement.quality_flag = 'suspect'
              AND uplink.ingestion_status = 'accepted'
              AND (
                (
                  uplink.source = 'ttn_mqtt'
                  AND measurement.quality_notes IN (
                    'Live TTN MQTT decoder output; physical interpretation and unit are unverified. Timestamp basis is TTN received_at.',
                    'Live TTN MQTT proxy decoder output; physical units remain unverified. The sensor is not deployed at Orchard Park. Timestamp basis is TTN received_at.'
                  )
                )
                OR
                (
                  uplink.source = 'ttn_offline_replay'
                  AND measurement.quality_notes = 'Offline replay decoder output; physical interpretation and unit are unverified. Timestamp basis is TTN received_at.'
                )
              )
            """
        )
    )


def downgrade() -> None:
    # This scientific data correction is intentionally one-way. Reverting application code must
    # not relabel successfully decoded observations as suspect or affect newer valid TTN records.
    pass
