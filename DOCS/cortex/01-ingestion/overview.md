# Connector & Ingestion Layer Overview

## Why This Phase Exists
This phase isolates a specific transformation responsibility in the Cortex cognition pipeline so downstream intelligence remains deterministic, replayable, and explainable.

## Responsibilities
- Connector authentication and source polling orchestration
- Source envelope validation and normalization
- Idempotent handoff to raw_store
- **Deep connector exhaust:** expand resource coverage, paginate to completion, run historical backfill within declared windows, and keep incremental sync + replay semantics honest for each stream (substrate alone is insufficient — see `../MASTER_TRACKER.md` §2.5 and `real-ingestion-definition.md`).

## Non-Responsibilities
- No organizational meaning inference
- No topic/concern/decision summarization
- No causal or risk classification

## Ownership Boundary
This phase owns only its contract outputs and may not bypass adjacent layers.
