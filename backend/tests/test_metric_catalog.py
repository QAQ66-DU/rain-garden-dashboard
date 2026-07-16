from os import environ
from pathlib import Path

import pytest
from app.metric_catalog import METRICS, get_metric, render_data_dictionary


def test_metric_codes_and_pairs_are_unique() -> None:
    codes = [metric.metric_code for metric in METRICS]
    pairs = [(metric.metric_code, metric.unit_code) for metric in METRICS]

    assert len(codes) == len(set(codes))
    assert len(pairs) == len(set(pairs))


def test_unknown_metric_is_rejected() -> None:
    with pytest.raises(ValueError, match="Unsupported metric"):
        get_metric("invented_metric")


def test_documented_dictionary_is_generated_from_catalog() -> None:
    default_path = Path(__file__).resolve().parents[2] / "docs" / "data-dictionary.md"
    dictionary = Path(environ.get("DATA_DICTIONARY_PATH", default_path))

    assert dictionary.read_text(encoding="utf-8") == render_data_dictionary()
