# ADR 0008: Normalize monitoring features and separate unit confirmation

- Status: accepted
- Decision: Devices belong to a site-scoped `MonitoringFeature`. Metric definitions are unit-neutral, physical units have their own catalogue, and each channel stores a nullable `unit_code` plus `unit_confirmation_status` (`pending`, `confirmed`, or `synthetic_demo_only`).
- Rationale: Orchard Park contains distinct Swale and Tree-pit assets, future sites may contain multiple assets, and an unknown deployment unit is a configuration state rather than a physical unit. This structure prevents demo-normalised values from being presented as confirmed mappings.
- Consequence: Existing Phase 1 channels migrate as `synthetic_demo_only`; non-synthetic canonical ingestion refuses numeric observations until their channel's physical-unit mapping is explicitly confirmed. The tree-pit device may exist with zero channels while its depth configuration remains pending.
