# Connector Isolation Model

## Fault Boundaries
- Connector type isolation:
  - Slack failures cannot block GitHub/Linear/Notion connectors.
- Tenant isolation:
  - tenant auth or data failures do not propagate to other tenants.
- Mode isolation:
  - replay failures do not block live runs by default.

## Queue Isolation
- Separate queue lanes by mode (`live`, `backfill`, `replay`, `retry`, `dead-letter`).
- Connector-specific routing keys prevent cross-connector contention.

## Resource Isolation
- Per-connector concurrency caps.
- Per-tenant quotas.
- Replay quotas independent from live quotas.

## Auth Isolation
- Auth failures mark only affected connector instance as `AUTH_FAILED`.
- Other connectors in tenant remain schedulable.

## Recovery Semantics
- Recovery run scoped to failed connector instance and mode.
- No global ingestion pause unless explicitly operator-triggered.
