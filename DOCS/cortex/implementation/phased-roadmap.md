# Phased Roadmap

## Phase 1: Connectors + Ingestion
Define adapter contracts, backfill/incremental strategy, idempotent ingestion envelopes.

## Phase 2: Raw Event Store
Implement immutable raw events, replay checkpoints, retention policy interfaces.

## Phase 3: Canonicalization
Define canonical schema, deterministic mapping, provenance guarantees.

## Phase 4: Entity Resolution
Implement identity linking, confidence scoring, merge/split audit.

## Phase 5: Graph
Build temporal graph edges for decisions, actions, artifacts, and ownership.

## Phase 6: Memory
Create compressed and derived memory layers with quality scoring.

## Phase 7: Reasoning
Introduce causal and timeline inference with deterministic + AI hybrid policy.

## Phase 8: Retrieval
Build query planner and evidence-grounded context pack assembly.

## Phase 9: Synthesis
Expose explainable synthesis outputs with provenance and confidence metadata.

## Phase 10: Admin/Governance
Operational controls for replay, monitoring, policy, and lifecycle management.

## Cross-cutting: admin closure every phase
Phases **01–09** each end with **Step 6 = runtime + admin closure** (per-phase operator visibility, triggers, and verification). Phase **10** integrates those slices into the unified governance UX; it does not replace the requirement that earlier phases already shipped their own closure when they completed.
