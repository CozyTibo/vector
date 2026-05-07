# Provenance Query Model

## Objective
Ensure every cognition output can be traced to source evidence through deterministic, operationally usable traversal paths.

## Provenance Traversal Use Cases
- canonical object -> raw evidence lineage,
- linkage assertion -> evidence and confidence basis,
- AI-assisted extraction -> source snippets and model context,
- replay divergence -> lineage of changed outputs.

## Traversal Requirements
- directional traversal (output -> input and input -> affected outputs),
- bounded-depth defaults for operator UX,
- full-depth audit mode for governance incidents,
- replay-aware lineage reconstruction across versions.

## Storage/Index Implications
- lineage chain identifiers,
- source reference indexes by object/time/phase,
- replay-versioned provenance anchors.

## Pressure Points
- recursive fanout on highly reused source events,
- repeated evidence expansions during debugging sessions,
- cross-phase joins where provenance schemas differ by stage.

## Optimization Strategy
- preserve normalized provenance truth,
- optionally precompute hot traversal edges for operational triage,
- invalidate/regenerate precomputations via deterministic replay boundaries.

## Non-Negotiable
Provenance acceleration must never sacrifice reconstructability or introduce opaque evidence gaps.
