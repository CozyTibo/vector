# Phase 02 Temporal Continuity Doctrine

## Purpose
Define deterministic temporal/revision ordering semantics for raw memory.

## Revision Chain Semantics
- A logical object may have multiple preserved revisions.
- Supersession means "newer preserved revision exists," not "older revision removed."
- Historical visibility requires older preserved revisions to remain retrievable unless policy deletion applies.

## Deletion Visibility
- If deletion is observed as an event/state, it is preserved as evidence.
- If deletion happened before observation, system reports non-observed gap (not synthetic delete event).

## Ordering Precedence
For deterministic retrieval/replay ordering:
1. provider_event_timestamp (when available and valid),
2. source_revision marker precedence,
3. fetched_at (observation timestamp),
4. replay timestamp as lineage metadata only (not source chronology authority),
5. stable tie-breaker key.

Replay timestamps never override provider chronology semantics for historical ordering.

## Temporal Guarantees
Phase 02 guarantees deterministic ordering over preserved rows under declared precedence.
Phase 02 does not guarantee objective chronology for events never observed.
