# Canonical Topic Model

> **Scope note:** This document describes a **canonical-layer** concept (labels/tags/themes in source or canon). It is **not** the same as **execution scope** materialization.
>
> For execution scope (Declared Domains, Emergent Domains), see [`execution-scope-architecture.md`](../execution-scope-architecture.md) and [`declared-domains-v1-plan.md`](../declared-domains-v1-plan.md).
>
> **Do not conflate** canonical `Topic` with Declared or Emergent Domains.

## Purpose
Represent recurring semantic themes linked to events, threads, artifacts, and decisions **at the canonical layer** when explicitly tagged or deterministically extracted.

## Lifecycle
- deterministic topic extraction when explicit tags/labels exist,
- AI-assisted topic inference for implicit themes (**future canonical concern — not Declared Domains V1**),
- supersession when topic taxonomy evolves.

## Ontology Semantics
- topics are not initiatives by default.
- topics may map to project/initiative contexts through relations, not direct identity conflation.
- **Declared Domains** are projections from initiative/project **seeds**, not canonical Topic entities.

## Provenance
- explicit evidence set required for topic assignment.

## Temporal
- topic relevance can vary over time; maintain validity ranges.

## Ambiguity/Confidence
- overlapping or uncertain topic assignments remain multi-valued with confidence metadata.
