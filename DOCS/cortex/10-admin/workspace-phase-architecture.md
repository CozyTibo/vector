# Workspace Phase Architecture

## Workspace Model
Workspace -> Cortex -> Phase Tabs -> Phase Objects -> Actions -> Audit Trail.

## Phase Tabs
- Ingestion
- Raw Memory
- Canonicalization
- Graph
- Memory
- Reasoning
- Retrieval
- Synthesis

## Per-Phase View Surfaces
- state and health,
- throughput and lag,
- lineage/provenance,
- failures and ambiguity,
- replay and reprocessing controls.

## Visibility Boundaries
- operators see tenant-scoped data only.
- cross-tenant diagnostics must use aggregated non-sensitive metadata.
- raw payload visibility follows permissions and redaction policies.

## Ownership Boundaries
- control plane reads from phase telemetry and control contracts.
- control plane actions invoke governed workflows; no direct unsafe phase mutation.
