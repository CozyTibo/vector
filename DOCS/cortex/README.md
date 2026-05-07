# Cortex Documentation Hub

This directory is the architecture source of truth for Cortex: an organizational cognition infrastructure focused on deterministic memory, replayability, temporal understanding, and bounded AI inference.

## Core Sections
- `00-overview/`: architecture constraints, invariants, terminology policy, traceability matrices, governance, lifecycle, and failure stance.
- `01-10*/`: phase-specific contracts, ownership boundaries, and readiness gates.
- `schemas/`: ontology, contracts, dependency matrices, field semantics, provenance/confidence, temporal and memory model semantics.
- `connectors/`: connector depth and adapter-only strategy (no intelligence leakage).
- `adr/`: architecture decisions constraining implementation.
- `implementation/`: ordering, dependency graph, replay architecture/criticality, safety gates, scale assumptions, extraction policy.

## Usage Rule
Implementation should begin only when phase readiness gates are satisfied and required contracts are stable.

## Governance Rule
Use `00-overview/drift-detection-checklist.md` before approving architecture or schema changes.
Use `00-overview/architectural-traceability-matrix.md` to map invariants to enforcement artifacts.
