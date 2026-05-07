# Entity Resolution Pipeline

## Stage Sequence
1. ingest canonical candidates,
2. deterministic identity signal extraction,
3. candidate linkage generation,
4. confidence scoring and conflict detection,
5. AI-assisted ambiguity resolution (bounded),
6. provenance + temporal attachment,
7. continuity/link persistence,
8. downstream emission and observability updates.

## Ordering Guarantees
- deterministic ordering within scope by chronology and identity priority rules,
- no global total ordering across unrelated scopes.

## Replay Guarantees
- same input + version tuple yields comparable link outputs,
- divergence must be explainable by version/evidence changes.

## Failure Semantics
- deterministic parse failures quarantine affected candidates,
- unresolved ambiguities are persisted, not dropped,
- provenance failure blocks link publication.

## Idempotency
- deterministic linkage keys prevent duplicate durable link records.
