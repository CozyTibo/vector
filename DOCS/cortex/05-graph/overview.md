# Organizational Graph Layer Overview

## Why This Phase Exists
This phase isolates a specific transformation responsibility in the Cortex cognition pipeline so downstream intelligence remains deterministic, replayable, and explainable.

## Responsibilities
- Temporal relationship graph construction
- Decision/dependency/blocker/ownership edge typing
- Lineage traversal primitives

## Non-Responsibilities
- No summarization output formatting
- No AI-generated truth assertions
- No source connector logic

## Ownership Boundary
This phase owns only its contract outputs and may not bypass adjacent layers.
