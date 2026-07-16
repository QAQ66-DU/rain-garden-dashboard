from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.metric_catalog import METRICS
from app.models.metric_definition import MetricDefinition


def sync_metric_catalog(session: Session) -> None:
    expected_keys = {(metric.metric_code, metric.unit_code) for metric in METRICS}
    actual = {
        (row.metric_code, row.unit_code): row for row in session.scalars(select(MetricDefinition))
    }
    unexpected = set(actual) - expected_keys
    if unexpected:
        raise RuntimeError("Database metric catalog contains entries absent from the code catalog")

    for metric in METRICS:
        key = (metric.metric_code, metric.unit_code)
        row = actual.get(key)
        if row is None:
            row = MetricDefinition(metric_code=metric.metric_code, unit_code=metric.unit_code)
            session.add(row)
        row.display_name = metric.display_name
        row.unit_symbol = metric.unit_symbol
        row.meaning = metric.meaning
        row.expected_type = metric.expected_type
        row.valid_min = metric.valid_min
        row.valid_max = metric.valid_max
        row.validity_basis = metric.validity_basis
        row.source = metric.source
        row.scientifically_confirmed = metric.scientifically_confirmed


def main() -> None:
    with SessionLocal.begin() as session:
        sync_metric_catalog(session)
    print(f"Synchronized {len(METRICS)} controlled metric definitions.")


if __name__ == "__main__":
    main()
