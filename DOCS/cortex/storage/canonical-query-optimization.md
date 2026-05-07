# Canonical Query Optimization

## Objective
Define optimization options for canonical query families without breaking replay determinism or provenance clarity.

## High-Value Canonical Queries
- timeline reconstruction of canonical entities/events,
- decision/topic continuity inspection,
- confidence/ambiguity triage views,
- operator drilldowns for incident context.

## Candidate Optimizations
- denormalized read models for repeated operator views,
- materialized timeline snapshots for common windows,
- selective pre-aggregations for ambiguity/confidence dashboards.

## Risks
- stale read models if refresh policies are weak,
- hidden divergence from canonical truth,
- over-optimization for one tenant/query profile.

## Guardrail
Every optimized artifact must be replay-rebuildable and traceable back to canonical source records.
