# Linkage Idempotency

## Objective
Prevent duplicate durable linkage records for same linkage identity and version context.

## Idempotency Keys
- deterministic linkage key:
  - tenant + linkage_type + from_id + to_id + version tuple.
- ambiguity key:
  - tenant + ambiguity_type + candidate set hash + version tuple.

## Retry Safety
- repeated linkage persistence attempts are no-op when idempotency key exists.
- partial retries preserve prior successful records and resume safely.
