# Canonical Thread Model

## Purpose
Represent temporally-linked discussion sequences independent of source thread mechanics.

## Lifecycle
- initialized from explicit source thread ids where available,
- reconstructed from reply/linkage metadata when source lacks explicit thread model,
- superseded only when linkage evidence changes.

## Ontology Semantics
- thread is a structured subset of discussion activity.
- thread can reference multiple topics and artifacts over time.

## Provenance
- each thread linkage must include evidence refs.

## Temporal
- thread ordering retains event chronology.

## Mutability
- thread identity immutable.
- membership/link edges supersedable.

## Ambiguity/Confidence
- uncertain membership is allowed as ambiguity records with confidence.
