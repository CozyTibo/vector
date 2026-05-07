# Canonical Artifact Model

## Purpose
Represent durable work objects (code changes, docs, issues, PRs, specs, transcripts) with tool-agnostic identity.

## Lifecycle
- derived from explicit source object references,
- revised over time with source revision metadata,
- never overwrites historical versions.

## Ontology Semantics
- artifacts are durable references, not events.
- events describe actions on artifacts.

## Provenance
- required source object refs and revision lineage.

## Temporal
- artifact lifecycle tracks creation/revision/deprecation intervals.

## Ambiguity/Confidence
- ambiguous artifact equivalence across tools captured as hypotheses with confidence.
