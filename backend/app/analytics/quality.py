from dataclasses import dataclass
from decimal import Decimal

from app.metric_catalog import get_metric
from app.models.enums import QualityFlag


@dataclass(frozen=True, slots=True)
class QualityAssessment:
    flag: QualityFlag
    notes: str | None


def assess_measurement(metric_code: str, value: Decimal) -> QualityAssessment:
    metric = get_metric(metric_code)
    if not value.is_finite():
        return QualityAssessment(QualityFlag.OUT_OF_RANGE, "Value must be finite.")

    if metric.valid_min is not None and value < Decimal(str(metric.valid_min)):
        return QualityAssessment(
            QualityFlag.OUT_OF_RANGE,
            f"Below definition-level minimum of {metric.valid_min:g} {metric.unit_symbol}.",
        )
    if metric.valid_max is not None and value > Decimal(str(metric.valid_max)):
        return QualityAssessment(
            QualityFlag.OUT_OF_RANGE,
            f"Above definition-level maximum of {metric.valid_max:g} {metric.unit_symbol}.",
        )
    return QualityAssessment(QualityFlag.VALID, None)
