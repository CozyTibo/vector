# Raw Event Storage Layer Overview

## Why This Phase Exists
This phase isolates a specific transformation responsibility in the Cortex cognition pipeline so downstream intelligence remains deterministic, replayable, and explainable.

## Responsibilities
- Immutable persistence of source-faithful payloads
- Deduplication via envelope hash/idempotency keys
- Replay indexing and retention metadata

## Non-Responsibilities
- No canonical field mapping
- No identity linking
- No semantic interpretation

## Ownership Boundary
This phase owns only its contract outputs and may not bypass adjacent layers.
