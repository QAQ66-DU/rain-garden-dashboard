import pytest
from app.db.sync_catalog import sync_metric_catalog
from app.metric_catalog import METRICS
from app.models.metric_definition import MetricDefinition
from sqlalchemy import select
from sqlalchemy.orm import Session

pytestmark = pytest.mark.integration


def test_database_catalog_matches_canonical_code_catalog(db_session: Session) -> None:
    sync_metric_catalog(db_session)
    db_session.flush()

    rows = db_session.scalars(
        select(MetricDefinition).order_by(MetricDefinition.metric_code, MetricDefinition.unit_code)
    ).all()
    expected = sorted(METRICS, key=lambda metric: (metric.metric_code, metric.unit_code))

    assert [(row.metric_code, row.unit_code) for row in rows] == [
        (metric.metric_code, metric.unit_code) for metric in expected
    ]
    assert [row.unit_symbol for row in rows] == [metric.unit_symbol for metric in expected]
    assert [row.validity_basis for row in rows] == [metric.validity_basis for metric in expected]
