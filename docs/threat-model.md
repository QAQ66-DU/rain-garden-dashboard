# Threat model

## Assets

- MQTT API key, webhook secret, and database credentials.
- Private raw uplinks, external device identifiers, DevEUIs, and exact coordinates.
- Normalized measurements, quality metadata, research reproducibility, and service availability.
- OpenAPI contract, metric catalog, migrations, and synthetic provenance.

## Trust boundaries

1. Public browser to read-only API.
2. TTN MQTT broker to the profile-gated worker.
3. Future TTN service to webhook endpoint.
4. Backend and worker to PostgreSQL.
5. Build and CI systems to dependency registries and container images.
6. Authenticated future users to private identifiers/coordinates, which is outside Phase 1.

## Threats and mitigations

| Threat                         | Phase 0/1 mitigation                                                                                                                                      | Residual risk                                                                              |
| ------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------ |
| Forged webhook                 | Required secret, constant-time comparison, disabled adapter, TLS requirement                                                                              | Secret rotation and signed TTN scheme await confirmed integration                          |
| MQTT credential disclosure     | Ignored local environment, blank example value, dedicated worker, no credential logging                                                                   | Operator-controlled key rotation and least privilege                                       |
| MQTT interception              | CA-validated TLS on port 8883; insecure TLS is disabled                                                                                                   | Production network controls remain future work                                             |
| Malformed MQTT message         | Per-message JSON validation, controlled logging without payload content, worker continues                                                                 | Broker-side abuse monitoring remains future work                                           |
| Replay/duplicate uplink        | Unique source/idempotency key and transactional get-or-create                                                                                             | Additional device and frame-reset cases require new evidence                               |
| Oversized/malformed input      | Configurable 256 KiB default, JSON content-type check, Pydantic canonical contract                                                                        | Distributed body controls require reverse proxy                                            |
| Injection                      | Pydantic validation and SQLAlchemy parameters; no arbitrary filters                                                                                       | Dependency defects remain possible                                                         |
| Secret leakage                 | Ignored environment files, redacted logs/errors, secret scan, no frontend secrets                                                                         | Operator misconfiguration remains possible                                                 |
| Raw data/identifier disclosure | Separate private models and allowlisted public schemas                                                                                                    | Future endpoints require new privacy review                                                |
| Offline fixture disclosure     | Exact ignored source paths, small redacted CI derivative, aggregate-only replay output, private raw/quarantine tables                                     | Local operators can still mishandle the source export                                      |
| Exact coordinate disclosure    | Private device fields are excluded from public schemas; eight approved Orchard Park reference coordinates are intentionally published in the frontend map | The approved map coordinates are public; database administrators can access private fields |
| Denial via broad queries       | 7-day default, 31-day maximum, observation and warning-count preflights, cursor pages, rate limiting                                                      | In-memory limiting is per process only                                                     |
| Silent truncation              | Explicit oversize error before result delivery                                                                                                            | Aggregation is unavailable in Phase 1                                                      |
| Spreadsheet formula injection  | CSV exports allowlisted normalized fields and exclude raw payload or network content                                                                      | If names become externally mutable, explicit formula-prefix neutralization is required     |
| Scientific misinterpretation   | Synthetic labels, explicit unit-confirmation status, channel identity, no performance scores, documented assumptions                                      | Users may still export screenshots without context                                         |
| Misleading historical coverage | Explicit schedule inputs, half-open windows, unavailable state when schedule is unknown, separate current freshness                                       | Real schedule and jitter settings remain unconfirmed                                       |
| Quality-detail disclosure      | Allowlisted warning schema and controlled safe explanations; raw notes and payloads remain private                                                        | Future quality rules require renewed field-level review                                    |
| Supply-chain compromise        | Lockfiles, pinned CI actions/images, audits, secret scanning                                                                                              | Registries and upstream releases remain external dependencies                              |
| Stack trace/database leakage   | Standard problem responses and production exception middleware                                                                                            | Development logs are more verbose and must not hold secrets                                |

## Accepted Phase 1 risks

- Public read access is suitable only for synthetic or approved non-sensitive data.
- In-memory rate limiting does not coordinate multiple processes.
- TTN key rotation and production network-level controls remain operator/deployment responsibilities.
- The MQTT worker is limited to eight reviewed public device IDs and their evidence-backed
  ApplicationUp shapes, and is disabled outside the explicit Compose `live` profile. Application-wide
  subscription does not authorize unknown-device persistence; those events are privately quarantined.
- There is no user authentication, private-coordinate endpoint, backup automation, or formal audit log.
- Confirmed coordinates remain visible to database administrators; browser/OpenAPI contract tests only protect the public application boundary.
- Offline replay is approved only for the local testbed. It does not authorize live ingress or
  public exposure of exact TTN or gateway identifiers.
