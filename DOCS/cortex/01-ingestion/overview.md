# Connector & Ingestion Layer Overview

## Why This Phase Exists
This phase isolates a specific transformation responsibility in the Cortex cognition pipeline so downstream intelligence remains deterministic, replayable, and explainable.

## Responsibilities
- Connector authentication and source polling orchestration
- Source envelope validation and normalization
- Idempotent handoff to raw_store

## Non-Responsibilities
- No organizational meaning inference
- No topic/concern/decision summarization
- No causal or risk classification

## Ownership Boundary
This phase owns only its contract outputs and may not bypass adjacent layers.
