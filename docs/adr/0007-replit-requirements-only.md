# ADR 0007: Legacy Replit prototype is requirements-only

- Status: accepted
- Decision: no code, package, data API, secret API, startup logic, or runtime dependency is copied from the legacy Replit prototype.
- Rationale: the new repository must be portable, reviewable, and independently reproducible.
- Consequence: any prototype behavior must be restated as a reviewed requirement before implementation.

