# Canonicalization Model

> **Normative supersession:** Phase 03 doctrine now owns definitions and boundaries. Start with `phase-03-canonical-model-doctrine.md` and `phase-03-normative-index.md`. This file remains a short conceptual primer.

## Definition
Canonicalization is the **deterministic structural projection layer** that converts Phase 02 raw records into normalized, ontology-aligned organizational memory objects **without semantic inference** (see `phase-03-anti-goals-doctrine.md`).

## Transformation Boundaries
- Source-boundary in: raw events with source semantics.
- Canonical-boundary out: tool-agnostic events/entities/relations with provenance.

## Normalization Scope
- normalize identifiers, event types, actor/artifact references, and explicit relationships.
- preserve source-specific details as evidence metadata, not canonical primary schema.

## Ontology Boundaries
- map only to defined ontology concepts.
- unresolved mappings remain explicit ambiguities; no forced ontology fit.

## Provenance & Temporal Preservation
- every canonical output includes source refs and transformation lineage.
- source chronology must survive mapping (`occurred_at` anchored).

## Replay Implications
- fixed raw input + fixed versions => stable canonical output set.
- version changes may alter outputs but must be explainable and auditable.

## Explicit Non-Goals
- no strategic reasoning,
- no predictive impact inference,
- no executive summaries.
