# Entity Resolution & Linking Layer Overview

## Why This Phase Exists
This phase isolates a specific transformation responsibility in the Cortex cognition pipeline so downstream intelligence remains deterministic, replayable, and explainable.

## Responsibilities
- Cross-tool actor/artifact identity reconciliation
- Merge/split decisions with confidence semantics
- Identity conflict artifacts and resolution status

## Non-Responsibilities
- No graph-level causal claims
- No narrative synthesis
- No ownership policy decisions without evidence

## Ownership Boundary
This phase owns only its contract outputs and may not bypass adjacent layers.
