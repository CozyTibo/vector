# Replay-Critical Fields

## Purpose
Classify envelope fields by replay impact so schema evolution does not accidentally break determinism.

## Classification Rules
- **Replay-Critical:** field semantics directly affect replay equivalence, ordering, idempotency, or lineage continuity.
- **Replay-Adjacent:** field supports operations/diagnostics around replay but should not change replay output equivalence.
- **Replay-Irrelevant:** operational-only metadata that must never participate in replay identity/equivalence logic.

## Replay-Critical
- `tenant_id`
- `connector_type`
- `connector_instance_id`
- `raw_event_id`
- `source_event_id` (when present)
- `source_object_id`
- `source_object_type`
- `source_occurred_at` semantics
- `payload_hash` semantics
- `ingestion_idempotency_key` semantics
- `schema_version`
- `extraction_version`
- `processor_version`
- `replay_job_id` and `replay_version` semantics
- `provenance.chain_id`
- minimum `provenance.source_refs[]`
- `ordering_metadata` semantics

## Replay-Adjacent
- `ingestion_run_id`
- `cursor_metadata`
- replay divergence counters
- replay checkpoint progress metrics
- queue lane selection metadata

## Replay-Irrelevant
- transient runtime diagnostics (host ids, worker runtime tags),
- operator notes/annotations,
- non-authoritative UI hints.

## Evolution Policy By Class
- Replay-Critical: semantic mutation forbidden without major version contract + explicit compatibility strategy.
- Replay-Adjacent: additive-only preferred; semantic changes require validation of non-impact on replay equivalence.
- Replay-Irrelevant: freely evolvable if isolated from replay/idempotency logic.
