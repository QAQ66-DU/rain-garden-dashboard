# ADR 0009: Use half-open, schedule-aligned Time Explorer coverage

- Status: accepted
- Decision: Site-wide historical queries use half-open UTC windows `[start, end)`. Expected observations are explicit schedule slots derived from the channel's reporting interval and anchor, with a configurable timestamp-jitter tolerance. Coverage is unavailable when any schedule input is unknown.
- Rationale: Counting rounded window duration is wrong for custom windows that do not align with a device schedule. Slot assignment also prevents duplicate uplinks from inflating coverage and keeps missing observations distinct from numeric zero.
- Consequence: `measured_at` determines slot membership and the scientific chart axis; `received_at` supports separate delay labels. One accepted observation fills at most one slot, flagged observations are received but not valid, and late/out-of-tolerance observations remain explicit. Metric-specific summaries exclude flagged values, and rainfall duration above zero requires known cadence and complete valid coverage. The UI separates incompatible units and current freshness from historical availability.
