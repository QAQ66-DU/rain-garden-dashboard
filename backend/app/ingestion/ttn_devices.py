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
    unit_code: str | None = None


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
    unit_code: str | None = None,
    *,
    decoded_type: str | None = None,
) -> TTNChannelMapping:
    return TTNChannelMapping(
        measurement_id=measurement_id,
        channel_code=channel_code,
        display_name=display_name,
        metric_code=metric_code,
        decoded_type=decoded_type or display_name,
        scientific_meaning=(
            f"Measurement ID {measurement_id} is mapped to {display_name} from supplied "
            "sensor metadata."
            if unit_code
            else f"The supplied decoder labels this field {display_name}; its physical unit "
            "has not been confirmed."
        ),
        verification_status="catalogued",
        unit_code=unit_code,
    )


def _confirmed_channel(
    measurement_id: int,
    channel_code: str,
    display_name: str,
    metric_code: str,
    unit_code: str,
    *,
    decoded_type: str = "report_telemetry",
) -> TTNChannelMapping:
    return TTNChannelMapping(
        measurement_id=measurement_id,
        channel_code=channel_code,
        display_name=display_name,
        metric_code=metric_code,
        decoded_type=decoded_type,
        scientific_meaning=(
            f"Measurement ID {measurement_id} is mapped to {display_name} from supplied "
            "sensor metadata."
        ),
        verification_status="catalogued",
        unit_code=unit_code,
    )


WEATHER_CHANNELS = (
    _weather_channel(4097, "air_temperature", "Air Temperature", "air_temperature", "deg_c"),
    _weather_channel(4098, "air_humidity", "Air Humidity", "relative_humidity", "pct"),
    _weather_channel(4099, "light_intensity", "Light Intensity", "light_intensity", "lux"),
    _weather_channel(4190, "uv_index", "UV Index", "uv_index"),
    _weather_channel(4105, "wind_speed", "Wind Speed", "wind_speed", "m_s"),
    _weather_channel(
        4104,
        "wind_direction_sensor",
        "Wind Direction Sensor",
        "wind_direction",
        "degree",
    ),
    _weather_channel(
        4113,
        "rain_gauge",
        "Rainfall Intensity",
        "rainfall_intensity",
        "mm_h",
        decoded_type="Rain Gauge",
    ),
    _weather_channel(
        4101,
        "barometric_pressure",
        "Barometric Pressure",
        "barometric_pressure",
        "pa",
    ),
)


TTN_DEVICE_MAPPINGS: dict[str, TTNDeviceMapping] = {
    "outflow-a": TTNDeviceMapping(
        device_id="outflow-a",
        device_type="test_telemetry_device",
        channels=(
            _confirmed_channel(
                1,
                "outflow_measurement_1",
                "Outflow A (Total)",
                "outflow_total",
                "ml",
                decoded_type="Measurement",
            ),
            _confirmed_channel(
                2,
                "outflow_measurement_2",
                "Outflow A",
                "outflow_rate",
                "ml_h",
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
            TTNChannelMapping(
                measurement_id=4106,
                channel_code="measurement_4106",
                display_name="pH",
                metric_code="ph",
                decoded_type="report_telemetry",
                scientific_meaning=(
                    "Measurement ID 4106 is mapped to dimensionless pH from supplied sensor "
                    "metadata; the current model cannot represent confirmed unitless channels."
                ),
                verification_status="catalogued",
            ),
        ),
    ),
    "soilmoisture-temp-sensor": TTNDeviceMapping(
        device_id="soilmoisture-temp-sensor",
        device_type="soil_moisture_sensor",
        channels=(
            _confirmed_channel(
                4102,
                "measurement_4102",
                "Soil Temperature",
                "soil_temperature",
                "deg_c",
            ),
            _confirmed_channel(
                4103,
                "measurement_4103",
                "Soil Moisture",
                "soil_moisture",
                "pct",
            ),
            _confirmed_channel(
                4108,
                "measurement_4108",
                "Electrical Conductivity",
                "soil_electrical_conductivity",
                "ds_m",
            ),
        ),
    ),
}

TTN_PROXY_DEVICE_IDS = tuple(TTN_DEVICE_MAPPINGS)
