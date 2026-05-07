# Ingestion Replay Strategy

## Replay Registration
Replay begins with immutable `replay_job_id`, `replay_version`, and scope:
- tenant,
- connector(s),
- time window,
- object-type or object-id filters.

## Replay Modes
- Full ingestion replay: full historical scan by connector.
- Partial replay: bounded time/object scope.
- Version replay: regenerate envelopes under new extraction version.

## Replay Isolation
- Replay queue lane is separate from live lane.
- Replay workers use dedicated concurrency budget.
- Replay cursor namespace separate from live cursor namespace.

## Replay Ordering
- Primary ordering by source chronology.
- Deterministic page traversal with persisted checkpoint tokens.
- No global order across connectors.

## Replay Consistency
- Identical source payload + version context -> identical envelope.
- Output differences must be attributable to version changes.
- Replay run stores divergence counters and sample diffs.
- Replay-critical field semantics are governed by `replay-critical-fields.md` and may not drift silently.

## Replay Checkpointing
- Replay checkpoints include:
  - replay cursor,
  - processed item count,
  - page token,
  - failure counters.
- Replay resumable from checkpoint after failure.

## Replay Transaction Boundaries
- Replay fetch, persist, and checkpoint are independently idempotent.
- Checkpoint commit only after persistence ack.
- Replay completion recorded after queue drain and final checkpoint.

## Live vs Replay Behavior
- Live mode advances live cursor.
- Replay mode never mutates live cursor unless explicitly configured for cursor replacement.
- Replay mode always tags envelopes with replay metadata.

## Contract Stability Requirement
Replay equivalence assumes frozen core envelope semantics from `raw-envelope-contract-stability.md`.
Schema evolution during replay-enabled operations must follow `schema-evolution-rules.md`.
