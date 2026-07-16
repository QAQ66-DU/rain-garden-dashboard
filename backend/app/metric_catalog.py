from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class MetricSpec:
    metric_code: str
    display_name: str
    unit_code: str
    unit_symbol: str
    meaning: str
    valid_min: float | None
    valid_max: float | None
    validity_basis: str
    source: str = "Approved Phase 1 controlled vocabulary"
    expected_type: str = "number"
    scientifically_confirmed: bool = False


METRICS: tuple[MetricSpec, ...] = (
    MetricSpec(
        "rainfall_mm",
        "Rainfall",
        "mm",
        "mm",
        "Accumulated rainfall reported for the observation interval.",
        0.0,
        None,
        "Definition-level non-negative bound only; device range is unconfirmed.",
    ),
    MetricSpec(
        "air_temperature_c",
        "Air temperature",
        "deg_c",
        "°C",
        "Air temperature in degrees Celsius.",
        None,
        None,
        "No Phase 1 validity range is confirmed.",
    ),
    MetricSpec(
        "relative_humidity_pct",
        "Relative humidity",
        "pct",
        "%",
        "Relative humidity as a percentage.",
        0.0,
        100.0,
        "Definition-level percentage bounds; device range is unconfirmed.",
    ),
    MetricSpec(
        "soil_moisture_vwc_pct",
        "Soil moisture",
        "vwc_pct",
        "% VWC",
        "Volumetric water content expressed as a percentage.",
        0.0,
        100.0,
        "Definition-level percentage bounds; calibration and device range are unconfirmed.",
    ),
    MetricSpec(
        "water_level_mm",
        "Water level",
        "mm",
        "mm",
        "Water level relative to an unconfirmed sensor datum.",
        None,
        None,
        "Reference datum and valid range are unconfirmed.",
    ),
    MetricSpec(
        "battery_voltage_v",
        "Battery voltage",
        "v",
        "V",
        "Device battery voltage.",
        None,
        None,
        "Battery chemistry, nominal voltage, and valid range are unconfirmed.",
    ),
    MetricSpec(
        "rssi_dbm",
        "Received signal strength",
        "dbm",
        "dBm",
        "Received signal strength indicator.",
        None,
        None,
        "Radio and network metadata ranges are unconfirmed.",
    ),
    MetricSpec(
        "snr_db",
        "Signal-to-noise ratio",
        "db",
        "dB",
        "LoRa signal-to-noise ratio.",
        None,
        None,
        "Radio and network metadata ranges are unconfirmed.",
    ),
)

METRICS_BY_CODE = {metric.metric_code: metric for metric in METRICS}


def get_metric(metric_code: str) -> MetricSpec:
    try:
        return METRICS_BY_CODE[metric_code]
    except KeyError as exc:
        raise ValueError(f"Unsupported metric code: {metric_code}") from exc


def render_data_dictionary() -> str:
    header = (
        "# Data dictionary\n\n"
        "This file is generated from `backend/app/metric_catalog.py`. Do not edit the table "
        "manually. Sensor-specific ranges, calibration, precision, and field confirmation remain "
        "unresolved unless explicitly stated.\n\n"
        "| Metric code | Meaning | Unit code | Display unit | Expected type | "
        "Valid-range status | Source | Scientifically confirmed |\n"
        "|---|---|---|---|---|---|---|---|\n"
    )
    rows = []
    for metric in METRICS:
        confirmed = "Yes" if metric.scientifically_confirmed else "No — vocabulary only"
        rows.append(
            "| "
            + " | ".join(
                (
                    f"`{metric.metric_code}`",
                    metric.meaning,
                    f"`{metric.unit_code}`",
                    metric.unit_symbol,
                    metric.expected_type,
                    metric.validity_basis,
                    metric.source,
                    confirmed,
                )
            )
            + " |"
        )
    return header + "\n".join(rows) + "\n"
