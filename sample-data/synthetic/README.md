# Deterministic synthetic dataset

The seed command generates seven days of illustrative observations at a one-hour generator cadence ending at `2026-06-01T12:00:00Z` with random seed `20260716`.

This cadence is a generator setting, not a confirmed real sensor sampling interval. Values are synthetic and are not evidence of hydrological performance. Selected observations are omitted to test missing-data behavior. A relative-humidity observation above 100% tests quality flags, and one duplicate canonical uplink is deliberately submitted to test idempotency.

The database is the generated runtime representation. `seed-manifest.json` records the stable generator contract.

