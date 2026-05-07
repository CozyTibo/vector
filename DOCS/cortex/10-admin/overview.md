# Admin / Observability / Governance Layer Overview

## Why This Phase Exists
This phase isolates a specific transformation responsibility in the Cortex cognition pipeline so downstream intelligence remains deterministic, replayable, and explainable.

## Responsibilities
- Connector lifecycle and sync operations
- Replay/reprocess controls and safety
- Governance policy enforcement and auditability

## Non-Responsibilities
- No business reasoning logic
- No direct mutation of domain truth without policy path
- No untracked manual overrides

## Ownership Boundary
This phase owns only its contract outputs and may not bypass adjacent layers.
