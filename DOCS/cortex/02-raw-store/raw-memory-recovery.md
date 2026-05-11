# Raw Memory Recovery

## Recovery Goals
- preserve evidence integrity,
- restore replay accessibility,
- contain corruption blast radius.

## Recovery Scenarios
- index corruption with intact payload rows,
- partial archival pointer loss,
- replay scan failures due to metadata drift,
- storage node failure impacting subset of partitions.

## Recovery Approach
- rebuild derived indexes from immutable raw rows.
- restore archival catalogs from audit logs and integrity manifests.
- quarantine uncertain scopes until integrity validation passes.

## Degraded Reconstruction Semantics
When recovery is incomplete, affected scopes must be explicitly marked as:
- partially reconstructable,
- replay-degraded, or
- unverifiable.

No silent downgrade to "healthy" is permitted.

## Survivability Assumption
As long as immutable raw payload + minimal identity/provenance metadata survive, replay substrate can be reconstructed.
