# Security policy

Do not report suspected vulnerabilities through public issues containing secrets, private identifiers, exact coordinates, or raw payloads. Use the university or project-owner private reporting channel once it is established.

Phase 1 is designed only for synthetic or explicitly approved non-sensitive read-only data. Production use with private data requires HTTPS, an established OIDC provider or authenticated reverse proxy, shared rate limiting, backup/restore procedures, and a renewed privacy/security review.

Never commit credentials. Copy `.env.example` to `.env`, supply unique local values, and keep `.env` untracked. If a secret may have been exposed, rotate it before relying on history cleanup.

Security controls and accepted risks are documented in `docs/threat-model.md`.
