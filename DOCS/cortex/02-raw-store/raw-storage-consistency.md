# Raw Storage Consistency

## Strong Consistency Required
- raw insert + idempotency uniqueness enforcement,
- replay lineage linkage writes,
- corruption-integrity marker updates.

## Eventual Consistency Acceptable
- aggregate storage metrics,
- archival inventory reporting,
- non-critical observability rollups.

## Replay Read Consistency
- replay scans must operate on consistent snapshot semantics or equivalent deterministic scan boundaries.
- replay completeness checks must use same consistency boundary as scan.

## Tenant Isolation Consistency
- tenant filters must be applied on all raw reads/writes.
- cross-tenant scan or mutation is a critical fault class.

## Index Consistency
- replay-critical indexes must remain in-sync with raw inserts.
- stale indexes must be detectable with integrity probes.
