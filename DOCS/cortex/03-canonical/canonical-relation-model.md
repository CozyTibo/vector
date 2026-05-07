# Canonical Relation Model

## Purpose
Represent typed relationships between canonical entities/events.

## Lifecycle
- deterministic relations from explicit references,
- inferred relation candidates (bounded),
- supersession when evidence changes.

## Semantics
- relation types include ownership, dependency, discussion linkage, supersession, etc.

## Provenance
- must include evidence event refs and source lineage.

## Temporal
- validity windows required for non-instant relations.

## Mutability
- relation identity immutable.
- confidence and status supersedable with new evidence.

## Ambiguity/Confidence
- inferred relations require `confidence_score` + `confidence_band`.
- conflicting relations remain explicit until resolved downstream.
