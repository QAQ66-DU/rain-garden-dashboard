from os import environ
from pathlib import Path

import pytest
from app.metric_catalog import METRICS, UNITS, get_metric, render_data_dictionary


def test_metric_codes_and_units_are_unique() -> None:
    codes = [metric.metric_code for metric in METRICS]
    units = [unit.unit_code for unit in UNITS]

    assert len(codes) == len(set(codes))
    assert len(units) == len(set(units))
    assert {metric.metric_group for metric in METRICS} == {
        "hydrology",
        "soil",
        "weather",
        "operational",
    }


def test_unknown_metric_is_rejected() -> None:
    with pytest.raises(ValueError, match="Unsupported metric"):
        get_metric("invented_metric")


def test_documented_dictionary_is_generated_from_catalog() -> None:
    default_path = Path(__file__).resolve().parents[2] / "docs" / "data-dictionary.md"
    dictionary = Path(environ.get("DATA_DICTIONARY_PATH", default_path))

    assert dictionary.read_text(encoding="utf-8") == render_data_dictionary()
