# Raw Event Schema

## Table: `raw_event_envelopes`
Purpose: immutable source-ingestion evidence records.

## Primary Key
- `raw_event_id` (UUID/ULID, immutable).

## Field Contract
- `raw_event_id`
  - meaning: unique envelope identity.
  - mutability: immutable.
  - uniqueness: global unique.
  - replay sensitivity: replay record references this id.
  - indexing: primary key.
- `tenant_id`
  - meaning: tenant isolation scope.
  - mutability: immutable.
  - uniqueness: scoped with other keys.
  - replay sensitivity: replay scope anchor.
  - indexing: tenant composite indexes.
- `connector_type`, `connector_instance_id`
  - meaning: adapter source route.
  - mutability: immutable.
  - indexing: tenant+connector lookups.
- `source_event_id`
  - meaning: source-native event identity when available.
  - mutability: immutable if present.
  - uniqueness: not globally unique; scoped by tenant+connector+object.
  - replay sensitivity: dedupe and replay identity anchor.
- `source_object_id`, `source_object_type`
  - meaning: source entity identity and object family.
  - mutability: immutable.
  - indexing: tenant+source_object_id lookup.
- `source_occurred_at`
  - meaning: source event-time anchor (`occurred_at` equivalent for raw).
  - mutability: immutable.
  - indexing: tenant+connector+source_occurred_at.
  - replay sensitivity: chronology reconstruction.
- `source_payload`
  - meaning: immutable raw payload JSONB.
  - mutability: immutable.
  - indexing: avoid broad JSON indexing; targeted expression indexes only when required.
- `payload_hash`
  - meaning: stable hash over normalized payload bytes.
  - mutability: immutable.
  - uniqueness: used with source identity for dedupe.
  - indexing: dedupe composite.
- `ingestion_run_id`
  - meaning: run that persisted this row.
  - mutability: immutable.
  - indexing: run lookup.
- `replay_job_id`, `replay_version`
  - meaning: replay context when replay-produced.
  - mutability: immutable.
  - indexing: replay lookups and replay progress scans.
- `ingestion_version` (`schema_version` + `processor_version` + `extraction_version`)
  - meaning: version pinning for deterministic reproduction.
  - mutability: immutable.
  - replay sensitivity: highest.
- `source_api_version`
  - meaning: provider version context if available.
  - mutability: immutable.
- `provenance_chain_id`, `provenance_source_refs`
  - meaning: provenance bootstrap fields.
  - mutability: immutable.
  - indexing: chain lookup optional.
- `ordering_metadata`
  - meaning: deterministic order hints (page_seq, fetch_seq, source cursor rank).
  - mutability: immutable.
- `cursor_metadata`
  - meaning: source cursor token/window used for fetch.
  - mutability: immutable.
- `observed_at`, `processed_at`, `created_at`
  - meaning: observation, ingestion processing, and persistence times.
  - mutability: immutable for row.

## Immutability Law
Raw rows are append-only. Corrections are represented by additional rows linked through source identity and revision metadata, never updates.

## Contract Stability Classification
- Frozen core and replay-critical semantics are defined in:
  - `raw-envelope-contract-stability.md`
  - `replay-critical-fields.md`
- Schema evolution guardrails are defined in:
  - `schema-evolution-rules.md`
  - `envelope-versioning-doctrine.md`

## Frozen Core Reminder
The following are treated as frozen cognition contract semantics:
- identity and scope fields,
- source chronology semantics,
- idempotency key semantics,
- replay lineage semantics,
- provenance minimum continuity fields,
- ordering semantics used for deterministic replay.

## Required Uniqueness Constraints
- `ingestion_idempotency_key` unique.
- Optional conditional unique:
  - (`tenant_id`, `connector_instance_id`, `source_event_id`, `source_revision`) when source ids are present.

## Replay Dependencies
Replay requires:
- stable source identity semantics,
- immutable payloads,
- preserved version fields,
- cursor/order metadata retained.
