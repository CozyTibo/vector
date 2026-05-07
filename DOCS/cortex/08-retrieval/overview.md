# Retrieval & Query Layer Overview

## Why This Phase Exists
This phase isolates a specific transformation responsibility in the Cortex cognition pipeline so downstream intelligence remains deterministic, replayable, and explainable.

## Responsibilities
- Evidence-grounded query planning
- Context-pack assembly with bounded scope
- Access-filtered retrieval selection

## Non-Responsibilities
- No memory mutation
- No hidden ranking without traceability
- No final synthesis phrasing

## Ownership Boundary
This phase owns only its contract outputs and may not bypass adjacent layers.
