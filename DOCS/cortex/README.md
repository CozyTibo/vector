# Cortex Documentation Hub

This directory is the architecture source of truth for Cortex: an organizational cognition infrastructure focused on deterministic memory, replayability, temporal understanding, and bounded AI inference.

## Core Sections
- `00-overview/`: architecture constraints, invariants, terminology policy, traceability matrices, governance, lifecycle, and failure stance.
- `01-10*/`: phase-specific contracts, ownership boundaries, and readiness gates (Phase 01 Step 0: `01-ingestion/phase-01-step-0-connector-migration-safety-spec.md`; **Phase 01 organizational exhaust (normative):** `01-ingestion/phase-01-organizational-exhaust-spec.md`; **raw persistence units:** `01-ingestion/phase-01-raw-persistence-doctrine.md`; **ingestion continuity (modes, idempotency, convergence):** `01-ingestion/phase-01-ingestion-continuity-doctrine.md`; **gap map + roadmap:** `implementation/organizational-exhaust-execution-track.md`).
- `schemas/`: ontology, contracts, dependency matrices, field semantics, provenance/confidence, temporal and memory model semantics.
- `connectors/`: connector depth and adapter-only strategy (no intelligence leakage).
- `adr/`: architecture decisions constraining implementation.
- `implementation/`: ordering, dependency graph, replay architecture/criticality, safety gates, scale assumptions, extraction policy.

## Usage Rule
Implementation should begin only when phase readiness gates are satisfied and required contracts are stable.

## Phase completion rule
A phase is **not finished** until its **last tracker step** ships both **runtime** and a **strong admin / control plane update** for that phase (visibility, scoped actions, verification). See `MASTER_TRACKER.md` §3 **Terminal step — admin & operator closure**. **Phase 01:** last step is **14** (organizational exhaust exit); Step **6** closes substrate admin only.

## Governance Rule
Use `00-overview/drift-detection-checklist.md` before approving architecture or schema changes.
Use `00-overview/architectural-traceability-matrix.md` to map invariants to enforcement artifacts.
