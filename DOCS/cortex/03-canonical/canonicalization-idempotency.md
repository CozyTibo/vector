# Canonicalization Idempotency

## Goal
Ensure repeated canonicalization attempts do not produce duplicate authoritative objects for same identity + version context.

## Idempotency Keys
- canonical event key:
  - tenant + source refs + canonical_event_type + version tuple.
- canonical entity/relation keys:
  - stable identity fields + version tuple.

## Retry Safety
- retried canonical persistence is no-op for existing idempotency key.
- partial failure retries preserve prior successful writes and resume deterministically.

## Replay Safety
- replay reruns with same version context produce equivalent canonical id sets.
