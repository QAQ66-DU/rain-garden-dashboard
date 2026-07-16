# Threat model

## Assets

- Webhook secret and database credentials.
- Private raw uplinks, external device identifiers, DevEUIs, and exact coordinates.
- Normalized measurements, quality metadata, research reproducibility, and service availability.
- OpenAPI contract, metric catalog, migrations, and synthetic provenance.

## Trust boundaries

1. Public browser to read-only API.
2. Future TTN service to webhook endpoint.
3. Backend to PostgreSQL.
4. Build and CI systems to dependency registries and container images.
5. Authenticated future users to private identifiers/coordinates, which is outside Phase 1.

## Threats and mitigations

| Threat                         | Phase 0/1 mitigation                                                                     | Residual risk                                                     |
| ------------------------------ | ---------------------------------------------------------------------------------------- | ----------------------------------------------------------------- |
| Forged webhook                 | Required secret, constant-time comparison, disabled adapter, TLS requirement             | Secret rotation and signed TTN scheme await confirmed integration |
| Replay/duplicate uplink        | Unique source/idempotency key and transactional get-or-create                            | Real TTN identifier selection awaits fixtures                     |
| Oversized/malformed input      | Configurable 256 KiB default, JSON content-type check, Pydantic canonical contract       | Distributed body controls require reverse proxy                   |
| Injection                      | Pydantic validation and SQLAlchemy parameters; no arbitrary filters                      | Dependency defects remain possible                                |
| Secret leakage                 | Ignored environment files, redacted logs/errors, secret scan, no frontend secrets        | Operator misconfiguration remains possible                        |
| Raw data/identifier disclosure | Separate private models and allowlisted public schemas                                   | Future endpoints require new privacy review                       |
| Exact coordinate disclosure    | Nullable private fields excluded from public schemas; disclosure classification          | Database administrators can access private data                   |
| Denial via broad queries       | 7-day default, 31-day maximum, 5,000-row preflight, cursor pages, rate limiting          | In-memory limiting is per process only                            |
| Silent truncation              | Explicit oversize error before result delivery                                           | Aggregation is unavailable in Phase 1                             |
| Spreadsheet formula injection  | CSV is not implemented; future export must neutralize `= + - @` prefixes                 | No export path exists yet                                         |
| Scientific misinterpretation   | Synthetic labels, units, channel identity, no performance scores, documented assumptions | Users may still export screenshots without context                |
| Supply-chain compromise        | Lockfiles, pinned CI actions/images, audits, secret scanning                             | Registries and upstream releases remain external dependencies     |
| Stack trace/database leakage   | Standard problem responses and production exception middleware                           | Development logs are more verbose and must not hold secrets       |

## Accepted Phase 1 risks

- Public read access is suitable only for synthetic or approved non-sensitive data.
- In-memory rate limiting does not coordinate multiple processes.
- TTN payload compatibility, secret rotation, and network-level controls are unimplemented.
- There is no user authentication, private-coordinate endpoint, backup automation, or formal audit log.
