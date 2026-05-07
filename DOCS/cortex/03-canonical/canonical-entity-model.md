# Canonical Entity Model

## Purpose
Represent normalized organizational actors/teams/projects/artifacts/topics/decisions as stable identities.

## Lifecycle
- seeded from deterministic extraction,
- reconciled/updated via later entity-resolution phase,
- superseded when label/type interpretation evolves.

## Semantics
- entity type + label + identity refs + status lifecycle.

## Provenance
- each entity must reference source identity evidence or canonical derivation evidence.

## Temporal
- validity windows via `effective_from`/`effective_to`.

## Mutability
- `canonical_entity_id` immutable.
- labels/status can supersede.

## Ambiguity/Confidence
- uncertain typing represented explicitly.
- confidence required for inferred entity traits.
