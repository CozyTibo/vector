# Temporal Propagation Model

## Temporal Objective
Preserve source chronology and temporal validity through canonical transformation.

## Required Temporal Fields
- inherited: `occurred_at`, `observed_at`
- canonical processing: `processed_at`, `created_at`
- inference context: `inferred_at` where AI-assisted fields exist
- validity windows: `effective_from`, `effective_to`

## Propagation Rules
- source event-time remains chronology anchor.
- canonical processing time never replaces source chronology.
- superseded canonical records retain temporal lineage links.

## Evolving State Support
- ownership, decision, and action states can evolve through superseding records with validity windows.
