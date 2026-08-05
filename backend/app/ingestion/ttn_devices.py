from __future__ import annotations

from dataclasses import dataclass

TTN_APPLICATION_ID = "rain-garden"
TTN_APPLICATION_UP_TOPIC = "v3/rain-garden@ttn/devices/+/up"
TTN_PROXY_SITE_NAME = "TTN proxy network"
TTN_PROXY_FEATURE_SLUG = "proxy-sensors"
TTN_PROXY_FEATURE_NAME = "Proxy sensors"


@dataclass(frozen=True, slots=True)
class TTNChannelMapping:
    measurement_id: int
    channel_code: str
    display_name: str
    metric_code: str
    decoded_type: str
    scientific_meaning: str | None = None
    verification_status: str = "unverified"


@dataclass(frozen=True, slots=True)
class TTNDeviceMapping:
    device_id: str
    device_type: str
    channels: tuple[TTNChannelMapping, ...]


def _unverified_channel(
    measurement_id: int,
    *,
    channel_code: str | None = None,
    display_name: str | None = None,
    decoded_type: str = "report_telemetry",
) -> TTNChannelMapping:
    return TTNChannelMapping(
        measurement_id=measurement_id,
        channel_code=channel_code or f"measurement_{measurement_id}",
        display_name=display_name or f"Measurement {measurement_id}",
        metric_code="unverified_numeric_output",
        decoded_type=decoded_type,
    )


def _weather_channel(
    measurement_id: int,
    channel_code: str,
    display_name: str,
    metric_code: str,
) -> TTNChannelMapping:
    return TTNChannelMapping(
        measurement_id=measurement_id,
        channel_code=channel_code,
        display_name=display_name,
        metric_code=metric_code,
        decoded_type=display_name,
        scientific_meaning=(
            f"The supplied decoder labels this field {display_name}; its physical unit "
            "has not been confirmed."
        ),
        verification_status="catalogued",
    )


WEATHER_CHANNELS = (
    _weather_channel(4097, "air_temperature", "Air Temperature", "air_temperature"),
    _weather_channel(4098, "air_humidity", "Air Humidity", "relative_humidity"),
    _weather_channel(4099, "light_intensity", "Light Intensity", "light_intensity"),
    _weather_channel(4190, "uv_index", "UV Index", "uv_index"),
    _weather_channel(4105, "wind_speed", "Wind Speed", "wind_speed"),
    _weather_channel(
        4104,
        "wind_direction_sensor",
        "Wind Direction Sensor",
        "wind_direction",
    ),
    _weather_channel(4113, "rain_gauge", "Rain Gauge", "unverified_numeric_output"),
    _weather_channel(
        4101,
        "barometric_pressure",
        "Barometric Pressure",
        "barometric_pressure",
    ),
)


TTN_DEVICE_MAPPINGS: dict[str, TTNDeviceMapping] = {
    "outflow-a": TTNDeviceMapping(
        device_id="outflow-a",
        device_type="test_telemetry_device",
        channels=(
            _unverified_channel(
                1,
                channel_code="outflow_measurement_1",
                display_name="Measurement 1",
                decoded_type="Measurement",
            ),
            _unverified_channel(
                2,
                channel_code="outflow_measurement_2",
                display_name="Measurement 2",
                decoded_type="Measurement",
            ),
        ),
    ),
    "soil-moisture-1": TTNDeviceMapping(
        device_id="soil-moisture-1",
        device_type="soil_moisture_sensor",
        channels=(_unverified_channel(1, decoded_type="Measurement"),),
    ),
    "prototype-board-1": TTNDeviceMapping(
        device_id="prototype-board-1",
        device_type="test_telemetry_device",
        channels=(),
    ),
    "weather-station-2": TTNDeviceMapping(
        device_id="weather-station-2",
        device_type="weather_station",
        channels=WEATHER_CHANNELS,
    ),
    "weather-station": TTNDeviceMapping(
        device_id="weather-station",
        device_type="weather_station",
        channels=WEATHER_CHANNELS,
    ),
    "vision-ai": TTNDeviceMapping(
        device_id="vision-ai",
        device_type="test_telemetry_device",
        channels=(),
    ),
    "ph-sensor": TTNDeviceMapping(
        device_id="ph-sensor",
        device_type="test_telemetry_device",
        channels=(
            _unverified_channel(4097),
            _unverified_channel(4106),
        ),
    ),
    "soilmoisture-temp-sensor": TTNDeviceMapping(
        device_id="soilmoisture-temp-sensor",
        device_type="soil_moisture_sensor",
        channels=(
            _unverified_channel(4102),
            _unverified_channel(4103),
            _unverified_channel(4108),
        ),
    ),
}

TTN_PROXY_DEVICE_IDS = tuple(TTN_DEVICE_MAPPINGS)
