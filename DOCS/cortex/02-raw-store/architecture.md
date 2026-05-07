# Raw Event Storage Layer Architecture

## Mission
Phase 02 is the immutable historical memory substrate of Cortex. It stores source-grounded records exactly enough to support replay, provenance continuity, and long-horizon reprocessing.

## Scope
Owns:
- immutable raw event persistence,
- replay-oriented storage indexing,
- retention and archival metadata,
- raw retrieval interfaces for replay/audit/reprocessing.

Does not own:
- canonical mapping,
- ontology interpretation,
- semantic enrichment,
- organizational reasoning.

## Logical Components
- `raw_event_store`: append-only source payload records.
- `raw_replay_index`: replay window and lineage lookup structures.
- `raw_archive_catalog`: hot/cold payload location metadata.
- `raw_integrity_registry`: checksum and corruption-detection metadata.

## Write Path
1. Receive validated ingestion envelope.
2. Validate immutability + idempotency constraints.
3. Persist raw payload record (append only).
4. Persist replay/index and integrity metadata.
5. Emit durable-write acknowledgement for downstream eligibility.

## Read Path
- replay scan by tenant/connector/time window,
- source-object forensic lookup,
- provenance bootstrap inspection,
- corruption and integrity verification scans.

## Storage Guarantees
- raw payload rows are never semantically rewritten.
- replay metadata is version-pinned and queryable.
- provenance bootstrap fields remain accessible across archival tiers.
