import pytest
from app.db.sync_catalog import sync_metric_catalog
from app.metric_catalog import METRICS, UNITS
from app.models.metric_definition import MetricDefinition
from app.models.unit_definition import UnitDefinition
from sqlalchemy import select
from sqlalchemy.orm import Session

pytestmark = pytest.mark.integration


def test_database_catalog_matches_canonical_code_catalog(db_session: Session) -> None:
    sync_metric_catalog(db_session)
    db_session.flush()

    rows = db_session.scalars(select(MetricDefinition).order_by(MetricDefinition.metric_code)).all()
    expected = sorted(METRICS, key=lambda metric: metric.metric_code)

    assert [row.metric_code for row in rows] == [metric.metric_code for metric in expected]
    assert [row.validity_basis for row in rows] == [metric.validity_basis for metric in expected]
    assert [row.metric_group for row in rows] == [metric.metric_group for metric in expected]
    units = db_session.scalars(select(UnitDefinition).order_by(UnitDefinition.unit_code)).all()
    expected_units = sorted(UNITS, key=lambda unit: unit.unit_code)
    assert [row.unit_code for row in units] == [unit.unit_code for unit in expected_units]
    assert [row.unit_symbol for row in units] == [unit.unit_symbol for unit in expected_units]
