from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class UnitSpec:
    unit_code: str
    display_name: str
    unit_symbol: str
    meaning: str


@dataclass(frozen=True, slots=True)
class MetricSpec:
    metric_code: str
    display_name: str
    meaning: str
    valid_min: float | None
    valid_max: float | None
    validity_basis: str
    metric_group: str = "operational"
    synthetic_demo_unit_code: str | None = None
    source: str = "Controlled monitoring vocabulary"
    expected_type: str = "number"
    scientifically_confirmed: bool = False


UNITS: tuple[UnitSpec, ...] = (
    UnitSpec("mm", "millimetres", "mm", "Length expressed in millimetres."),
    UnitSpec("deg_c", "degrees Celsius", "°C", "Temperature on the Celsius scale."),
    UnitSpec("pct", "percent", "%", "Dimensionless percentage."),
    UnitSpec(
        "vwc_pct",
        "volumetric water content percent",
        "% VWC",
        "Volumetric water content expressed as a percentage.",
    ),
    UnitSpec(
        "us_cm",
        "microsiemens per centimetre",
        "µS/cm",
        "Electrical conductivity expressed in microsiemens per centimetre.",
    ),
    UnitSpec("m_s", "metres per second", "m/s", "Speed expressed in metres per second."),
    UnitSpec("degree", "degrees", "°", "Angular direction in degrees."),
    UnitSpec(
        "mm_h", "millimetres per hour", "mm/h", "Intensity expressed as millimetres per hour."
    ),
    UnitSpec("lux", "lux", "lx", "Illuminance expressed in lux."),
    UnitSpec("uv_index", "UV index", "UV index", "Dimensionless ultraviolet index."),
    UnitSpec("hpa", "hectopascals", "hPa", "Pressure expressed in hectopascals."),
    UnitSpec("v", "volts", "V", "Electric potential expressed in volts."),
    UnitSpec("dbm", "decibel-milliwatts", "dBm", "Power ratio referenced to one milliwatt."),
    UnitSpec("db", "decibels", "dB", "Dimensionless logarithmic ratio."),
)


def _metric(
    code: str,
    name: str,
    meaning: str,
    unit: str | None,
    valid_min: float | None = None,
    valid_max: float | None = None,
    validity_basis: str = "No deployment-specific validity range is confirmed.",
    *,
    metric_group: str = "operational",
    source: str = (
        "Confirmed Orchard Park measurement vocabulary; unit mapping is demo-only unless a "
        "channel is confirmed."
    ),
) -> MetricSpec:
    return MetricSpec(
        code,
        name,
        meaning,
        valid_min,
        valid_max,
        validity_basis,
        metric_group,
        unit,
        source,
    )


METRICS: tuple[MetricSpec, ...] = (
    _metric(
        "soil_moisture",
        "Soil moisture",
        "Soil moisture measurement.",
        "vwc_pct",
        0.0,
        100.0,
        "Definition-level percentage bounds for the demo-normalised representation only.",
        metric_group="soil",
    ),
    _metric(
        "soil_temperature",
        "Soil temperature",
        "Soil temperature measurement.",
        "deg_c",
        metric_group="soil",
    ),
    _metric(
        "soil_electrical_conductivity",
        "Soil electrical conductivity",
        "Soil electrical conductivity measurement.",
        "us_cm",
        0.0,
        None,
        "Definition-level non-negative bound for the demo-normalised representation only.",
        metric_group="soil",
    ),
    _metric(
        "water_level",
        "Water level",
        "Water level relative to a channel-specific, currently unconfirmed datum.",
        "mm",
        metric_group="hydrology",
    ),
    _metric(
        "air_temperature",
        "Air temperature",
        "Air temperature measurement.",
        "deg_c",
        metric_group="weather",
    ),
    _metric(
        "relative_humidity",
        "Relative humidity",
        "Relative humidity measurement.",
        "pct",
        0.0,
        100.0,
        "Definition-level percentage bounds; device range is unconfirmed.",
        metric_group="weather",
    ),
    _metric(
        "wind_speed",
        "Wind speed",
        "Wind speed measurement.",
        "m_s",
        0.0,
        None,
        "Definition-level non-negative bound only; device range is unconfirmed.",
        metric_group="weather",
    ),
    _metric(
        "wind_direction",
        "Wind direction",
        "Circular wind direction measurement.",
        "degree",
        0.0,
        360.0,
        "Definition-level circular direction bounds only; device range is unconfirmed.",
        metric_group="weather",
    ),
    _metric(
        "rainfall_intensity",
        "Rainfall intensity",
        "Instantaneous or interval-representative rainfall intensity; never accumulated rainfall.",
        "mm_h",
        0.0,
        None,
        "Definition-level non-negative bound only; device range is unconfirmed.",
        metric_group="hydrology",
    ),
    _metric(
        "light_intensity",
        "Light intensity",
        "Light-intensity measurement.",
        "lux",
        0.0,
        None,
        "Definition-level non-negative bound for the demo-normalised representation only.",
        metric_group="weather",
    ),
    _metric(
        "uv_index",
        "UV index",
        "Ultraviolet index measurement.",
        "uv_index",
        0.0,
        None,
        "Definition-level non-negative bound only; device range is unconfirmed.",
        metric_group="weather",
    ),
    _metric(
        "barometric_pressure",
        "Barometric pressure",
        "Barometric pressure measurement.",
        "hpa",
        metric_group="weather",
    ),
    # Compatibility vocabulary retained for existing Phase 1 rows. The confirmed inventory does
    # not use these metric codes.
    _metric(
        "rainfall_mm",
        "Legacy rainfall",
        "Deprecated accumulated-rainfall demo vocabulary.",
        "mm",
        0.0,
        None,
        "Legacy Phase 1 definition-level bound.",
        source="Deprecated Phase 1 synthetic vocabulary",
        metric_group="hydrology",
    ),
    _metric(
        "air_temperature_c",
        "Legacy air temperature",
        "Deprecated Phase 1 temperature vocabulary.",
        "deg_c",
        source="Deprecated Phase 1 synthetic vocabulary",
        metric_group="weather",
    ),
    _metric(
        "relative_humidity_pct",
        "Legacy relative humidity",
        "Deprecated Phase 1 humidity vocabulary.",
        "pct",
        0.0,
        100.0,
        "Legacy Phase 1 percentage bounds.",
        source="Deprecated Phase 1 synthetic vocabulary",
        metric_group="weather",
    ),
    _metric(
        "soil_moisture_vwc_pct",
        "Legacy soil moisture",
        "Deprecated Phase 1 soil-moisture vocabulary.",
        "vwc_pct",
        0.0,
        100.0,
        "Legacy Phase 1 percentage bounds.",
        source="Deprecated Phase 1 synthetic vocabulary",
        metric_group="soil",
    ),
    _metric(
        "water_level_mm",
        "Legacy water level",
        "Deprecated Phase 1 water-level vocabulary.",
        "mm",
        source="Deprecated Phase 1 synthetic vocabulary",
        metric_group="hydrology",
    ),
    _metric(
        "battery_voltage_v",
        "Battery voltage",
        "Device battery voltage.",
        "v",
        source="Phase 1 operational vocabulary",
    ),
    _metric(
        "rssi_dbm",
        "Received signal strength",
        "Received signal strength indicator.",
        "dbm",
        source="Phase 1 operational vocabulary",
    ),
    _metric(
        "snr_db",
        "Signal-to-noise ratio",
        "LoRa signal-to-noise ratio.",
        "db",
        source="Phase 1 operational vocabulary",
    ),
    _metric(
        "unverified_numeric_output",
        "Unverified numeric output",
        (
            "Numeric decoder output retained for isolated replay inspection; its physical "
            "quantity and unit have not been established."
        ),
        None,
        source="Offline TTN replay testbed vocabulary",
    ),
)

METRICS_BY_CODE = {metric.metric_code: metric for metric in METRICS}
UNITS_BY_CODE = {unit.unit_code: unit for unit in UNITS}


def get_metric(metric_code: str) -> MetricSpec:
    try:
        return METRICS_BY_CODE[metric_code]
    except KeyError as exc:
        raise ValueError(f"Unsupported metric code: {metric_code}") from exc


def get_unit(unit_code: str) -> UnitSpec:
    try:
        return UNITS_BY_CODE[unit_code]
    except KeyError as exc:
        raise ValueError(f"Unsupported unit code: {unit_code}") from exc


def render_data_dictionary() -> str:
    header = (
        "# Data dictionary\n\n"
        "This file is generated from `backend/app/metric_catalog.py`. Metrics and physical units "
        "are separate concepts. A channel may have no unit while confirmation is pending. "
        "Demo-normalised units are illustrative and do not confirm the deployed sensor mapping.\n\n"
        "| Metric code | Group | Meaning | Synthetic demo unit | Valid-range status | Source | "
        "Deployment unit confirmed |\n"
        "|---|---|---|---|---|---|---|\n"
    )
    rows = []
    for metric in METRICS:
        unit = UNITS_BY_CODE.get(metric.synthetic_demo_unit_code or "")
        demo_unit = f"`{unit.unit_code}` ({unit.unit_symbol})" if unit else "None"
        rows.append(
            "| "
            + " | ".join(
                (
                    f"`{metric.metric_code}`",
                    metric.metric_group,
                    metric.meaning,
                    demo_unit,
                    metric.validity_basis,
                    metric.source,
                    "No — channel status controls confirmation",
                )
            )
            + " |"
        )
    return header + "\n".join(rows) + "\n"
