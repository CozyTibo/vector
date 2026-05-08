# Raw Event Storage Layer Architecture

## Mission
Phase 02 is the immutable historical memory substrate of Cortex.

Foundational doctrine:
**Preserve evidence, do not interpret meaning.**

Phase 02 preserves observed organizational evidence with deterministic lineage and replay-safe access.
It does not claim omniscient organizational truth.

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

## Trust Boundary (Guarantees vs Non-Guarantees)
Phase 02 guarantees:
- continuity of captured evidence,
- continuity of provenance and replay lineage,
- deterministic replay boundaries over preserved rows,
- temporal reconstruction of what Cortex actually observed.

Phase 02 does not guarantee:
- perfect provider omniscience,
- recovery of states never observed by Cortex,
- reconstruction of data deleted before first observation,
- semantic/causal correctness about organizational meaning.

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

## Enforcement Posture (Stabilization Track)
Phase 02 enforcement is progressive:
- trust-aware runtime behavior with explicit risk signaling,
- catastrophic-only hard blocking initially,
- `would_block` semantics exposed before universal fail-closed rollout.

## Read Path
- replay scan by tenant/connector/time window,
- source-object forensic lookup,
- provenance bootstrap inspection,
- corruption and integrity verification scans.

## Storage Guarantees
- raw payload rows are never semantically rewritten.
- replay metadata is version-pinned and queryable.
- provenance bootstrap fields remain accessible across archival tiers.

## Historical Reconstruction Semantics
Reconstruction means "as-of preserved observation," not "as-of objective universal truth."

Examples:
- If a Slack message was deleted before Cortex ingested it, reconstruction cannot include it.
- If a provider mutates historical payloads after capture, Phase 02 preserves what was observed at capture time.
- If replay happens after provider-side deletion, replay uses preserved evidence; it does not refill missing provider history.
