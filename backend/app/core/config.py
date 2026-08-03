from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_env: Literal["development", "test", "production"] = "development"
    demo_mode: bool = True
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    database_url: str = Field(min_length=1)
    cors_allowed_origins: str = "http://localhost:5173"

    webhook_body_limit_bytes: int = Field(default=262_144, ge=1_024, le=1_048_576)
    ttn_webhook_enabled: bool = False
    ttn_webhook_secret: SecretStr | None = None
    ttn_mqtt_host: str = "eu1.cloud.thethings.network"
    ttn_mqtt_port: int = Field(default=8883, ge=1, le=65_535)
    ttn_mqtt_username: str = "rain-garden@ttn"
    ttn_mqtt_topic: str = "v3/rain-garden@ttn/devices/outflow-a/up"
    ttn_mqtt_api_key: SecretStr | None = None

    public_rate_limit_requests: int = Field(default=120, ge=1, le=10_000)
    public_rate_limit_window_seconds: int = Field(default=60, ge=1, le=3_600)
    ingestion_rate_limit_requests: int = Field(default=30, ge=1, le=1_000)
    ingestion_rate_limit_window_seconds: int = Field(default=60, ge=1, le=3_600)

    device_stale_after_minutes: int = Field(default=90, ge=1, le=43_200)
    device_offline_after_minutes: int = Field(default=180, ge=2, le=43_200)
    default_measurement_range_days: int = Field(default=7, ge=1, le=31)
    max_measurement_range_days: int = Field(default=31, ge=1, le=31)
    max_measurement_result_rows: int = Field(default=5_000, ge=1, le=5_000)

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_allowed_origins.split(",") if origin.strip()]

    @model_validator(mode="after")
    def validate_related_settings(self) -> "Settings":
        if self.device_offline_after_minutes <= self.device_stale_after_minutes:
            raise ValueError("offline threshold must be greater than stale threshold")
        if self.default_measurement_range_days > self.max_measurement_range_days:
            raise ValueError("default measurement range cannot exceed the maximum")
        if self.ttn_webhook_enabled:
            if (
                self.ttn_webhook_secret is None
                or len(self.ttn_webhook_secret.get_secret_value()) < 16
            ):
                raise ValueError("enabled TTN webhook requires a secret of at least 16 characters")
        if self.app_env == "production" and not self.cors_origins:
            raise ValueError("production requires at least one CORS origin")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
