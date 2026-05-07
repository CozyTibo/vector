# Canonicalization Layer Overview

## Why This Phase Exists
This phase isolates a specific transformation responsibility in the Cortex cognition pipeline so downstream intelligence remains deterministic, replayable, and explainable.

## Responsibilities
- Mapping raw events into CanonicalEvent/Entity/Relation contracts
- Normalization of tool-specific schemas into organizational primitives
- Deterministic reference extraction and structure standardization

## Non-Responsibilities
- No causal inference
- No strategic summary generation
- No prediction of future impact

## Ownership Boundary
This phase owns only its contract outputs and may not bypass adjacent layers.
