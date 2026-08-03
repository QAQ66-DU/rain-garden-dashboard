import pytest
from app.core.config import Settings
from app.ingestion.ttn_mqtt import MQTTConfigurationError, require_mqtt_api_key
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


def test_non_secret_mqtt_configuration_loads_without_an_api_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TTN_MQTT_HOST", "mqtt.example.invalid")
    monkeypatch.setenv("TTN_MQTT_PORT", "8883")
    monkeypatch.setenv("TTN_MQTT_USERNAME", "test-application@example")
    monkeypatch.setenv("TTN_MQTT_TOPIC", "v3/rain-garden@ttn/devices/outflow-a/up")

    settings = Settings(database_url="postgresql+psycopg://example:example@db/example")

    assert settings.ttn_mqtt_host == "mqtt.example.invalid"
    assert settings.ttn_mqtt_port == 8883
    assert settings.ttn_mqtt_username == "test-application@example"
    assert settings.ttn_mqtt_topic == "v3/rain-garden@ttn/devices/outflow-a/up"
    assert settings.ttn_mqtt_api_key is None


def test_mqtt_worker_requires_the_api_key_only_at_worker_startup() -> None:
    settings = Settings(database_url="postgresql+psycopg://example:example@db/example")

    with pytest.raises(MQTTConfigurationError, match="TTN_MQTT_API_KEY is required"):
        require_mqtt_api_key(settings)
