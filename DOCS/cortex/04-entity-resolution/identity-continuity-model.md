# Identity Continuity Model

## Objective
Model how identities persist, split, merge, and evolve through time.

## Continuity States
- `stable`,
- `candidate_merge`,
- `merged`,
- `split`,
- `superseded`,
- `unresolved`.

## Temporal Behavior
- continuity records include validity windows,
- superseding continuity records preserve history,
- no silent overwrite of prior identity assumptions.

## Replay & Provenance
- continuity outcomes must be reproducible by replay under same versions,
- each continuity state references supporting evidence lineage.
