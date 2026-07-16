# ADR 0006: Docker portability

- Status: accepted
- Decision: multi-stage frontend/backend Dockerfiles and Docker Compose are the canonical local workflow.
- Rationale: users need only Docker and a modern browser on macOS, Windows, or Linux.
- Consequence: host-native commands are supported for contributors but are not required for dashboard users.
