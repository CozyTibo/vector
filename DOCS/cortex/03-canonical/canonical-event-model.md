# Canonical Event Model

## Purpose
Represent normalized organizational activity events independent of source tool schema.

## Lifecycle
- created from raw event transformation,
- optionally superseded by improved mappings under newer versions,
- retained for temporal replay and lineage continuity.

## Semantics
- captures what happened, who was involved, and when.
- references related entities and source evidence.

## Provenance
- required source refs and transformation lineage for each event.

## Temporal
- `occurred_at` is primary chronology anchor,
- `processed_at` marks transformation-time,
- supersession links preserve history.

## Mutability
- identity fields immutable.
- enrichments supersedable via versioned replay.

## Ambiguity/Confidence
- explicit ambiguity markers for uncertain classification.
- confidence required when inferred event facets exist.
