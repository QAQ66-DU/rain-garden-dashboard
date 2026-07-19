from decimal import Decimal

from app.analytics.quality import assess_measurement
from app.models.enums import QualityFlag


def test_zero_rainfall_is_a_real_valid_value() -> None:
    assessment = assess_measurement("rainfall_intensity", Decimal("0"))

    assert assessment.flag is QualityFlag.VALID
    assert assessment.notes is None


def test_relative_humidity_above_definition_bound_is_flagged() -> None:
    assessment = assess_measurement("relative_humidity", Decimal("112"))

    assert assessment.flag is QualityFlag.OUT_OF_RANGE
    assert assessment.notes == "Above definition-level maximum of 100."


def test_unconfirmed_water_level_range_is_not_invented() -> None:
    assessment = assess_measurement("water_level", Decimal("-5"))

    assert assessment.flag is QualityFlag.VALID
