from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.metric_catalog import METRICS, UNITS
from app.models.metric_definition import MetricDefinition
from app.models.unit_definition import UnitDefinition


def sync_metric_catalog(session: Session) -> None:
    expected_codes = {metric.metric_code for metric in METRICS}
    actual = {row.metric_code: row for row in session.scalars(select(MetricDefinition))}
    unexpected = set(actual) - expected_codes
    if unexpected:
        raise RuntimeError("Database metric catalog contains entries absent from the code catalog")

    for metric in METRICS:
        metric_row = actual.get(metric.metric_code)
        if metric_row is None:
            metric_row = MetricDefinition(metric_code=metric.metric_code)
            session.add(metric_row)
        metric_row.display_name = metric.display_name
        metric_row.metric_group = metric.metric_group
        metric_row.meaning = metric.meaning
        metric_row.expected_type = metric.expected_type
        metric_row.valid_min = metric.valid_min
        metric_row.valid_max = metric.valid_max
        metric_row.validity_basis = metric.validity_basis
        metric_row.source = metric.source
        metric_row.scientifically_confirmed = metric.scientifically_confirmed

    expected_units = {unit.unit_code for unit in UNITS}
    actual_units = {row.unit_code: row for row in session.scalars(select(UnitDefinition))}
    unexpected_units = set(actual_units) - expected_units
    if unexpected_units:
        raise RuntimeError("Database unit catalog contains entries absent from the code catalog")
    for unit in UNITS:
        unit_row = actual_units.get(unit.unit_code)
        if unit_row is None:
            unit_row = UnitDefinition(unit_code=unit.unit_code)
            session.add(unit_row)
        unit_row.display_name = unit.display_name
        unit_row.unit_symbol = unit.unit_symbol
        unit_row.meaning = unit.meaning

    # Existing channels may reference newly added catalogue rows immediately after this returns.
    session.flush()


def main() -> None:
    with SessionLocal.begin() as session:
        sync_metric_catalog(session)
    print(f"Synchronized {len(METRICS)} metrics and {len(UNITS)} physical units.")


if __name__ == "__main__":
    main()
