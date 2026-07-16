# ADR 0004: Long-format channel measurements

- Status: accepted
- Decision: measurements reference SensorChannel; metric code remains independent of depth and position.
- Rationale: one device may expose repeated metrics at different depths or positions, and a wide nullable table would not scale safely.
- Consequence: queries join channel metadata, while comparability decisions remain explicit in services and UI.
