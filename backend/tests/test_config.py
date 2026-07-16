import pytest
from app.core.config import Settings
from pydantic import ValidationError


def test_default_phase_one_limits_are_bounded() -> None:
    settings = Settings(database_url="postgresql+psycopg://example:example@db/example")

    assert settings.default_measurement_range_days == 7
    assert settings.max_measurement_range_days == 31
    assert settings.max_measurement_result_rows == 5_000
    assert settings.webhook_body_limit_bytes == 262_144


def test_enabled_webhook_requires_a_substantial_secret() -> None:
    with pytest.raises(ValidationError, match="secret of at least 16 characters"):
        Settings(
            database_url="postgresql+psycopg://example:example@db/example",
            ttn_webhook_enabled=True,
            ttn_webhook_secret="short",
        )


def test_offline_threshold_must_follow_stale_threshold() -> None:
    with pytest.raises(ValidationError, match="offline threshold"):
        Settings(
            database_url="postgresql+psycopg://example:example@db/example",
            device_stale_after_minutes=180,
            device_offline_after_minutes=90,
        )
