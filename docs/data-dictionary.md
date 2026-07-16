# Data dictionary

This file is generated from `backend/app/metric_catalog.py`. Do not edit the table manually. Sensor-specific ranges, calibration, precision, and field confirmation remain unresolved unless explicitly stated.

| Metric code | Meaning | Unit code | Display unit | Expected type | Valid-range status | Source | Scientifically confirmed |
|---|---|---|---|---|---|---|---|
| `rainfall_mm` | Accumulated rainfall reported for the observation interval. | `mm` | mm | number | Definition-level non-negative bound only; device range is unconfirmed. | Approved Phase 1 controlled vocabulary | No — vocabulary only |
| `air_temperature_c` | Air temperature in degrees Celsius. | `deg_c` | °C | number | No Phase 1 validity range is confirmed. | Approved Phase 1 controlled vocabulary | No — vocabulary only |
| `relative_humidity_pct` | Relative humidity as a percentage. | `pct` | % | number | Definition-level percentage bounds; device range is unconfirmed. | Approved Phase 1 controlled vocabulary | No — vocabulary only |
| `soil_moisture_vwc_pct` | Volumetric water content expressed as a percentage. | `vwc_pct` | % VWC | number | Definition-level percentage bounds; calibration and device range are unconfirmed. | Approved Phase 1 controlled vocabulary | No — vocabulary only |
| `water_level_mm` | Water level relative to an unconfirmed sensor datum. | `mm` | mm | number | Reference datum and valid range are unconfirmed. | Approved Phase 1 controlled vocabulary | No — vocabulary only |
| `battery_voltage_v` | Device battery voltage. | `v` | V | number | Battery chemistry, nominal voltage, and valid range are unconfirmed. | Approved Phase 1 controlled vocabulary | No — vocabulary only |
| `rssi_dbm` | Received signal strength indicator. | `dbm` | dBm | number | Radio and network metadata ranges are unconfirmed. | Approved Phase 1 controlled vocabulary | No — vocabulary only |
| `snr_db` | LoRa signal-to-noise ratio. | `db` | dB | number | Radio and network metadata ranges are unconfirmed. | Approved Phase 1 controlled vocabulary | No — vocabulary only |
