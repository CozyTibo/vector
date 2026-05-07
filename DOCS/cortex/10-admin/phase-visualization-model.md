# Phase Visualization Model

## Visualization Contract
Every phase view must include:
- current phase state,
- phase-specific health metrics,
- key transitions and backlog pressure,
- replay/reprocessing context,
- lineage/provenance signal health.

## Phase 01 (Ingestion) Visualization
- ingestion runs, checkpoints, connector health, lag, throttling, dead-letter, replay jobs.
- control CTAs:
  - root: `Scheduled Polling ON/OFF` with current mode indicator,
  - workspace: `Trigger Connector Ingestion` quick action per connector row.
- CTA behavior requirements:
  - intuitive placement near ingestion health summary and connector list,
  - clear state labeling (`Active`, `Paused`, `Manual Only`),
  - action preview with scope, queue lane, and expected impact.

## Phase 02 (Raw Memory) Visualization
- raw growth, replay accessibility, archival tier state, integrity/corruption signals, provenance continuity.

## Phase 03 (Canonicalization) Visualization
- canonical throughput, mapping success/failure, ambiguity queues, confidence distributions, replay divergence.

## Future Phase Visualization (04+)
- graph state transitions and lineage quality,
- memory compaction and projection drift,
- reasoning hypothesis confidence and conflict,
- retrieval context-pack quality,
- synthesis confidence and citation completeness.

## Human Digest Requirement
Each phase page includes a "What is happening" digest:
- current objective,
- current bottleneck,
- confidence/trust status,
- recommended safe actions.
